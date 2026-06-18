from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CLEANED_DIR = DATA_DIR / "cleaned"


def ensure_dirs() -> None:
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)


def remove_footnotes(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value)
    text = re.sub(r"\[[^\]]*\]", "", text)
    text = re.sub(r"[#†‡*~⍟]", "", text)
    return text.strip()


def to_number(value: object) -> float | None:
    if pd.isna(value):
        return None
    text = remove_footnotes(value)
    text = text.replace(",", "").replace("%", "").replace("+", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group())


def min_max(series: pd.Series, reverse: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    min_value = values.min()
    max_value = values.max()
    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        result = pd.Series([None] * len(values), index=values.index)
    else:
        result = (values - min_value) / (max_value - min_value)
    if reverse:
        result = 1 - result
    return result.round(4)


def clean_city_basic() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / "city_basic.csv")
    df = df.rename(
        columns={
            "city_zh": "city_name_zh",
            "city_en": "city_name_en",
            "province": "province_zh",
        }
    )
    for col in ["city_name_zh", "city_name_en", "province_zh", "region", "city_tier"]:
        df[col] = df[col].map(remove_footnotes)
    df = df.drop_duplicates(subset=["city_name_zh", "city_name_en"])
    df.to_csv(CLEANED_DIR / "city_basic_clean.csv", index=False, encoding="utf-8-sig")
    return df


def clean_cost() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / "city_cost_numbeo.csv")
    df = df.rename(columns={"city_zh": "city_name_zh", "city_en": "city_name_en"})
    df["city_name_zh"] = df["city_name_zh"].map(remove_footnotes)
    df["city_name_en"] = df["city_name_en"].map(remove_footnotes)

    numeric_cols = [
        "cost_of_living_index",
        "rent_index",
        "cost_plus_rent_index",
        "groceries_index",
        "restaurant_price_index",
        "local_purchasing_power_index",
    ]
    for col in numeric_cols:
        df[col] = df[col].map(to_number)

    df = df.drop_duplicates(subset=["city_name_en"])
    df.to_csv(CLEANED_DIR / "city_cost_clean.csv", index=False, encoding="utf-8-sig")
    return df


def clean_gdp() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / "city_gdp_wikipedia.csv")

    en_col = next(col for col in df.columns if "cities" in col.lower())
    zh_col = next((col for col in df.columns if "城市" in col), None)
    rank_col = next((col for col in df.columns if "rank" in col.lower()), None)
    province_col = next((col for col in df.columns if "province" in col.lower()), None)
    gdp_2024_cny_col = next(
        col for col in df.columns if "GDP in 2024" in col and "(CNY)" in col
    )
    gdp_2024_usd_col = next(
        col for col in df.columns if "GDP in 2024" in col and "(USD)" in col
    )

    out = pd.DataFrame(
        {
            "gdp_rank": df[rank_col].map(to_number) if rank_col else None,
            "city_name_en": df[en_col].map(remove_footnotes),
            "city_name_zh": df[zh_col].map(remove_footnotes) if zh_col else "",
            "province_en": df[province_col].map(remove_footnotes) if province_col else "",
            "gdp_2024_cny_million": df[gdp_2024_cny_col].map(to_number),
            "gdp_2024_usd_million": df[gdp_2024_usd_col].map(to_number),
            "source": df["source"],
        }
    )
    out = out.dropna(subset=["city_name_en"])
    out = out.drop_duplicates(subset=["city_name_en"])
    out.to_csv(CLEANED_DIR / "city_gdp_clean.csv", index=False, encoding="utf-8-sig")
    return out


def clean_population() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED_DIR / "city_population_wikipedia.csv")

    city_col = "City"
    province_col = "Province"
    pop_2020_col = next(col for col in df.columns if "2020 Census" in col)
    pop_2010_col = next(col for col in df.columns if "2010 Census" in col)
    change_col = next(col for col in df.columns if "change" in col.lower())

    out = pd.DataFrame(
        {
            "city_name_en": df[city_col].map(remove_footnotes),
            "province_en": df[province_col].map(remove_footnotes),
            "population_2020": df[pop_2020_col].map(to_number),
            "population_2010": df[pop_2010_col].map(to_number),
            "population_change_percent": df[change_col].map(to_number),
            "source": df["source"],
        }
    )
    out = out.dropna(subset=["city_name_en"])
    out = out.drop_duplicates(subset=["city_name_en"])
    out.to_csv(CLEANED_DIR / "city_population_clean.csv", index=False, encoding="utf-8-sig")
    return out


def build_city_panel(
    basic: pd.DataFrame,
    cost: pd.DataFrame,
    gdp: pd.DataFrame,
    population: pd.DataFrame,
) -> pd.DataFrame:
    panel = basic.merge(
        gdp[
            [
                "city_name_en",
                "gdp_rank",
                "gdp_2024_cny_million",
                "gdp_2024_usd_million",
            ]
        ],
        on="city_name_en",
        how="left",
    )
    panel = panel.merge(
        population[
            [
                "city_name_en",
                "population_2020",
                "population_2010",
                "population_change_percent",
            ]
        ],
        on="city_name_en",
        how="left",
    )
    panel = panel.merge(
        cost.drop(columns=["city_name_zh"], errors="ignore"),
        on="city_name_en",
        how="left",
    )

    panel["gdp_per_capita_2024_cny"] = (
        panel["gdp_2024_cny_million"] * 1_000_000 / panel["population_2020"]
    ).round(2)

    panel["gdp_index"] = min_max(panel["gdp_2024_cny_million"])
    panel["population_index"] = min_max(panel["population_2020"])
    panel["living_cost_index_norm"] = min_max(panel["cost_of_living_index"], reverse=True)
    panel["rent_index_norm"] = min_max(panel["rent_index"], reverse=True)
    panel["purchasing_power_index_norm"] = min_max(panel["local_purchasing_power_index"])

    panel["city_living_value_reference_index"] = (
        panel[
            [
                "gdp_index",
                "living_cost_index_norm",
                "rent_index_norm",
                "purchasing_power_index_norm",
            ]
        ].mean(axis=1, skipna=True)
    ).round(4)

    panel["missing_key_fields"] = panel[
        [
            "gdp_2024_cny_million",
            "population_2020",
            "cost_of_living_index",
            "rent_index",
            "local_purchasing_power_index",
        ]
    ].isna().sum(axis=1)

    panel.to_csv(CLEANED_DIR / "city_panel_clean.csv", index=False, encoding="utf-8-sig")
    return panel


def write_quality_report(panel: pd.DataFrame) -> None:
    rows = []
    for col in panel.columns:
        rows.append(
            {
                "field": col,
                "missing_count": int(panel[col].isna().sum()),
                "missing_rate": round(float(panel[col].isna().mean()), 4),
                "unique_count": int(panel[col].nunique(dropna=True)),
            }
        )
    pd.DataFrame(rows).to_csv(
        CLEANED_DIR / "data_quality_report.csv", index=False, encoding="utf-8-sig"
    )


def main() -> None:
    ensure_dirs()
    basic = clean_city_basic()
    cost = clean_cost()
    gdp = clean_gdp()
    population = clean_population()
    panel = build_city_panel(basic, cost, gdp, population)
    write_quality_report(panel)
    print("数据清洗完成，结果已保存到 data/cleaned。")


if __name__ == "__main__":
    main()
