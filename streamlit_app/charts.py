from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


COLOR_SEQ = ["#0F4C81", "#1B8A8F", "#D89C27", "#C65D7B", "#64748B", "#74A9D8", "#B7D4EA"]
CITY_TYPE_COLORS = {
    "高薪高成本": "#0F4C81",
    "高薪较低成本": "#1B8A8F",
    "均衡发展型": "#D89C27",
    "收入压力型": "#C65D7B",
    "数据不足": "#94A3B8",
}
TYPE_ORDER = ["高薪较低成本", "均衡发展型", "高薪高成本", "收入压力型", "数据不足"]
RMB_METRICS = {
    "税后月薪": "avg_salary",
    "单人生活成本": "monthly_cost_single_rmb",
    "市中心一居室租金": "rent_1br_city_centre_rmb",
    "扣除生活成本后结余": "monthly_balance_after_cost_rmb",
    "扣除生活成本和房租后结余": "monthly_balance_after_rent_cost_rmb",
}


def empty_chart(message: str = "暂无可展示数据") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 18, "color": "#64748B"},
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20))
    return fig


def _text_template(unit: str) -> str:
    if "元" in unit or "亿元" in unit:
        return "%{text:,.0f}"
    return "%{text:.2f}"


def _focus_city_labels(data: pd.DataFrame, x_col: str, y_col: str, max_labels: int = 9) -> pd.Series:
    """Label only analytical outliers so small scatter charts stay readable."""
    if data.empty:
        return pd.Series(dtype="object")

    focus: set[int] = set()
    for col in [x_col, y_col]:
        values = pd.to_numeric(data[col], errors="coerce")
        if values.notna().sum() < 2:
            continue
        focus.add(values.idxmax())
        focus.add(values.idxmin())

    if len(focus) < max_labels:
        x = pd.to_numeric(data[x_col], errors="coerce")
        y = pd.to_numeric(data[y_col], errors="coerce")
        x_z = (x - x.mean()) / (x.std() or 1)
        y_z = (y - y.mean()) / (y.std() or 1)
        distance = (x_z.pow(2) + y_z.pow(2)).sort_values(ascending=False)
        focus.update(distance.head(max_labels).index.tolist())

    focus = set(list(focus)[:max_labels])
    return data.apply(lambda row: row["display_city"] if row.name in focus else "", axis=1)


def _polish_xy(fig: go.Figure, title: str, x_title: str, y_title: str, height: int = 500) -> go.Figure:
    fig.update_traces(
        marker=dict(line=dict(width=1, color="#FFFFFF"), opacity=0.82),
        textfont=dict(size=12, color="#334155"),
        selector=dict(mode="markers+text"),
    )
    fig.update_layout(
        title=title,
        height=height,
        template="simple_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Microsoft YaHei, Arial, sans-serif", size=13, color="#334155"),
        title_font=dict(size=18, color="#1F2937"),
        xaxis_title=x_title,
        yaxis_title=y_title,
        legend_title_text="城市类型",
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
        margin=dict(l=54, r=38, t=58, b=118),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E5E7EB", zeroline=False, ticks="")
    fig.update_yaxes(showgrid=True, gridcolor="#E5E7EB", zeroline=False, ticks="")
    return fig


def _legend_bottom(fig: go.Figure, bottom: int = 104) -> go.Figure:
    fig.update_layout(
        legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="center", x=0.5, title=""),
        margin=dict(b=bottom),
    )
    return fig


def bar_rank(df: pd.DataFrame, column: str, title: str, unit: str = "", top_n: int = 10) -> go.Figure:
    if column not in df.columns:
        return empty_chart(f"缺少字段：{column}")
    data = df[["display_city", column]].dropna().sort_values(column, ascending=True).tail(top_n)
    if data.empty:
        return empty_chart()
    fig = px.bar(
        data,
        x=column,
        y="display_city",
        orientation="h",
        text=column,
        color=column,
        color_continuous_scale="Blues",
    )
    fig.update_traces(texttemplate=_text_template(unit), textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=title,
        height=420,
        xaxis_title=unit,
        yaxis_title="",
        coloraxis_showscale=False,
        margin=dict(l=95, r=50, t=60, b=40),
    )
    return fig


