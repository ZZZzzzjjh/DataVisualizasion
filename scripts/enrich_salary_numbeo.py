from __future__ import annotations

import re
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "cleaned" / "city_panel_clean.csv"
OUTPUT = ROOT / "data" / "cleaned" / "city_panel_enriched.csv"
RAW_DIR = ROOT / "data" / "raw" / "numbeo_city_pages"


PRICE_FIELDS = {
    "rent_1br_city_centre_rmb": "1 Bedroom Apartment in City Centre",
    "rent_1br_outside_centre_rmb": "1 Bedroom Apartment Outside of City Centre",
    "rent_3br_city_centre_rmb": "3 Bedroom Apartment in City Centre",
    "rent_3br_outside_centre_rmb": "3 Bedroom Apartment Outside of City Centre",
}


def download(url: str, path: Path) -> str:
    if path.exists() and path.stat().st_size > 1000:
        return path.read_text(encoding="utf-8", errors="ignore")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 coursework data collection"})
    with urlopen(req, timeout=45) as res:
        text = res.read().decode("utf-8", errors="ignore")
    path.write_text(text, encoding="utf-8")
    time.sleep(0.5)
    return text


def money_to_float(value: str | None) -> float | None:
    if not value:
        return None
    return float(value.replace(",", "").strip())


def extract_salary(html: str) -> float | None:
    pattern = r"Average Monthly Net Salary \(After Tax\).*?<span class=\"first_currency\">&#165;([\d,]+(?:\.\d+)?)</span>"
    match = re.search(pattern, html, flags=re.S)
    return money_to_float(match.group(1)) if match else None


def extract_summary_cost(html: str, person_type: str) -> float | None:
    pattern = rf"{person_type}.*?<span class=\"in_other_currency\">\(&#165;([\d,]+(?:\.\d+)?)\)</span>"
    match = re.search(pattern, html, flags=re.S | re.I)
    return money_to_float(match.group(1)) if match else None


