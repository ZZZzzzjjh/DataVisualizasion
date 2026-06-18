from __future__ import annotations

import csv
import json
import math
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


SOURCES = {
    "numbeo_china": "https://www.numbeo.com/cost-of-living/country_result.jsp?country=China",
    "datav_china_geojson": "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json",
    "job_sdf_repo": "https://github.com/Job-SDF/benchmark",
    "city_gdp_wikipedia": "https://en.wikipedia.org/wiki/List_of_Chinese_prefecture-level_cities_by_GDP",
    "city_population_wikipedia": "https://en.wikipedia.org/wiki/List_of_cities_in_China_by_population",
    "nbs_data": "https://data.stats.gov.cn/",
    "china_statistical_yearbook": "https://www.stats.gov.cn/sj/ndsj/",
}


CORE_CITIES = [
    ("北京", "Beijing", "北京市", "华北", "一线"),
    ("上海", "Shanghai", "上海市", "华东", "一线"),
    ("广州", "Guangzhou", "广东省", "华南", "一线"),
    ("深圳", "Shenzhen", "广东省", "华南", "一线"),
    ("杭州", "Hangzhou", "浙江省", "华东", "新一线"),
    ("南京", "Nanjing", "江苏省", "华东", "新一线"),
    ("苏州", "Suzhou", "江苏省", "华东", "新一线"),
    ("成都", "Chengdu", "四川省", "西南", "新一线"),
    ("重庆", "Chongqing", "重庆市", "西南", "新一线"),
    ("武汉", "Wuhan", "湖北省", "华中", "新一线"),
    ("西安", "Xi'an", "陕西省", "西北", "新一线"),
    ("长沙", "Changsha", "湖南省", "华中", "新一线"),
    ("郑州", "Zhengzhou", "河南省", "华中", "新一线"),
    ("天津", "Tianjin", "天津市", "华北", "新一线"),
    ("青岛", "Qingdao", "山东省", "华东", "新一线"),
    ("宁波", "Ningbo", "浙江省", "华东", "新一线"),
    ("厦门", "Xiamen", "福建省", "华东", "二线"),
    ("合肥", "Hefei", "安徽省", "华东", "新一线"),
    ("佛山", "Foshan", "广东省", "华南", "新一线"),
    ("东莞", "Dongguan", "广东省", "华南", "新一线"),
]


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


def download(url: str, path: Path) -> None:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 data-visualization-coursework"})
    with urlopen(req, timeout=60) as response:
        path.write_bytes(response.read())