def categorical_bar(df: pd.DataFrame, column: str, title: str) -> go.Figure:
    if column not in df.columns:
        return empty_chart(f"缺少字段：{column}")
    data = df[column].dropna()
    if data.empty:
        return empty_chart("暂无分类数据")
    counts = data.value_counts().reset_index()
    counts.columns = ["类别", "数量"]
    fig = px.bar(counts, x="类别", y="数量", text="数量", color="数量", color_continuous_scale="Blues")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=title,
        height=380,
        xaxis_title="",
        yaxis_title="数量",
        coloraxis_showscale=False,
        margin=dict(l=40, r=40, t=60, b=80),
    )
    return fig


def tier_box(df: pd.DataFrame, column: str, title: str, y_title: str = "指标值") -> go.Figure:
    if column not in df.columns:
        return empty_chart(f"缺少字段：{column}")
    data = df.dropna(subset=[column])
    if data.empty:
        return empty_chart()
    fig = px.box(
        data,
        x="city_tier",
        y=column,
        color="city_tier",
        points="all",
        hover_name="display_city",
        color_discrete_sequence=COLOR_SEQ,
    )
    fig.update_layout(
        title=title,
        height=380,
        xaxis_title="城市等级",
        yaxis_title=y_title,
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def city_type_donut(df: pd.DataFrame) -> go.Figure:
    if "city_type" not in df.columns:
        return empty_chart("缺少城市类型字段")
    data = df["city_type"].dropna().value_counts().rename_axis("城市类型").reset_index(name="城市数量")
    if data.empty:
        return empty_chart("暂无城市类型数据")
    fig = px.pie(
        data,
        names="城市类型",
        values="城市数量",
        hole=0.58,
        color="城市类型",
        color_discrete_map=CITY_TYPE_COLORS,
        category_orders={"城市类型": TYPE_ORDER},
    )
    fig.update_traces(textinfo="label+value", marker=dict(line=dict(color="#FFFFFF", width=2)))
    fig.update_layout(
        title="城市类型分布",
        height=390,
        template="simple_white",
        paper_bgcolor="#FFFFFF",
        font=dict(family="Microsoft YaHei, Arial, sans-serif", size=13, color="#334155"),
        showlegend=False,
        margin=dict(l=30, r=30, t=60, b=30),
    )
    return fig


def income_allocation_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    required = [
        "display_city",
        "avg_salary",
        "monthly_cost_single_rmb",
        "rent_1br_city_centre_rmb",
        "monthly_balance_after_rent_cost_rmb",
    ]
    if any(col not in df.columns for col in required):
        return empty_chart("缺少收入或支出字段")

    data = (
        df[required]
        .dropna()
        .sort_values("monthly_balance_after_rent_cost_rmb", ascending=False)
        .head(top_n)
        .copy()
    )
    if data.empty:
        return empty_chart()

    data["实际结余"] = data["monthly_balance_after_rent_cost_rmb"].clip(lower=0)
    data["收支缺口"] = data["monthly_balance_after_rent_cost_rmb"].clip(upper=0)
    plot_df = data.melt(
        id_vars="display_city",
        value_vars=["monthly_cost_single_rmb", "rent_1br_city_centre_rmb", "实际结余", "收支缺口"],
        var_name="项目",
        value_name="金额（元/月）",
    )
    label_map = {
        "monthly_cost_single_rmb": "生活成本",
        "rent_1br_city_centre_rmb": "房租",
        "实际结余": "实际结余",
        "收支缺口": "收支缺口",
    }
    plot_df["项目"] = plot_df["项目"].map(label_map)
    fig = px.bar(
        plot_df,
        x="金额（元/月）",
        y="display_city",
        color="项目",
        orientation="h",
        barmode="relative",
        text="金额（元/月）",
        color_discrete_map={
            "生活成本": "#74A9D8",
            "房租": "#D89C27",
            "实际结余": "#1B8A8F",
            "收支缺口": "#C65D7B",
        },
        category_orders={"项目": ["生活成本", "房租", "实际结余", "收支缺口"]},
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="inside", insidetextanchor="middle")
    fig.update_layout(
        title="月薪去向拆解",
        height=max(420, 36 * len(data) + 160),
        template="simple_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Microsoft YaHei, Arial, sans-serif", size=13, color="#334155"),
        xaxis_title="元/月",
        yaxis_title="",
        margin=dict(l=80, r=40, t=62, b=106),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#E5E7EB", zeroline=True, zerolinecolor="#64748B", ticks="")
    fig.update_yaxes(autorange="reversed", ticks="")
    return _legend_bottom(fig, bottom=112)


def scatter_salary_cost(df: pd.DataFrame) -> go.Figure:
    needed = ["avg_salary", "monthly_cost_single_rmb"]
    if any(col not in df.columns for col in needed):
        return empty_chart("缺少税后月薪或单人月生活成本字段")
    data = df.dropna(subset=needed)
    if data.empty:
        return empty_chart()
    data = data.copy()
    data["重点标注"] = _focus_city_labels(data, "monthly_cost_single_rmb", "avg_salary", max_labels=8)
    size_col = "rent_1br_city_centre_rmb" if data["rent_1br_city_centre_rmb"].notna().any() else None
    fig = px.scatter(
        data,
        x="monthly_cost_single_rmb",
        y="avg_salary",
        size=size_col,
        color="city_type",
        hover_name="display_city",
        text="重点标注",
        color_discrete_map=CITY_TYPE_COLORS,
        category_orders={"city_type": TYPE_ORDER},
        labels={
            "monthly_cost_single_rmb": "单人月生活成本（元/月，不含房租）",
            "avg_salary": "税后月薪（元/月）",
            "rent_1br_city_centre_rmb": "市中心一居室租金（元/月）",
            "city_type": "城市类型",
        },
    )
    fig.update_traces(textposition="top center", cliponaxis=False)
    return _polish_xy(
        fig,
        "税后月薪与单人月生活成本关系",
        "单人月生活成本（元/月，不含房租）",
        "税后月薪（元/月）",
        480,
    )


def balance_quadrant(df: pd.DataFrame) -> go.Figure:
    needed = ["avg_salary", "monthly_balance_after_rent_cost_rmb"]
    if any(col not in df.columns for col in needed):
        return empty_chart("缺少月薪或月结余字段")
    data = df.dropna(subset=needed)
    if data.empty:
        return empty_chart()
    data = data.copy()
    x_mid = data["avg_salary"].median()
    y_mid = data["monthly_balance_after_rent_cost_rmb"].median()
    data["重点标注"] = _focus_city_labels(data, "avg_salary", "monthly_balance_after_rent_cost_rmb", max_labels=10)
    fig = px.scatter(
        data,
        x="avg_salary",
        y="monthly_balance_after_rent_cost_rmb",
        size="monthly_cost_single_rmb",
        color="city_type",
        hover_name="display_city",
        text="重点标注",
        color_discrete_map=CITY_TYPE_COLORS,
        category_orders={"city_type": TYPE_ORDER},
        labels={
            "avg_salary": "税后月薪（元/月）",
            "monthly_balance_after_rent_cost_rmb": "扣除生活成本和房租后月结余（元/月）",
            "monthly_cost_single_rmb": "单人月生活成本（元/月）",
            "city_type": "城市类型",
        },
    )
    fig.add_vline(x=x_mid, line_dash="dash", line_color="#64748B")
    fig.add_hline(y=y_mid, line_dash="dash", line_color="#64748B")
    fig.update_traces(textposition="top center", cliponaxis=False)
    return _polish_xy(
        fig,
        "月薪与实际月结余四象限",
        "税后月薪（元/月）",
        "扣除生活成本和房租后月结余（元/月）",
        520,
    )


def single_city_budget_waterfall(df: pd.DataFrame, city: str) -> go.Figure:
    data = df[df["display_city"] == city]
    if data.empty:
        return empty_chart("未找到该城市")
    row = data.iloc[0]
    required = ["avg_salary", "monthly_cost_single_rmb", "rent_1br_city_centre_rmb"]
    if any(pd.isna(row.get(col)) for col in required):
        return empty_chart("该城市缺少月薪、生活成本或租金数据")

    salary = row["avg_salary"]
    living = row["monthly_cost_single_rmb"]
    rent = row["rent_1br_city_centre_rmb"]
    balance = salary - living - rent
    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["税后月薪", "生活成本", "市中心一居室租金", "剩余金额"],
            y=[salary, -living, -rent, balance],
            text=[f"{salary:,.0f}", f"-{living:,.0f}", f"-{rent:,.0f}", f"{balance:,.0f}"],
            textposition="outside",
            connector={"line": {"color": "#CBD5E1"}},
            increasing={"marker": {"color": "#0F4C81"}},
            decreasing={"marker": {"color": "#9CC7E6"}},
            totals={"marker": {"color": "#2F6F9F" if balance >= 0 else "#5B6F95"}},
        )
    )
    fig.update_layout(
        title=f"{city} 月收入与主要支出拆解",
        height=420,
        yaxis_title="元/月",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return fig


def single_city_benchmark(df: pd.DataFrame, city: str) -> go.Figure:
    data = df.copy()
    row_df = data[data["display_city"] == city]
    if row_df.empty:
        return empty_chart("未找到该城市")
    row = row_df.iloc[0]
    rows = []
    for label, col in RMB_METRICS.items():
        if col not in data.columns or pd.isna(row.get(col)):
            continue
        rows.append({"指标": label, "对象": city, "金额（元/月）": row[col]})
        rows.append({"指标": label, "对象": "当前样本中位数", "金额（元/月）": data[col].median()})
    plot_df = pd.DataFrame(rows).dropna()
    if plot_df.empty:
        return empty_chart()
    fig = px.bar(
        plot_df,
        x="指标",
        y="金额（元/月）",
        color="对象",
        barmode="group",
        color_discrete_sequence=["#0F4C81", "#9CC7E6"],
    )
    fig.update_layout(
        title=f"{city} 与样本中位数对比",
        height=450,
        xaxis_title="",
        yaxis_title="元/月",
        margin=dict(l=40, r=40, t=60, b=95),
    )
    return _legend_bottom(fig, bottom=112)


def compare_grouped_bars(df: pd.DataFrame, selected: list[str]) -> go.Figure:
    data = df[df["display_city"].isin(selected)].copy() if selected else df.head(4).copy()
    if data.empty:
        return empty_chart("请选择城市进行对比")
    rows = []
    for label, col in RMB_METRICS.items():
        if col not in data.columns:
            continue
        for _, row in data.iterrows():
            rows.append({"城市": row["display_city"], "指标": label, "金额（元/月）": row[col]})
    plot_df = pd.DataFrame(rows).dropna(subset=["金额（元/月）"])
    if plot_df.empty:
        return empty_chart()
    fig = px.bar(
        plot_df,
        x="指标",
        y="金额（元/月）",
        color="城市",
        barmode="group",
        color_discrete_sequence=COLOR_SEQ,
    )
    fig.update_layout(
        title="城市月薪、成本、房租与结余对比",
        height=460,
        xaxis_title="",
        yaxis_title="元/月",
        margin=dict(l=40, r=40, t=60, b=100),
    )
    return _legend_bottom(fig, bottom=120)


def multi_city_gap_bars(df: pd.DataFrame, selected: list[str]) -> go.Figure:
    data = df[df["display_city"].isin(selected)].copy()
    if len(data) < 2:
        return empty_chart("请选择至少两个城市进行差异化对比")

    metrics = {
        "税后月薪差额": "avg_salary",
        "生活成本差额": "monthly_cost_single_rmb",
        "房租差额": "rent_1br_city_centre_rmb",
        "实际月结余差额": "monthly_balance_after_rent_cost_rmb",
    }
    rows = []
    for label, col in metrics.items():
        if col not in data.columns:
            continue
        mean_value = data[col].mean()
        for _, row in data.iterrows():
            diff = row[col] - mean_value
            rows.append(
                {
                    "城市": row["display_city"],
                    "指标": label,
                    "较所选城市平均值差额（元/月）": diff,
                    "方向": "高于均值" if diff >= 0 else "低于均值",
                }
            )
    plot_df = pd.DataFrame(rows).dropna()
    if plot_df.empty:
        return empty_chart()
    fig = px.bar(
        plot_df,
        x="较所选城市平均值差额（元/月）",
        y="城市",
        color="方向",
        facet_col="指标",
        facet_col_wrap=2,
        orientation="h",
        color_discrete_map={"高于均值": "#0F4C81", "低于均值": "#9CC7E6"},
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="#64748B")
    fig.update_layout(
        title="相对所选城市平均值的差异",
        height=620,
        xaxis_title="元/月",
        yaxis_title="",
        margin=dict(l=85, r=40, t=70, b=50),
    )
    return _legend_bottom(fig, bottom=108)


def multi_city_decision_heatmap(df: pd.DataFrame, selected: list[str]) -> go.Figure:
    data = df[df["display_city"].isin(selected)].copy()
    metrics = {
        "月薪": "avg_salary",
        "生活成本": "monthly_cost_single_rmb",
        "房租": "rent_1br_city_centre_rmb",
        "实际结余": "monthly_balance_after_rent_cost_rmb",
    }
    available = [(label, col) for label, col in metrics.items() if col in data.columns]
    if len(data) < 2 or not available:
        return empty_chart("请选择至少两个城市")

    z_values = []
    text_values = []
    for _, row in data.iterrows():
        z_row = []
        text_row = []
        for _, col in available:
            series = pd.to_numeric(data[col], errors="coerce")
            value = row[col]
            min_v, max_v = series.min(), series.max()
            if pd.isna(value) or pd.isna(min_v) or pd.isna(max_v) or min_v == max_v:
                z_row.append(0.5)
                text_row.append("暂无")
            else:
                z_row.append((value - min_v) / (max_v - min_v))
                text_row.append(f"{value:,.0f}")
        z_values.append(z_row)
        text_values.append(text_row)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=[label for label, _ in available],
            y=data["display_city"],
            text=text_values,
            texttemplate="%{text}",
            colorscale="Blues",
            showscale=False,
            hovertemplate="城市：%{y}<br>指标：%{x}<br>金额：%{text} 元/月<extra></extra>",
        )
    )
    fig.update_layout(
        title="多城市决策矩阵：文本为元/月，颜色表示所选城市内相对高低",
        height=380,
        margin=dict(l=80, r=40, t=70, b=40),
    )
    return fig


