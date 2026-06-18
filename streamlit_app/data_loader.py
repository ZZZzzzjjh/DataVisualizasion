from __future__ import annotations

from pathlib import Path

import pandas as pd


APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parents[0]


def data_file(name: str) -> Path:
    for base in [APP_DIR, ROOT]:
        path = base / "data" / "cleaned" / name
        if path.exists():
            return path
    return APP_DIR / "data" / "cleaned" / name


ENRICHED_PATH = data_file("city_panel_enriched.csv")
BASE_PATH = data_file("city_panel_clean.csv")
DATA_PATH = ENRICHED_PATH if ENRICHED_PATH.exists() else BASE_PATH


FIELD_LABELS = {
    "display_city": "城市",
    "city_name_zh": "城市中文名",
    "city_name_en": "城市英文名",
    "province_zh": "省份",
    "region": "区域",
    "city_tier": "城市等级",
    "gdp_rank": "GDP排名",
    "gdp_2024_cny_million": "GDP（百万元）",
    "gdp_2024_cny_billion": "GDP（亿元）",
    "population_2020": "2020年人口",
    "population_2020_million": "人口（百万人）",
    "population_change_percent": "人口变化率（%）",
    "gdp_per_capita_2024_cny": "人均GDP（元）",
    "avg_salary": "税后月薪（元/月）",
    "monthly_cost_single_rmb": "单人月生活成本（元/月，不含房租）",
    "monthly_cost_family_rmb": "四口之家月生活成本（元/月，不含房租）",
    "rent_1br_city_centre_rmb": "市中心一居室月租金（元/月）",
    "rent_1br_outside_centre_rmb": "非中心一居室月租金（元/月）",
    "rent_3br_city_centre_rmb": "市中心三居室月租金（元/月）",
    "rent_3br_outside_centre_rmb": "非中心三居室月租金（元/月）",
    "salary_cost_ratio": "月薪/单人生活成本",
    "salary_rent_ratio": "月薪/市中心一居室租金",
    "monthly_balance_after_cost_rmb": "扣除生活成本后月结余（元/月）",
    "monthly_balance_after_rent_cost_rmb": "扣除生活成本和房租后月结余（元/月）",
    "cost_of_living_index": "生活成本参考指数",
    "rent_index": "租金参考指数",
    "local_purchasing_power_index": "购买力参考指数",
    "job_market_proxy": "招聘热度代理",
    "job_count": "岗位数量",
    "industry": "行业类别",
    "position_type": "职位类型",
    "education_requirement": "学历要求",
    "experience_requirement": "经验要求",
    "employment_score": "就业吸引力得分",
    "dashboard_score": "综合参考得分",
    "city_type": "城市类型",
    "missing_key_fields": "关键字段缺失数",
    "salary_source": "薪资来源",
    "living_cost_source": "生活成本来源",
    "rent_source": "租金来源",
    "job_data_note": "就业数据说明",
}


NUMERIC_COLUMNS = [
    "gdp_2024_cny_million",
    "gdp_2024_cny_billion",
    "population_2020",
    "population_2020_million",
    "population_change_percent",
    "gdp_per_capita_2024_cny",
    "cost_of_living_index",
    "rent_index",
    "local_purchasing_power_index",
    "gdp_index",
    "population_index",
    "living_cost_index_norm",
    "rent_index_norm",
    "purchasing_power_index_norm",
    "dashboard_score",
    "missing_key_fields",
    "job_count",
    "avg_salary",
    "job_market_proxy",
    "job_density",
    "employment_score",
    "monthly_cost_single_rmb",
    "monthly_cost_family_rmb",
    "rent_1br_city_centre_rmb",
    "rent_1br_outside_centre_rmb",
    "rent_3br_city_centre_rmb",
    "rent_3br_outside_centre_rmb",
    "salary_cost_ratio",
    "salary_rent_ratio",
    "monthly_balance_after_cost_rmb",
    "monthly_balance_after_rent_cost_rmb",
]