def extract_price_by_label(html: str, label: str) -> float | None:
    pattern = (
        rf"<td[^>]*>\s*{re.escape(label)}\s*</td>\s*"
        rf"<td[^>]*class=\"priceValue[^\"]*\"[^>]*>\s*"
        rf"<span class=\"first_currency\">&#165;([\d,]+(?:\.\d+)?)</span>"
    )
    match = re.search(pattern, html, flags=re.S | re.I)
    return money_to_float(match.group(1)) if match else None


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(INPUT)

    extracted: dict[str, list[float | None]] = {
        "avg_salary": [],
        "monthly_cost_single_rmb": [],
        "monthly_cost_family_rmb": [],
        **{field: [] for field in PRICE_FIELDS},
    }

    for _, row in df.iterrows():
        city_en = str(row.get("city_name_en", "")).strip()
        city_zh = str(row.get("city_name_zh", "")).strip()
        if not city_en:
            for values in extracted.values():
                values.append(None)
            continue

        url = f"https://www.numbeo.com/cost-of-living/in/{quote(city_en)}?country=China"
        html = download(url, RAW_DIR / f"{city_en}.html")

        values = {
            "avg_salary": extract_salary(html),
            "monthly_cost_single_rmb": extract_summary_cost(html, "single person"),
            "monthly_cost_family_rmb": extract_summary_cost(html, "family of four"),
        }
        values.update({field: extract_price_by_label(html, label) for field, label in PRICE_FIELDS.items()})

        for field, value in values.items():
            extracted[field].append(value)
        print(
            f"{city_zh or city_en}: salary={values['avg_salary']}, "
            f"single_cost={values['monthly_cost_single_rmb']}, "
            f"rent_1br={values['rent_1br_city_centre_rmb']}"
        )

    for field, values in extracted.items():
        df[field] = values

    salary = pd.to_numeric(df["avg_salary"], errors="coerce")
    single_cost = pd.to_numeric(df["monthly_cost_single_rmb"], errors="coerce")
    rent = pd.to_numeric(df["rent_1br_city_centre_rmb"], errors="coerce")

    imputed = df["avg_salary"].isna() | df["monthly_cost_single_rmb"].isna() | df["rent_1br_city_centre_rmb"].isna()
    if imputed.any():
        cost_index = pd.to_numeric(df.get("cost_of_living_index"), errors="coerce")
        rent_index = pd.to_numeric(df.get("rent_index"), errors="coerce")
        power_index = pd.to_numeric(df.get("local_purchasing_power_index"), errors="coerce")

        salary_factor = (salary / power_index).replace([float("inf"), -float("inf")], pd.NA).median()
        single_cost_factor = (single_cost / cost_index).replace([float("inf"), -float("inf")], pd.NA).median()
        family_cost_factor = (
            pd.to_numeric(df["monthly_cost_family_rmb"], errors="coerce") / cost_index
        ).replace([float("inf"), -float("inf")], pd.NA).median()
        rent_factor = (rent / rent_index).replace([float("inf"), -float("inf")], pd.NA).median()
        rent_outside_factor = (
            pd.to_numeric(df["rent_1br_outside_centre_rmb"], errors="coerce") / rent_index
        ).replace([float("inf"), -float("inf")], pd.NA).median()
        rent_3br_factor = (
            pd.to_numeric(df["rent_3br_city_centre_rmb"], errors="coerce") / rent_index
        ).replace([float("inf"), -float("inf")], pd.NA).median()
        rent_3br_outside_factor = (
            pd.to_numeric(df["rent_3br_outside_centre_rmb"], errors="coerce") / rent_index
        ).replace([float("inf"), -float("inf")], pd.NA).median()

        df.loc[df["avg_salary"].isna(), "avg_salary"] = (power_index * salary_factor).round(2)
        df.loc[df["monthly_cost_single_rmb"].isna(), "monthly_cost_single_rmb"] = (
            cost_index * single_cost_factor
        ).round(1)
        df.loc[df["monthly_cost_family_rmb"].isna(), "monthly_cost_family_rmb"] = (
            cost_index * family_cost_factor
        ).round(1)
        df.loc[df["rent_1br_city_centre_rmb"].isna(), "rent_1br_city_centre_rmb"] = (
            rent_index * rent_factor
        ).round(1)
        df.loc[df["rent_1br_outside_centre_rmb"].isna(), "rent_1br_outside_centre_rmb"] = (
            rent_index * rent_outside_factor
        ).round(1)
        df.loc[df["rent_3br_city_centre_rmb"].isna(), "rent_3br_city_centre_rmb"] = (
            rent_index * rent_3br_factor
        ).round(1)
        df.loc[df["rent_3br_outside_centre_rmb"].isna(), "rent_3br_outside_centre_rmb"] = (
            rent_index * rent_3br_outside_factor
        ).round(1)

        for field in [
            "avg_salary",
            "monthly_cost_single_rmb",
            "monthly_cost_family_rmb",
            "rent_1br_city_centre_rmb",
            "rent_1br_outside_centre_rmb",
            "rent_3br_city_centre_rmb",
            "rent_3br_outside_centre_rmb",
        ]:
            tier_median = df.groupby("city_tier")[field].transform("median")
            region_median = df.groupby("region")[field].transform("median")
            overall_median = df[field].median()
            df[field] = df[field].fillna(tier_median).fillna(region_median).fillna(overall_median)

        df["rmb_data_note"] = (
            "Numbeo城市页可直接提取；少数缺失城市按同批城市参考指数与人民币金额的中位换算关系估算，"
            "若参考指数也缺失，则按同等级/同区域城市中位数补齐。"
        )

    salary = pd.to_numeric(df["avg_salary"], errors="coerce")
    single_cost = pd.to_numeric(df["monthly_cost_single_rmb"], errors="coerce")
    rent = pd.to_numeric(df["rent_1br_city_centre_rmb"], errors="coerce")
    df["salary_cost_ratio"] = salary / single_cost
    df["salary_rent_ratio"] = salary / rent
    df["monthly_balance_after_cost_rmb"] = salary - single_cost
    df["monthly_balance_after_rent_cost_rmb"] = salary - single_cost - rent

    df["salary_source"] = "Numbeo city page: Average Monthly Net Salary (After Tax)"
    df["living_cost_source"] = "Numbeo city page: estimated monthly costs excluding rent, RMB"
    df["rent_source"] = "Numbeo city page: monthly apartment rent, RMB"

    if "population_2020_million" not in df.columns and "population_2020" in df.columns:
        df["population_2020_million"] = pd.to_numeric(df["population_2020"], errors="coerce") / 1_000_000

    # 公开城市级岗位数量较难直接下载，这里用 GDP 与人口构造招聘热度代理，只作为辅助对比。
    gdp = pd.to_numeric(df.get("gdp_2024_cny_million"), errors="coerce")
    pop = pd.to_numeric(df.get("population_2020"), errors="coerce")
    df["job_market_proxy"] = ((gdp / gdp.max()) * 0.6 + (pop / pop.max()) * 0.4).round(4)
    df["job_count"] = pd.NA
    df["job_data_note"] = "未找到可直接公开下载的城市级岗位数量表；使用经济规模与人口规模构造招聘热度代理指标。"

    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(OUTPUT)


if __name__ == "__main__":
    main()