def grouped_metric_bar(summary: pd.DataFrame, metric: str, title: str, unit: str = "") -> go.Figure:
    if summary.empty or metric not in summary.columns:
        return empty_chart()
    data = summary.sort_values(metric, ascending=True)
    fig = px.bar(
        data,
        x=metric,
        y="分组",
        orientation="h",
        text=metric,
        color=metric,
        color_continuous_scale="Blues",
    )
    fig.update_traces(texttemplate=_text_template(unit), textposition="outside", cliponaxis=False)
    fig.update_layout(
        title=title,
        height=360,
        xaxis_title=unit,
        yaxis_title="",
        coloraxis_showscale=False,
        margin=dict(l=80, r=50, t=60, b=40),
    )
    return fig


def score_table(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "display_city",
        "region",
        "city_tier",
        "avg_salary",
        "monthly_cost_single_rmb",
        "rent_1br_city_centre_rmb",
        "monthly_balance_after_cost_rmb",
        "monthly_balance_after_rent_cost_rmb",
        "city_type",
    ]
    existing = [col for col in cols if col in df.columns]
    data = df[existing].copy()
    sort_col = "monthly_balance_after_rent_cost_rmb"
    if sort_col in data.columns:
        data = data.sort_values(sort_col, ascending=False)
    data.insert(0, "排名", range(1, len(data) + 1))
    return data.rename(
        columns={
            "display_city": "城市",
            "region": "区域",
            "city_tier": "城市等级",
            "avg_salary": "税后月薪（元/月）",
            "monthly_cost_single_rmb": "单人月生活成本（元/月）",
            "rent_1br_city_centre_rmb": "市中心一居室租金（元/月）",
            "monthly_balance_after_cost_rmb": "扣除生活成本后月结余（元/月）",
            "monthly_balance_after_rent_cost_rmb": "扣除生活成本和房租后月结余（元/月）",
            "city_type": "城市类型",
        }
    )


