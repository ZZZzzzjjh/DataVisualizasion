from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from charts import (
    balance_quadrant,
    bar_rank,
    compare_grouped_bars,
    education_structure_chart,
    grouped_metric_bar,
    industry_share_chart,
    multi_city_decision_heatmap,
    multi_city_gap_bars,
    position_salary_chart,
    scatter_salary_cost,
    score_table,
    single_city_benchmark,
    single_city_budget_waterfall,
    tier_box,
)
from data_loader import (
    build_ai_context,
    city_compare_table,
    display_columns,
    expected_columns_by_chapter,
    field_dictionary,
    filter_data,
    filter_job_structure,
    generate_rule_based_insights,
    job_data_available,
    load_city_data,
    load_job_structure,
    region_summary,
    summary_metrics,
)
from deepseek_client import analyze_with_deepseek
from styles import apply_style


st.set_page_config(page_title="城市就业与生活成本分析", page_icon="📊", layout="wide")
apply_style()


@st.cache_data(show_spinner=False)
def cached_base_data(cache_version: str = "schema-v8") -> pd.DataFrame:
    return load_city_data()


@st.cache_data(show_spinner=False)
def cached_job_structure(cache_version: str = "job-schema-v1") -> pd.DataFrame:
    return load_job_structure()


def fmt_rmb(value: float | int | None) -> str:
    if pd.isna(value):
        return "暂无"
    return f"{value:,.0f} 元/月"


def metric_delta(row: pd.Series, df: pd.DataFrame, column: str) -> str | None:
    value = row.get(column)
    median = df[column].median() if column in df.columns else pd.NA
    if pd.isna(value) or pd.isna(median):
        return None
    diff = value - median
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:,.0f} vs 中位数"


def normalize_metric(series: pd.Series, higher_better: bool = True) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    min_v, max_v = values.min(), values.max()
    if pd.isna(min_v) or pd.isna(max_v) or min_v == max_v:
        return pd.Series([0.5] * len(values), index=values.index)
    score = (values - min_v) / (max_v - min_v)
    return score if higher_better else 1 - score


DEFAULT_RECOMMEND_WEIGHTS = {
    "月结余": 0.38,
    "税后月薪": 0.24,
    "低房租": 0.18,
    "低生活成本": 0.12,
    "就业热度": 0.08,
}


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(max(float(value), 0.0) for value in weights.values())
    if total <= 0:
        return DEFAULT_RECOMMEND_WEIGHTS.copy()
    return {key: max(float(value), 0.0) / total for key, value in weights.items()}