def load_city_data(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_excel(path) if path.suffix.lower() in {".xlsx", ".xls"} else pd.read_csv(path)
    return ensure_dashboard_columns(normalize_columns(df))


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def ensure_dashboard_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "display_city" not in df.columns:
        df["display_city"] = df.get("city_name_zh", df.get("city_name_en", "未知城市"))
    if "city_name_zh" not in df.columns:
        df["city_name_zh"] = df["display_city"]
    if "city_name_en" not in df.columns:
        df["city_name_en"] = df["display_city"]

    if "gdp_2024_cny_billion" not in df.columns and "gdp_2024_cny_million" in df.columns:
        df["gdp_2024_cny_billion"] = df["gdp_2024_cny_million"] / 1000
    if "population_2020_million" not in df.columns and "population_2020" in df.columns:
        df["population_2020_million"] = df["population_2020"] / 1_000_000

    for col in [
        "avg_salary",
        "monthly_cost_single_rmb",
        "monthly_cost_family_rmb",
        "rent_1br_city_centre_rmb",
        "rent_1br_outside_centre_rmb",
        "rent_3br_city_centre_rmb",
        "rent_3br_outside_centre_rmb",
        "job_count",
    ]:
        if col not in df.columns:
            df[col] = pd.NA

    if "job_market_proxy" not in df.columns:
        gdp = pd.to_numeric(df.get("gdp_2024_cny_million"), errors="coerce")
        pop = pd.to_numeric(df.get("population_2020"), errors="coerce")
        if gdp.notna().any() and pop.notna().any():
            df["job_market_proxy"] = ((gdp / gdp.max()) * 0.6 + (pop / pop.max()) * 0.4).round(4)
        else:
            df["job_market_proxy"] = pd.NA

    salary = pd.to_numeric(df["avg_salary"], errors="coerce")
    single_cost = pd.to_numeric(df["monthly_cost_single_rmb"], errors="coerce")
    rent = pd.to_numeric(df["rent_1br_city_centre_rmb"], errors="coerce")
    df["salary_cost_ratio"] = salary / single_cost
    df["salary_rent_ratio"] = salary / rent
    df["monthly_balance_after_cost_rmb"] = salary - single_cost
    df["monthly_balance_after_rent_cost_rmb"] = salary - single_cost - rent

    for col in ["industry", "position_type", "education_requirement", "experience_requirement"]:
        if col not in df.columns:
            df[col] = pd.NA

    if "job_density" not in df.columns:
        df["job_density"] = df["job_count"] / df["population_2020_million"]

    if "employment_score" not in df.columns:
        df["employment_score"] = _mean_existing(df, ["job_market_proxy", "avg_salary", "monthly_balance_after_cost_rmb"])

    if "dashboard_score" not in df.columns:
        df["dashboard_score"] = _mean_existing(
            df,
            ["gdp_index", "population_index", "monthly_balance_after_cost_rmb", "salary_cost_ratio"],
        )

    if "city_type" not in df.columns:
        df["city_type"] = df.apply(classify_city_type, axis=1)

    if "salary_source" not in df.columns:
        df["salary_source"] = "Numbeo city page"
    if "living_cost_source" not in df.columns:
        df["living_cost_source"] = "Numbeo city page"
    if "rent_source" not in df.columns:
        df["rent_source"] = "Numbeo city page"
    if "job_data_note" not in df.columns:
        df["job_data_note"] = "招聘热度为经济规模与人口规模代理指标，不等同于真实岗位数量。"

    return df


def _mean_existing(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    available = [col for col in columns if col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().any()]
    if not available:
        return pd.Series([pd.NA] * len(df), index=df.index)
    normed = []
    for col in available:
        values = pd.to_numeric(df[col], errors="coerce")
        min_v, max_v = values.min(), values.max()
        if pd.isna(min_v) or pd.isna(max_v) or min_v == max_v:
            normed.append(pd.Series([pd.NA] * len(df), index=df.index))
        else:
            normed.append((values - min_v) / (max_v - min_v))
    return pd.concat(normed, axis=1).mean(axis=1, skipna=True)


def classify_city_type(row: pd.Series) -> str:
    salary = row.get("avg_salary")
    cost = row.get("monthly_cost_single_rmb")
    balance = row.get("monthly_balance_after_cost_rmb")
    if pd.isna(salary) or pd.isna(cost):
        return "数据不足"
    high_salary = salary >= 9000
    high_cost = cost >= 3500
    if high_salary and high_cost and pd.notna(balance) and balance >= 5000:
        return "高薪高成本"
    if high_salary and not high_cost:
        return "高薪较低成本"
    if not high_salary and high_cost:
        return "收入压力型"
    return "均衡发展型"


def filter_data(df: pd.DataFrame, regions: list[str], tiers: list[str], cities: list[str]) -> pd.DataFrame:
    out = ensure_dashboard_columns(df)
    if regions:
        out = out[out["region"].isin(regions)]
    if tiers:
        out = out[out["city_tier"].isin(tiers)]
    if cities:
        out = out[out["display_city"].isin(cities)]
    return out


def job_data_available(df: pd.DataFrame) -> bool:
    data = ensure_dashboard_columns(df)
    return data[["avg_salary", "monthly_cost_single_rmb", "rent_1br_city_centre_rmb"]].notna().any().any()


def summary_metrics(df: pd.DataFrame) -> dict[str, str]:
    data = ensure_dashboard_columns(df)
    metrics = {
        "城市数量": f"{len(data)}",
        "平均GDP": _money(data["gdp_2024_cny_billion"].mean(), "亿元", 0),
        "平均税后月薪": _money(data["avg_salary"].mean(), "元/月", 0),
        "平均单人月生活成本": _money(data["monthly_cost_single_rmb"].mean(), "元/月", 0),
        "平均市中心一居室租金": _money(data["rent_1br_city_centre_rmb"].mean(), "元/月", 0),
        "平均月结余": _money(data["monthly_balance_after_cost_rmb"].mean(), "元/月", 0),
    }
    return metrics


def _money(value: float, unit: str, decimals: int = 0) -> str:
    if pd.isna(value):
        return "暂无"
    return f"{value:,.{decimals}f} {unit}"


def display_columns(df: pd.DataFrame) -> pd.DataFrame:
    data = ensure_dashboard_columns(df)
    preferred = [
        "display_city",
        "province_zh",
        "region",
        "city_tier",
        "gdp_2024_cny_billion",
        "population_2020_million",
        "gdp_per_capita_2024_cny",
        "avg_salary",
        "monthly_cost_single_rmb",
        "rent_1br_city_centre_rmb",
        "monthly_balance_after_cost_rmb",
        "monthly_balance_after_rent_cost_rmb",
        "salary_cost_ratio",
        "job_market_proxy",
        "city_type",
    ]
    cols = [col for col in preferred if col in data.columns]
    return data[cols].rename(columns=FIELD_LABELS)


def field_dictionary() -> pd.DataFrame:
    return pd.DataFrame(
        [{"英文字段名": key, "中文列名": value} for key, value in FIELD_LABELS.items()]
    )


def expected_columns_by_chapter() -> pd.DataFrame:
    rows = [
        ("3.1 宏观背景", "gdp_2024_cny_billion", "GDP（亿元）", "用于城市经济规模对比"),
        ("3.1 宏观背景", "population_2020_million", "人口（百万人）", "用于城市人口规模对比"),
        ("3.1 宏观背景", "gdp_per_capita_2024_cny", "人均GDP（元）", "用于发展水平背景分析"),
        ("3.2 就业市场", "avg_salary", "税后月薪（元/月）", "用于薪资水平和就业回报分析"),
        ("3.2 就业市场", "job_market_proxy", "招聘热度代理", "用于城市就业机会强弱辅助比较"),
        ("3.3 生活成本", "monthly_cost_single_rmb", "单人月生活成本（元/月，不含房租）", "用于生活成本水平分析"),
        ("3.3 生活成本", "rent_1br_city_centre_rmb", "市中心一居室月租金（元/月）", "用于住房压力分析"),
        ("3.4 匹配关系", "monthly_balance_after_cost_rmb", "扣除生活成本后月结余（元/月）", "用于判断薪资是否覆盖日常支出"),
        ("3.4 匹配关系", "monthly_balance_after_rent_cost_rmb", "扣除生活成本和房租后月结余（元/月）", "用于判断真实居住压力"),
        ("4 建模洞察", "city_type", "城市类型", "用于城市类型划分"),
    ]
    return pd.DataFrame(rows, columns=["目录位置", "英文字段名", "中文列名", "用途"])


def region_summary(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    data = ensure_dashboard_columns(df)
    if group_col not in data.columns:
        return pd.DataFrame()
    agg = (
        data.groupby(group_col, dropna=False)
        .agg(
            城市数量=("display_city", "count"),
            平均GDP亿元=("gdp_2024_cny_billion", "mean"),
            平均税后月薪元=("avg_salary", "mean"),
            平均单人月生活成本元=("monthly_cost_single_rmb", "mean"),
            平均市中心一居室租金元=("rent_1br_city_centre_rmb", "mean"),
            平均月结余元=("monthly_balance_after_cost_rmb", "mean"),
        )
        .reset_index()
        .rename(columns={group_col: "分组"})
    )
    return agg.sort_values("平均月结余元", ascending=False)


def city_compare_table(df: pd.DataFrame, selected: list[str]) -> pd.DataFrame:
    data = ensure_dashboard_columns(df)
    if selected:
        data = data[data["display_city"].isin(selected)].copy()
    cols = [
        "display_city",
        "region",
        "city_tier",
        "avg_salary",
        "monthly_cost_single_rmb",
        "rent_1br_city_centre_rmb",
        "monthly_balance_after_cost_rmb",
        "monthly_balance_after_rent_cost_rmb",
        "gdp_2024_cny_billion",
        "city_type",
    ]
    return data[[col for col in cols if col in data.columns]].rename(columns=FIELD_LABELS)


def generate_rule_based_insights(df: pd.DataFrame) -> list[str]:
    data = ensure_dashboard_columns(df)
    if data.empty:
        return ["当前筛选条件下没有可分析的数据。"]

    insights: list[str] = []
    salary_data = data.dropna(subset=["avg_salary"])
    if len(salary_data) >= 2:
        high = salary_data.sort_values("avg_salary", ascending=False).iloc[0]
        low = salary_data.sort_values("avg_salary", ascending=True).iloc[0]
        insights.append(
            f"税后月薪最高的是{high['display_city']}，约 {high['avg_salary']:,.0f} 元/月；"
            f"最低的是{low['display_city']}，约 {low['avg_salary']:,.0f} 元/月。"
        )

    balance_data = data.dropna(subset=["monthly_balance_after_rent_cost_rmb"])
    if len(balance_data) >= 2:
        high = balance_data.sort_values("monthly_balance_after_rent_cost_rmb", ascending=False).iloc[0]
        low = balance_data.sort_values("monthly_balance_after_rent_cost_rmb", ascending=True).iloc[0]
        insights.append(
            f"扣除单人生活成本和市中心一居室房租后，{high['display_city']} 的估算月结余最高，"
            f"约 {high['monthly_balance_after_rent_cost_rmb']:,.0f} 元/月；"
            f"{low['display_city']} 的压力相对更大，约 {low['monthly_balance_after_rent_cost_rmb']:,.0f} 元/月。"
        )

    cost_data = data.dropna(subset=["monthly_cost_single_rmb"])
    if len(cost_data) >= 2:
        high = cost_data.sort_values("monthly_cost_single_rmb", ascending=False).iloc[0]
        low = cost_data.sort_values("monthly_cost_single_rmb", ascending=True).iloc[0]
        insights.append(
            f"单人月生活成本最高的是{high['display_city']}，约 {high['monthly_cost_single_rmb']:,.0f} 元/月；"
            f"最低的是{low['display_city']}，约 {low['monthly_cost_single_rmb']:,.0f} 元/月。"
        )

    type_counts = data["city_type"].value_counts(dropna=True)
    if not type_counts.empty:
        insights.append(f"当前样本中数量最多的城市类型是“{type_counts.index[0]}”。")

    return insights


def build_ai_context(df: pd.DataFrame, max_rows: int = 12) -> str:
    data = ensure_dashboard_columns(df)
    columns = [
        "display_city",
        "region",
        "city_tier",
        "avg_salary",
        "monthly_cost_single_rmb",
        "rent_1br_city_centre_rmb",
        "monthly_balance_after_cost_rmb",
        "monthly_balance_after_rent_cost_rmb",
        "gdp_2024_cny_billion",
        "city_type",
    ]
    existing = [col for col in columns if col in data.columns]
    sort_col = "monthly_balance_after_rent_cost_rmb"
    return data[existing].sort_values(sort_col, ascending=False).head(max_rows).to_csv(index=False)


JOB_STRUCTURE_PATH = data_file("city_job_structure.csv")


def load_job_structure(path: Path = JOB_STRUCTURE_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for col in ["job_share_percent", "position_avg_salary_rmb"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def filter_job_structure(
    job_df: pd.DataFrame,
    regions: list[str],
    tiers: list[str],
    cities: list[str],
) -> pd.DataFrame:
    if job_df.empty:
        return job_df
    out = job_df.copy()
    if regions and "region" in out.columns:
        out = out[out["region"].isin(regions)]
    if tiers and "city_tier" in out.columns:
        out = out[out["city_tier"].isin(tiers)]
    if cities and "city_name_zh" in out.columns:
        out = out[out["city_name_zh"].isin(cities)]
    return out