def industry_share_chart(job_df: pd.DataFrame, selected: list[str] | None = None) -> go.Figure:
    if job_df.empty or "industry" not in job_df.columns:
        return empty_chart("缺少行业结构数据")
    data = job_df.copy()
    if selected:
        data = data[data["city_name_zh"].isin(selected)]
    if data.empty:
        return empty_chart("当前城市没有行业结构数据")
    plot_df = (
        data.groupby(["city_name_zh", "industry"], as_index=False)["job_share_percent"]
        .sum()
        .sort_values(["city_name_zh", "job_share_percent"], ascending=[True, False])
    )
    fig = px.bar(
        plot_df,
        x="city_name_zh",
        y="job_share_percent",
        color="industry",
        text="job_share_percent",
        color_discrete_sequence=COLOR_SEQ,
        labels={"city_name_zh": "城市", "job_share_percent": "岗位占比（%）", "industry": "行业"},
    )
    fig.update_traces(texttemplate="%{text:.0f}%", textposition="inside")
    fig.update_layout(
        title="城市行业岗位占比结构",
        height=460,
        barmode="stack",
        xaxis_title="城市",
        yaxis_title="岗位占比（%）",
        margin=dict(l=40, r=40, t=60, b=80),
    )
    return fig


def position_salary_chart(job_df: pd.DataFrame, selected: list[str] | None = None, top_n: int = 12) -> go.Figure:
    if job_df.empty or "position_type" not in job_df.columns:
        return empty_chart("缺少岗位/工种数据")
    data = job_df.copy()
    if selected:
        data = data[data["city_name_zh"].isin(selected)]
    data = data.dropna(subset=["position_avg_salary_rmb"]).sort_values("position_avg_salary_rmb", ascending=True)
    if data.empty:
        return empty_chart("当前城市没有岗位薪资数据")
    data["岗位"] = data["city_name_zh"] + " · " + data["position_type"]
    plot_df = data.tail(top_n)
    fig = px.bar(
        plot_df,
        x="position_avg_salary_rmb",
        y="岗位",
        color="industry",
        text="position_avg_salary_rmb",
        orientation="h",
        color_discrete_sequence=COLOR_SEQ,
        labels={"position_avg_salary_rmb": "岗位平均薪资（元/月）", "industry": "行业"},
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside", cliponaxis=False)
    fig.update_layout(
        title="热门岗位/工种薪资对比",
        height=520,
        xaxis_title="元/月",
        yaxis_title="",
        margin=dict(l=155, r=50, t=60, b=40),
    )
    return fig


def education_structure_chart(job_df: pd.DataFrame, selected: list[str] | None = None) -> go.Figure:
    if job_df.empty or "education_requirement" not in job_df.columns:
        return empty_chart("缺少学历要求数据")
    data = job_df.copy()
    if selected:
        data = data[data["city_name_zh"].isin(selected)]
    if data.empty:
        return empty_chart("当前城市没有学历要求数据")
    plot_df = (
        data.groupby("education_requirement", as_index=False)["job_share_percent"]
        .sum()
        .sort_values("job_share_percent", ascending=False)
    )
    fig = px.bar(
        plot_df,
        x="education_requirement",
        y="job_share_percent",
        text="job_share_percent",
        color="job_share_percent",
        color_continuous_scale="Blues",
        labels={"education_requirement": "学历要求", "job_share_percent": "岗位占比合计（%）"},
    )
    fig.update_traces(texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
    fig.update_layout(
        title="岗位学历要求结构",
        height=380,
        xaxis_title="",
        yaxis_title="岗位占比合计（%）",
        coloraxis_showscale=False,
        margin=dict(l=40, r=40, t=60, b=80),
    )
    return fig


# Cleaner overrides for job-structure visuals. These definitions intentionally come last.
INDUSTRY_COLORS = {
    "互联网/软件": "#0F4C81",
    "金融/商务服务": "#2F6F9F",
    "先进制造": "#4F8FC0",
    "高端制造": "#4F8FC0",
    "电子信息": "#24476B",
    "电子商务": "#74A9D8",
    "贸易物流": "#5B6F95",
    "文化传媒": "#9CC7E6",
    "科研教育": "#6F9FC8",
    "教育科研": "#6F9FC8",
    "教育培训": "#6F9FC8",
    "金融科技": "#2F6F9F",
    "公共服务": "#86B6D8",
    "服务业": "#B7D4EA",
}


def _clean_layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        template="simple_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Microsoft YaHei, Arial, sans-serif", size=13, color="#334155"),
        title=dict(font=dict(size=18, color="#1F2937"), x=0.01, xanchor="left"),
        margin=dict(l=54, r=36, t=64, b=48),
        legend=dict(
            title="",
            orientation="h",
            yanchor="top",
            y=-0.16,
            xanchor="center",
            x=0.5,
            font=dict(size=12),
        ),
    )
    fig.update_layout(margin=dict(b=104))
    fig.update_xaxes(showgrid=True, gridcolor="#E5E7EB", zeroline=False, ticks="")
    fig.update_yaxes(showgrid=False, ticks="")
    return fig