def clean_number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value)
    if text.lower() in {"nan", "none", ""}:
        return None
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = text.replace(",", "").replace("¥", "").replace("$", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        num = float(match.group())
    except ValueError:
        return None
    if math.isnan(num):
        return None
    return num


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def create_city_basic() -> None:
    rows = []
    for zh, en, province, region, tier in CORE_CITIES:
        rows.append(
            {
                "city_zh": zh,
                "city_en": en,
                "province": province,
                "region": region,
                "city_tier": tier,
                "notes": "课程项目核心城市清单；GDP、人口等数值建议后续从国家统计局或城市统计年鉴补全。",
            }
        )
    write_csv(
        PROCESSED_DIR / "city_basic.csv",
        rows,
        ["city_zh", "city_en", "province", "region", "city_tier", "notes"],
    )


def parse_numbeo() -> None:
    import pandas as pd

    url = SOURCES["numbeo_china"]
    tables = pd.read_html(url)
    city_table = None
    for table in tables:
        cols = [str(c) for c in table.columns]
        if any("City" in c for c in cols) and any("Cost of Living" in c for c in cols):
            city_table = table
            break
    if city_table is None:
        raise RuntimeError("未在 Numbeo 页面中找到城市生活成本表。")

    city_table.columns = [str(c).strip() for c in city_table.columns]
    rename = {
        "City": "city_en",
        "Cost of Living Index": "cost_of_living_index",
        "Rent Index": "rent_index",
        "Cost of Living Plus Rent Index": "cost_plus_rent_index",
        "Groceries Index": "groceries_index",
        "Restaurant Price Index": "restaurant_price_index",
        "Local Purchasing Power Index": "local_purchasing_power_index",
    }
    city_table = city_table.rename(columns=rename)
    keep = [c for c in rename.values() if c in city_table.columns]
    rows = []
    en_to_zh = {en: zh for zh, en, *_ in CORE_CITIES}
    for _, row in city_table.iterrows():
        city_en = str(row.get("city_en", "")).strip()
        rows.append(
            {
                "city_zh": en_to_zh.get(city_en, ""),
                "city_en": city_en,
                "cost_of_living_index": clean_number(row.get("cost_of_living_index")),
                "rent_index": clean_number(row.get("rent_index")),
                "cost_plus_rent_index": clean_number(row.get("cost_plus_rent_index")),
                "groceries_index": clean_number(row.get("groceries_index")),
                "restaurant_price_index": clean_number(row.get("restaurant_price_index")),
                "local_purchasing_power_index": clean_number(row.get("local_purchasing_power_index")),
                "source": url,
            }
        )
    write_csv(
        PROCESSED_DIR / "city_cost_numbeo.csv",
        rows,
        [
            "city_zh",
            "city_en",
            "cost_of_living_index",
            "rent_index",
            "cost_plus_rent_index",
            "groceries_index",
            "restaurant_price_index",
            "local_purchasing_power_index",
            "source",
        ],
    )


def create_job_source_index() -> None:
    rows = [
        {
            "dataset": "Job-SDF benchmark",
            "scope": "招聘需求预测研究数据；包含城市、岗位、企业、时间等维度，适合提取岗位数量、城市就业热度和岗位结构。",
            "url": SOURCES["job_sdf_repo"],
            "local_status": "请按仓库 README 获取完整数据；若网络允许，可进一步下载仓库中的 dataset 文件。",
        },
        {
            "dataset": "智联招聘/猎聘/BOSS直聘公开薪酬报告",
            "scope": "城市平均薪酬、行业薪酬、人才流动趋势；适合作为城市薪资水平数据来源。",
            "url": "https://www.zhaopin.com/ 或 https://www.liepin.com/ 或 https://www.zhipin.com/",
            "local_status": "报告通常为网页或 PDF，建议手动下载最新版并记录发布日期。",
        },
    ]
    write_csv(PROCESSED_DIR / "job_data_sources.csv", rows, ["dataset", "scope", "url", "local_status"])


def flatten_columns(columns: object) -> list[str]:
    flat = []
    for col in columns:
        if isinstance(col, tuple):
            flat.append(" ".join(str(part).strip() for part in col if str(part) != "nan"))
        else:
            flat.append(str(col).strip())
    return flat


def parse_wikipedia_table(
    url: str,
    raw_filename: str,
    output_name: str,
    keyword_candidates: list[str],
) -> None:
    import pandas as pd

    raw_path = RAW_DIR / raw_filename
    source = raw_path if raw_path.exists() else url
    tables = pd.read_html(source)
    selected = None
    for table in tables:
        table.columns = flatten_columns(table.columns)
        joined_cols = " ".join(table.columns)
        if any(keyword.lower() in joined_cols.lower() for keyword in keyword_candidates):
            selected = table
            break
    if selected is None:
        selected = tables[0]
        selected.columns = flatten_columns(selected.columns)

    selected = selected.dropna(how="all")
    selected["source"] = url
    selected.to_csv(PROCESSED_DIR / output_name, index=False, encoding="utf-8-sig")


def parse_city_reference_tables() -> None:
    parse_wikipedia_table(
        SOURCES["city_gdp_wikipedia"],
        "city_gdp_wikipedia.html",
        "city_gdp_wikipedia.csv",
        ["GDP", "City", "Province"],
    )
    parse_wikipedia_table(
        SOURCES["city_population_wikipedia"],
        "city_population_wikipedia.html",
        "city_population_wikipedia.csv",
        ["Population", "City", "Urban"],
    )


def create_score_template() -> None:
    rows = []
    for zh, en, *_ in CORE_CITIES:
        rows.append(
            {
                "city_zh": zh,
                "city_en": en,
                "job_opportunity_index": "",
                "salary_index": "",
                "cost_index": "",
                "income_cost_ratio": "",
                "job_living_value_index": "",
                "city_type": "",
                "notes": "根据 city_job.csv 与 city_cost_numbeo.csv 标准化后计算。",
            }
        )
    write_csv(
        PROCESSED_DIR / "city_score_template.csv",
        rows,
        [
            "city_zh",
            "city_en",
            "job_opportunity_index",
            "salary_index",
            "cost_index",
            "income_cost_ratio",
            "job_living_value_index",
            "city_type",
            "notes",
        ],
    )


def download_raw_files() -> None:
    raw_targets = {
        "numbeo_china_cost_of_living.html": SOURCES["numbeo_china"],
        "china_province_geojson_datav.json": SOURCES["datav_china_geojson"],
        "city_gdp_wikipedia.html": SOURCES["city_gdp_wikipedia"],
        "city_population_wikipedia.html": SOURCES["city_population_wikipedia"],
    }
    for filename, url in raw_targets.items():
        download(url, RAW_DIR / filename)


def write_description() -> None:
    text = f"""# 数据集描述与数据来源

本目录为《城市就业与生活成本分析》准备课程项目数据。数据分为 `raw` 原始文件和 `processed` 整理后的 CSV 文件。

## 文件清单

| 文件 | 类型 | 用途 |
| --- | --- | --- |
| `data/processed/city_basic.csv` | 城市基础信息 | 作为城市维度表，用于区域、城市等级、城市名称统一 |
| `data/processed/city_gdp_wikipedia.csv` | 城市 GDP 参考表 | 用于补充城市经济规模指标 |
| `data/processed/city_population_wikipedia.csv` | 城市人口参考表 | 用于补充人口规模指标 |
| `data/processed/city_cost_numbeo.csv` | 生活成本数据 | 用于分析城市生活成本、租金指数、消费指数 |
| `data/processed/job_data_sources.csv` | 就业数据来源索引 | 记录可用于补充就业与薪资数据的公开来源 |
| `data/processed/city_score_template.csv` | 综合评价模板 | 用于后续计算就业生活性价比指数 |
| `data/raw/numbeo_china_cost_of_living.html` | 原始网页 | Numbeo 中国城市生活成本页面备份 |
| `data/raw/china_province_geojson_datav.json` | 地图边界 | 中国省级 GeoJSON，可用于 ECharts 地图 |

## 1. city_basic.csv

字段说明：

| 字段 | 含义 |
| --- | --- |
| `city_zh` | 城市中文名 |
| `city_en` | 城市英文名，用于与英文数据源匹配 |
| `province` | 所属省份或直辖市 |
| `region` | 所属区域 |
| `city_tier` | 城市等级 |
| `notes` | 数据说明 |

说明：该文件是课程分析用的核心城市清单，建议后续从国家统计局或城市统计年鉴补充 GDP、常住人口、人均可支配收入、人均消费支出等数值指标。

## 1.1 城市 GDP 与人口参考表

本地文件：

- `data/processed/city_gdp_wikipedia.csv`
- `data/processed/city_population_wikipedia.csv`

来源：

- [List of Chinese prefecture-level cities by GDP]({SOURCES["city_gdp_wikipedia"]})
- [List of cities in China by population]({SOURCES["city_population_wikipedia"]})

说明：这两份表为公开百科页面整理表格，适合课程项目快速搭建基础指标。正式论文中建议进一步用国家统计局、城市统计年鉴或地方统计公报核验关键城市的 GDP 与人口数值。

## 2. city_cost_numbeo.csv

字段说明：

| 字段 | 含义 |
| --- | --- |
| `city_zh` | 城市中文名，能匹配核心城市时填入 |
| `city_en` | 城市英文名 |
| `cost_of_living_index` | 生活成本指数 |
| `rent_index` | 租金指数 |
| `cost_plus_rent_index` | 生活成本加租金指数 |
| `groceries_index` | 食品杂货指数 |
| `restaurant_price_index` | 餐饮价格指数 |
| `local_purchasing_power_index` | 本地购买力指数 |
| `source` | 数据来源链接 |

来源：[Numbeo Cost of Living in China]({SOURCES["numbeo_china"]})

使用说明：Numbeo 为用户贡献型生活成本数据库，适合课程项目做城市横向比较。论文中应说明该数据不是中国官方统计数据，适合作为生活成本参考指标。

## 3. job_data_sources.csv

该文件记录就业与薪资数据的推荐来源。就业数据通常没有统一、免费的官方城市级完整下载表，因此建议使用以下两类数据：

- 公开研究数据集：如 [Job-SDF benchmark]({SOURCES["job_sdf_repo"]})，适合提取城市岗位需求、岗位类型和时间变化。
- 招聘平台公开报告：如智联招聘、猎聘、BOSS直聘等发布的城市薪酬报告，适合补充平均薪资和行业薪酬。

建议整理成 `city_job.csv`：

| 字段 | 含义 |
| --- | --- |
| `city_zh` | 城市中文名 |
| `job_count` | 岗位数量 |
| `avg_salary` | 平均薪资 |
| `industry` | 行业类别 |
| `position_type` | 岗位类型 |
| `education` | 学历要求 |
| `experience` | 经验要求 |
| `source` | 数据来源 |

## 4. city_score_template.csv

该文件用于后续计算综合评价指标。

推荐公式：

```text
就业生活性价比指数 = 标准化岗位机会指数 + 标准化薪资指数 - 标准化生活成本指数
```

城市类型可按薪资和成本划分为：

- 高薪高成本型
- 高薪低成本型
- 低薪高成本型
- 均衡发展型

## 5. 地图数据

地图边界来源：[阿里云 DataV GeoAtlas](https://datav.aliyun.com/portal/school/atlas/area_selector)

本地文件：`data/raw/china_province_geojson_datav.json`

说明：当前下载的是中国省级 GeoJSON，适合做全国省级地图。如果要做地级市地图，可在 DataV GeoAtlas 页面选择对应省份或城市级边界后下载。

## 6. 官方统计数据补充来源

建议用于补充 GDP、人口、收入、消费支出等指标：

- [国家统计局国家数据]({SOURCES["nbs_data"]})
- [中国统计年鉴]({SOURCES["china_statistical_yearbook"]})

推荐补充字段：

| 字段 | 来源建议 |
| --- | --- |
| `gdp` | 国家统计局、城市统计年鉴 |
| `population` | 国家统计局、城市统计年鉴 |
| `per_capita_disposable_income` | 国家统计局、地方统计年鉴 |
| `per_capita_consumption_expenditure` | 国家统计局、地方统计年鉴 |
| `average_wage` | 统计年鉴、人社部门、招聘平台报告 |

## 7. 引用建议

论文中可以这样写：

> 本研究综合使用国家统计局公开统计数据、Numbeo 城市生活成本数据、招聘平台公开薪酬报告及 DataV GeoAtlas 地图边界数据，构建城市就业与生活成本分析数据集。为保证不同来源数据的一致性，本文对城市名称、指标单位和时间口径进行了统一处理。

## 8. 注意事项

- 不同来源数据的发布时间可能不同，分析时应尽量统一到同一年或相近年份。
- Numbeo 数据为用户贡献型数据，应作为参考性指标使用。
- 招聘平台数据可能存在行业和平台用户偏差，应在论文中说明局限性。
- 若需要正式统计口径，GDP、人口、收入和消费支出应优先使用国家统计局或地方统计年鉴。
"""
    (ROOT / "数据集描述.md").write_text(text, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    download_raw_files()
    create_city_basic()
    parse_city_reference_tables()
    parse_numbeo()
    create_job_source_index()
    create_score_template()
    write_description()
    print("数据集已下载并整理完成。")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