def build_recommendations(
    df: pd.DataFrame,
    min_salary: int,
    max_rent: int,
    min_balance: int,
    top_k: int,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    data = df.copy()
    weights = normalize_weights(weights or DEFAULT_RECOMMEND_WEIGHTS)
    numeric_cols = [
        "avg_salary",
        "monthly_cost_single_rmb",
        "rent_1br_city_centre_rmb",
        "monthly_balance_after_rent_cost_rmb",
        "job_market_proxy",
    ]
    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    if min_salary > 0:
        data = data[data["avg_salary"] >= min_salary]
    if max_rent > 0:
        data = data[data["rent_1br_city_centre_rmb"] <= max_rent]
    if min_balance > 0:
        data = data[data["monthly_balance_after_rent_cost_rmb"] >= min_balance]
    if data.empty:
        return pd.DataFrame()

    data["_月结余得分"] = normalize_metric(data["monthly_balance_after_rent_cost_rmb"], True)
    data["_税后月薪得分"] = normalize_metric(data["avg_salary"], True)
    data["_低房租得分"] = normalize_metric(data["rent_1br_city_centre_rmb"], False)
    data["_低生活成本得分"] = normalize_metric(data["monthly_cost_single_rmb"], False)
    data["_就业热度得分"] = normalize_metric(data["job_market_proxy"], True)
    data["推荐分"] = (
        data["_月结余得分"] * weights["月结余"]
        + data["_税后月薪得分"] * weights["税后月薪"]
        + data["_低房租得分"] * weights["低房租"]
        + data["_低生活成本得分"] * weights["低生活成本"]
        + data["_就业热度得分"] * weights["就业热度"]
    )
    data["权重结构"] = (
        f"月结余 {weights['月结余']:.0%} / "
        f"月薪 {weights['税后月薪']:.0%} / "
        f"低房租 {weights['低房租']:.0%} / "
        f"低成本 {weights['低生活成本']:.0%} / "
        f"就业 {weights['就业热度']:.0%}"
    )
    data["推荐理由"] = data.apply(
        lambda row: (
            f"税后月薪约 {row['avg_salary']:,.0f} 元/月，"
            f"市中心一居室租金约 {row['rent_1br_city_centre_rmb']:,.0f} 元/月，"
            f"扣除生活成本和房租后约剩 {row['monthly_balance_after_rent_cost_rmb']:,.0f} 元/月。"
        ),
        axis=1,
    )
    cols = [
        "display_city",
        "region",
        "city_tier",
        "avg_salary",
        "monthly_cost_single_rmb",
        "rent_1br_city_centre_rmb",
        "monthly_balance_after_rent_cost_rmb",
        "city_type",
        "推荐分",
        "权重结构",
        "推荐理由",
    ]
    out = data[[col for col in cols if col in data.columns]].sort_values("推荐分", ascending=False).head(top_k)
    return out.rename(
        columns={
            "display_city": "城市",
            "region": "区域",
            "city_tier": "城市等级",
            "avg_salary": "税后月薪（元/月）",
            "monthly_cost_single_rmb": "单人生活成本（元/月）",
            "rent_1br_city_centre_rmb": "市中心一居室租金（元/月）",
            "monthly_balance_after_rent_cost_rmb": "扣除生活成本和房租后结余（元/月）",
            "city_type": "城市类型",
        }
    )


def recommendation_context(table: pd.DataFrame) -> str:
    if table.empty:
        return "没有满足硬性筛选条件的候选城市。"
    return table.to_csv(index=False)


base_df = cached_base_data()
base_job_df = cached_job_structure()

st.title("城市就业与生活成本分析")

with st.sidebar:
    st.header("分析设置")
    regions = st.multiselect("区域", sorted(base_df["region"].dropna().unique()))
    tiers = st.multiselect("城市等级", sorted(base_df["city_tier"].dropna().unique()))

    filtered = filter_data(base_df, regions, tiers, [])
    if filtered.empty:
        st.warning("当前筛选没有城市，已临时恢复全部城市。")
        filtered = base_df

    city_options = sorted(filtered["display_city"].dropna().unique())
    top_n = st.slider("排名展示数量", min_value=5, max_value=20, value=10)

    st.divider()
    analysis_mode = st.radio("交互模式", ["单城市画像", "多城市对比"])
    preferred = ["杭州", "北京", "上海", "深圳", "成都"]
    default_city = next((city for city in preferred if city in city_options), city_options[0])

    if analysis_mode == "单城市画像":
        selected_city = st.selectbox("观察城市", city_options, index=city_options.index(default_city))
        compare_cities: list[str] = []
    else:
        smart_defaults = [city for city in preferred if city in city_options]
        if len(smart_defaults) < 2:
            smart_defaults = city_options[: min(4, len(city_options))]
        compare_cities = st.multiselect("对比城市", city_options, default=smart_defaults[:5])
        selected_city = compare_cities[0] if compare_cities else default_city

selected_row_df = filtered[filtered["display_city"] == selected_city]
selected_row = selected_row_df.iloc[0] if not selected_row_df.empty else pd.Series(dtype="object")
selected_for_ai = selected_row_df if analysis_mode == "单城市画像" else filtered[filtered["display_city"].isin(compare_cities)]
if selected_for_ai.empty:
    selected_for_ai = filtered

job_cities = [selected_city] if analysis_mode == "单城市画像" else compare_cities
job_filtered = filter_job_structure(base_job_df, regions, tiers, job_cities)
if job_filtered.empty:
    job_filtered = filter_job_structure(base_job_df, regions, tiers, [])

metric_items = list(summary_metrics(filtered).items())
for row_start in range(0, len(metric_items), 3):
    cols = st.columns(min(3, len(metric_items) - row_start))
    for col, (label, value) in zip(cols, metric_items[row_start : row_start + 3]):
        col.metric(label, value)

with st.expander("当前筛选的自动洞察", expanded=False):
    for item in generate_rule_based_insights(filtered):
        st.markdown(f"- {item}")

if not job_data_available(filtered):
    st.warning("当前薪资、生活成本或租金字段不足，部分图表会显示为暂无数据。")

tab_overview, tab_workspace, tab_jobs, tab_cost, tab_match, tab_segments, tab_recommend, tab_ai, tab_data = st.tabs(
    ["总览", "城市工作台", "就业结构", "成本收支", "薪资匹配", "城市分型", "推荐助手", "AI 助手", "数据管理"]
)

with tab_overview:
    st.subheader("城市概览")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(bar_rank(filtered, "gdp_2024_cny_billion", "GDP 规模对比", "亿元", top_n), width="stretch", key="macro_gdp")
    with c2:
        st.plotly_chart(bar_rank(filtered, "population_2020_million", "人口规模对比", "百万人", top_n), width="stretch", key="macro_population")
    st.plotly_chart(tier_box(filtered, "gdp_per_capita_2024_cny", "不同城市等级的人均 GDP 分布", "元/人"), width="stretch", key="macro_gdp_pc")

with tab_jobs:
    st.subheader("就业结构")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(bar_rank(filtered, "avg_salary", "税后月薪对比", "元/月", top_n), width="stretch", key="job_salary")
    with c2:
        st.plotly_chart(bar_rank(filtered, "job_market_proxy", "招聘热度代理对比", "", top_n), width="stretch", key="job_proxy")

    st.plotly_chart(industry_share_chart(job_filtered, job_cities), width="stretch", key="job_industry_structure")
    c3, c4 = st.columns([1.15, 0.85])
    with c3:
        st.plotly_chart(position_salary_chart(job_filtered, job_cities, top_n=12), width="stretch", key="job_position_salary")
    with c4:
        st.plotly_chart(education_structure_chart(job_filtered, job_cities), width="stretch", key="job_education_structure")

with tab_cost:
    st.subheader("成本收支")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(bar_rank(filtered, "monthly_cost_single_rmb", "单人月生活成本对比", "元/月", top_n), width="stretch", key="cost_single")
    with c2:
        st.plotly_chart(bar_rank(filtered, "rent_1br_city_centre_rmb", "市中心一居室月租金对比", "元/月", top_n), width="stretch", key="cost_rent")
    st.plotly_chart(bar_rank(filtered, "monthly_balance_after_cost_rmb", "扣除单人生活成本后月结余", "元/月", top_n), width="stretch", key="cost_balance")

with tab_match:
    st.subheader("薪资匹配")
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(scatter_salary_cost(filtered), width="stretch", key="match_salary_cost")
    with c2:
        st.plotly_chart(balance_quadrant(filtered), width="stretch", key="match_balance")
with tab_segments:
    st.subheader("城市分型")
    st.plotly_chart(balance_quadrant(filtered), width="stretch", key="model_quadrant")
    st.markdown("#### 按实际月结余排序")
    st.dataframe(
        score_table(filtered),
        width="stretch",
        hide_index=True,
        column_config={
            "税后月薪（元/月）": st.column_config.NumberColumn(format="%.0f"),
            "单人月生活成本（元/月）": st.column_config.NumberColumn(format="%.0f"),
            "市中心一居室租金（元/月）": st.column_config.NumberColumn(format="%.0f"),
            "扣除生活成本后月结余（元/月）": st.column_config.NumberColumn(format="%.0f"),
            "扣除生活成本和房租后月结余（元/月）": st.column_config.NumberColumn(format="%.0f"),
        },
    )

with tab_workspace:
    if analysis_mode == "单城市画像":
        st.subheader(f"{selected_city} 城市画像")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("税后月薪", fmt_rmb(selected_row.get("avg_salary")), metric_delta(selected_row, filtered, "avg_salary"))
        k2.metric("单人生活成本", fmt_rmb(selected_row.get("monthly_cost_single_rmb")), metric_delta(selected_row, filtered, "monthly_cost_single_rmb"), delta_color="inverse")
        k3.metric("市中心一居室租金", fmt_rmb(selected_row.get("rent_1br_city_centre_rmb")), metric_delta(selected_row, filtered, "rent_1br_city_centre_rmb"), delta_color="inverse")
        k4.metric("扣除生活成本和房租后结余", fmt_rmb(selected_row.get("monthly_balance_after_rent_cost_rmb")), metric_delta(selected_row, filtered, "monthly_balance_after_rent_cost_rmb"))
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(single_city_budget_waterfall(filtered, selected_city), width="stretch", key="single_budget")
        with c2:
            st.plotly_chart(single_city_benchmark(filtered, selected_city), width="stretch", key="single_benchmark")
        st.markdown("#### 城市详情")
        st.dataframe(city_compare_table(filtered, [selected_city]), width="stretch", hide_index=True)
    else:
        st.subheader("多城市对比")
        if len(compare_cities) < 2:
            st.warning("请至少选择两个城市，才能进行差异化对比。")
        else:
            st.plotly_chart(compare_grouped_bars(filtered, compare_cities), width="stretch", key="multi_compare")
            c1, c2 = st.columns([1.15, 0.85])
            with c1:
                st.plotly_chart(multi_city_gap_bars(filtered, compare_cities), width="stretch", key="multi_gap")
            with c2:
                st.plotly_chart(multi_city_decision_heatmap(filtered, compare_cities), width="stretch", key="multi_heatmap")
            st.markdown("#### 对比表")
            st.dataframe(city_compare_table(filtered, compare_cities), width="stretch", hide_index=True)

    region_tab, tier_tab = st.tabs(["区域对比", "城市等级对比"])
    with region_tab:
        rs = region_summary(filtered, "region")
        st.plotly_chart(grouped_metric_bar(rs, "平均月结余元", "不同区域平均月结余对比", "元/月"), width="stretch", key="region_balance")
        st.dataframe(rs, width="stretch", hide_index=True)
    with tier_tab:
        ts = region_summary(filtered, "city_tier")
        st.plotly_chart(grouped_metric_bar(ts, "平均单人月生活成本元", "不同城市等级单人月生活成本对比", "元/月"), width="stretch", key="tier_cost")
        st.dataframe(ts, width="stretch", hide_index=True)

with tab_recommend:
    st.subheader("推荐助手")
    st.caption("先用硬性条件筛掉不符合要求的城市，再用可调权重计算推荐分；权重会自动归一化为 100%。")
    requirement = st.text_area(
        "你的城市选择要求",
        value="我是应届毕业生，希望城市就业机会不错，房租不要太高，扣除生活成本和房租后还能有一定结余。",
        placeholder="例如：想去华东或新一线城市，税后月薪最好 8000 以上，房租不要太贵，适合毕业生长期发展。",
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        min_salary = st.number_input("最低税后月薪", min_value=0, max_value=20000, value=7000, step=500, help="单位：元/月")
    with c2:
        max_rent = st.number_input("最高可接受房租", min_value=0, max_value=15000, value=4500, step=500, help="单位：元/月，0 表示不限制")
    with c3:
        min_balance = st.number_input("最低实际月结余", min_value=0, max_value=15000, value=1000, step=500, help="扣除生活成本和房租后的结余，单位：元/月")
    with c4:
        top_k = st.number_input("推荐数量", min_value=3, max_value=10, value=5, step=1)

    with st.expander("推荐模型权重设置", expanded=True):
        w1, w2, w3, w4, w5 = st.columns(5)
        with w1:
            weight_balance = st.slider("月结余", 0, 60, 38, help="越高越偏向扣除生活成本和房租后剩余更多的城市")
        with w2:
            weight_salary = st.slider("月薪", 0, 60, 24, help="越高越偏向税后月薪更高的城市")
        with w3:
            weight_rent = st.slider("低房租", 0, 60, 18, help="越高越偏向市中心一居室租金更低的城市")
        with w4:
            weight_cost = st.slider("低生活成本", 0, 60, 12, help="越高越偏向日常生活成本更低的城市")
        with w5:
            weight_job = st.slider("就业热度", 0, 60, 8, help="越高越偏向就业热度代理指标更高的城市")

    recommend_weights = normalize_weights(
        {
            "月结余": weight_balance,
            "税后月薪": weight_salary,
            "低房租": weight_rent,
            "低生活成本": weight_cost,
            "就业热度": weight_job,
        }
    )
    st.caption(
        "当前归一化权重："
        f"月结余 {recommend_weights['月结余']:.0%}，"
        f"月薪 {recommend_weights['税后月薪']:.0%}，"
        f"低房租 {recommend_weights['低房租']:.0%}，"
        f"低生活成本 {recommend_weights['低生活成本']:.0%}，"
        f"就业热度 {recommend_weights['就业热度']:.0%}。"
    )

    recommendations = build_recommendations(filtered, min_salary, max_rent, min_balance, int(top_k), recommend_weights)
    if recommendations.empty:
        st.warning("当前硬性条件下没有城市满足要求，可以适当降低最低月薪、提高可接受房租或减少最低结余。")
    else:
        st.markdown("#### 数据推荐结果")
        st.dataframe(
            recommendations,
            width="stretch",
            hide_index=True,
            column_config={
                "税后月薪（元/月）": st.column_config.NumberColumn(format="%.0f"),
                "单人生活成本（元/月）": st.column_config.NumberColumn(format="%.0f"),
                "市中心一居室租金（元/月）": st.column_config.NumberColumn(format="%.0f"),
                "扣除生活成本和房租后结余（元/月）": st.column_config.NumberColumn(format="%.0f"),
                "推荐分": st.column_config.ProgressColumn(format="%.2f", min_value=0, max_value=1),
            },
        )
    if st.button("让 DeepSeek 解释推荐", type="primary", disabled=recommendations.empty):
        prompt = f"""
用户城市选择需求：
{requirement}

硬性条件：
- 最低税后月薪：{min_salary} 元/月
- 最高可接受房租：{max_rent} 元/月
- 最低实际月结余：{min_balance} 元/月
- 当前推荐权重：{recommendations["权重结构"].iloc[0] if not recommendations.empty and "权重结构" in recommendations.columns else "默认权重"}

请基于候选城市数据推荐 3-5 个城市，并说明推荐排序、每个城市适合的原因、需要注意的风险，以及可以直接写进课程报告的一段总结。
"""
        with st.spinner("正在调用 DeepSeek 生成推荐解释..."):
            st.markdown(analyze_with_deepseek(prompt, recommendation_context(recommendations)))
with tab_ai:
    st.subheader("AI 助手")
    preset_options = (
        [
            f"请评价{selected_city}的月薪、生活成本、房租、就业结构和实际月结余，写成报告结论。",
            f"请说明{selected_city}适不适合毕业生就业生活，并给出理由。",
        ]
        if analysis_mode == "单城市画像"
        else [
            "请比较所选城市的月薪、生活成本、房租、就业结构和实际月结余差异。",
            "请从毕业生就业城市选择角度，对所选城市给出排序建议。",
            "请总结所选城市中高薪高成本、均衡发展和收入压力型城市的差别。",
        ]
    )
    preset = st.selectbox("分析问题", preset_options)
    custom = st.text_area("自定义问题", placeholder="例如：比较杭州、上海、成都的月薪、行业结构和实际月结余。")
    question = custom.strip() or preset
    if st.button("生成 AI 建议", type="primary"):
        with st.spinner("正在调用 DeepSeek 生成分析..."):
            st.markdown(analyze_with_deepseek(question, build_ai_context(selected_for_ai)))
with tab_data:
    st.subheader("数据管理")
    st.info(
        "数据可信度说明：GDP、人口等宏观指标来自公开统计资料或公开网页整理；"
        "生活成本和租金主要参考 Numbeo，适合做城市间相对比较；"
        "就业结构表为课程项目补充数据，不代表实时全量招聘岗位。"
    )
    st.dataframe(expected_columns_by_chapter(), width="stretch", hide_index=True)
    st.subheader("字段字典")
    st.dataframe(field_dictionary(), width="stretch", hide_index=True)
    st.subheader("当前筛选后的数据")
    st.dataframe(display_columns(filtered), width="stretch", hide_index=True)