def _industry_color(industry: str) -> str:
    return INDUSTRY_COLORS.get(industry, "#5B6F95")


def industry_share_chart(job_df: pd.DataFrame, selected: list[str] | None = None) -> go.Figure:
    if job_df.empty or "industry" not in job_df.columns:
        return empty_chart("缺少行业结构数据")
    data = job_df.copy()
    if selected:
        data = data[data["city_name_zh"].isin(selected)]
    if data.empty:
        return empty_chart("当前城市没有行业结构数据")

    cities = sorted(data["city_name_zh"].dropna().unique())
    plot_df = (
        data.groupby(["city_name_zh", "industry"], as_index=False)["job_share_percent"]
        .sum()
        .sort_values("job_share_percent", ascending=True)
    )

    if len(cities) == 1:
        city = cities[0]
        city_df = plot_df[plot_df["city_name_zh"] == city].copy()
        fig = go.Figure(
            go.Bar(
                x=city_df["job_share_percent"],
                y=city_df["industry"],
                orientation="h",
                marker=dict(color=[_industry_color(v) for v in city_df["industry"]], line=dict(width=0)),
                text=[f"{v:.0f}%" for v in city_df["job_share_percent"]],
                textposition="outside",
                hovertemplate="%{y}<br>岗位占比：%{x:.0f}%<extra></extra>",
            )
        )
        fig.update_layout(showlegend=False, title=f"{city} 行业岗位结构")
        fig.update_xaxes(range=[0, max(36, city_df["job_share_percent"].max() + 8)], title="岗位占比（%）")
        fig.update_yaxes(title="")
        return _clean_layout(fig, 360)

    plot_df = plot_df.sort_values(["city_name_zh", "job_share_percent"], ascending=[True, False])
    fig = px.bar(
        plot_df,
        x="job_share_percent",
        y="city_name_zh",
        color="industry",
        orientation="h",
        color_discrete_map=INDUSTRY_COLORS,
        labels={"city_name_zh": "城市", "job_share_percent": "岗位占比（%）", "industry": "行业"},
        hover_data={"job_share_percent": ":.0f"},
    )
    if len(cities) <= 4:
        fig.update_traces(texttemplate="%{x:.0f}%", textposition="inside")
    fig.update_layout(barmode="stack", title="多城市行业岗位结构对比")
    fig.update_xaxes(title="岗位占比（%）", range=[0, 100])
    fig.update_yaxes(title="")
    return _clean_layout(fig, max(360, 72 * len(cities) + 150))


def position_salary_chart(job_df: pd.DataFrame, selected: list[str] | None = None, top_n: int = 12) -> go.Figure:
    if job_df.empty or "position_type" not in job_df.columns:
        return empty_chart("缺少岗位/工种数据")
    data = job_df.copy()
    if selected:
        data = data[data["city_name_zh"].isin(selected)]
    data = data.dropna(subset=["position_avg_salary_rmb"]).copy()
    if data.empty:
        return empty_chart("当前城市没有岗位薪资数据")

    cities = sorted(data["city_name_zh"].dropna().unique())
    data["展示岗位"] = data["position_type"] if len(cities) == 1 else data["city_name_zh"] + " · " + data["position_type"]
    plot_df = data.sort_values("position_avg_salary_rmb", ascending=True).tail(top_n)
    fig = go.Figure()
    for industry, group in plot_df.groupby("industry", sort=False):
        fig.add_trace(
            go.Bar(
                x=group["position_avg_salary_rmb"],
                y=group["展示岗位"],
                orientation="h",
                name=industry,
                marker=dict(color=_industry_color(industry), line=dict(width=0)),
                text=[f"{v:,.0f}" for v in group["position_avg_salary_rmb"]],
                textposition="outside",
                hovertemplate="%{y}<br>行业：" + industry + "<br>薪资：%{x:,.0f} 元/月<extra></extra>",
            )
        )
    fig.update_layout(title="岗位/工种薪资对比")
    fig.update_xaxes(title="元/月", range=[0, plot_df["position_avg_salary_rmb"].max() * 1.18])
    fig.update_yaxes(title="")
    return _clean_layout(fig, max(420, 34 * len(plot_df) + 150))


def education_structure_chart(job_df: pd.DataFrame, selected: list[str] | None = None) -> go.Figure:
    if job_df.empty or "education_requirement" not in job_df.columns:
        return empty_chart("缺少学历要求数据")
    data = job_df.copy()
    if selected:
        data = data[data["city_name_zh"].isin(selected)]
    if data.empty:
        return empty_chart("当前城市没有学历要求数据")

    cities = sorted(data["city_name_zh"].dropna().unique())
    plot_df = (
        data.groupby(["city_name_zh", "education_requirement"], as_index=False)["job_share_percent"]
        .sum()
    )

    if len(cities) == 1:
        city = cities[0]
        city_df = plot_df[plot_df["city_name_zh"] == city].sort_values("job_share_percent", ascending=False)
        fig = go.Figure(
            go.Pie(
                labels=city_df["education_requirement"],
                values=city_df["job_share_percent"],
                hole=0.58,
                sort=False,
                marker=dict(colors=["#0F4C81", "#2F6F9F", "#74A9D8", "#B7D4EA"], line=dict(color="#FFFFFF", width=2)),
                textinfo="label+percent",
                textposition="outside",
                hovertemplate="%{label}<br>岗位占比：%{value:.0f}%<extra></extra>",
            )
        )
        fig.update_layout(title=f"{city} 学历要求结构", showlegend=False)
        return _clean_layout(fig, 360)

    fig = px.bar(
        plot_df,
        x="job_share_percent",
        y="city_name_zh",
        color="education_requirement",
        orientation="h",
        color_discrete_sequence=["#0F4C81", "#2F6F9F", "#74A9D8", "#B7D4EA"],
        labels={"city_name_zh": "城市", "job_share_percent": "岗位占比（%）", "education_requirement": "学历要求"},
    )
    fig.update_layout(barmode="stack", title="多城市学历要求结构")
    fig.update_xaxes(title="岗位占比（%）", range=[0, 100])
    fig.update_yaxes(title="")
    return _clean_layout(fig, max(340, 60 * len(cities) + 130))
