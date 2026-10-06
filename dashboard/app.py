from pathlib import Path
import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "warehouse" / "retail_warehouse.db"
QUALITY_REPORT_PATH = PROJECT_ROOT / "reports" / "11_data_quality_results.csv"
PIPELINE_REPORT_PATH = PROJECT_ROOT / "reports" / "12_pipeline_run_summary.csv"

SEGMENT_LABELS = {
    "champions": "冠军客户",
    "loyal_customers": "忠诚客户",
    "potential_loyalists": "潜力忠诚客户",
    "new_customers": "近期单次客户",
    "at_risk_high_value": "高价值流失风险",
    "hibernating": "沉睡客户",
    "needs_attention": "需要关注",
    "anonymous": "匿名订单",
}

COLOR_SEQUENCE = [
    "#0F766E",
    "#2563EB",
    "#7C3AED",
    "#D97706",
    "#DC2626",
    "#64748B",
    "#0891B2",
    "#475569",
]


st.set_page_config(
    page_title="零售经营分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def load_database_data(database_path, database_modified_ns):
    """从可信的本地 SQLite 文件读取仪表盘数据。"""
    del database_modified_ns

    with sqlite3.connect(database_path) as connection:
        orders = pd.read_sql_query(
            """
            SELECT
                invoice_no,
                order_start_time,
                customer_id,
                country,
                product_count,
                total_quantity,
                observed_sales_amount,
                duplicate_candidate_amount,
                adjusted_sales_amount
            FROM fact_orders;
            """,
            connection,
        )

        customers = pd.read_sql_query(
            """
            SELECT
                customer_id,
                latest_country,
                order_count,
                recency_days,
                adjusted_sales_amount,
                average_order_value,
                customer_segment
            FROM mart_customer_rfm;
            """,
            connection,
        )

    return orders, customers


@st.cache_data(show_spinner=False)
def load_csv_report(report_path, report_modified_ns):
    """读取小型运行报告，并以修改时间作为缓存版本。"""
    del report_modified_ns
    return pd.read_csv(report_path)


def format_money(value):
    return f"£{value:,.2f}"


if not DATABASE_PATH.exists():
    st.error("找不到 SQLite 数据仓库。请先在项目根目录执行完整流水线。")
    st.code("python run_pipeline.py", language="powershell")
    st.stop()


orders, customers = load_database_data(
    str(DATABASE_PATH),
    DATABASE_PATH.stat().st_mtime_ns,
)

orders["order_start_time"] = pd.to_datetime(
    orders["order_start_time"]
)
orders["order_month"] = (
    orders["order_start_time"]
    .dt.to_period("M")
    .astype(str)
)

customers["segment_label"] = (
    customers["customer_segment"]
    .map(SEGMENT_LABELS)
    .fillna(customers["customer_segment"])
)

orders = orders.merge(
    customers[["customer_id", "segment_label"]],
    on="customer_id",
    how="left",
)
orders["segment_label"] = orders["segment_label"].fillna(
    SEGMENT_LABELS["anonymous"]
)


st.title("零售交易数据仓库与客户经营分析")
st.caption(
    "UCI Online Retail · 2010-12-01 至 2011-12-09 · "
    "金额单位：英镑"
)

months = sorted(orders["order_month"].unique().tolist())
countries = sorted(orders["country"].dropna().unique().tolist())
segments = sorted(orders["segment_label"].unique().tolist())

st.sidebar.header("筛选条件")

selected_months = st.sidebar.select_slider(
    "月份范围",
    options=months,
    value=(months[0], months[-1]),
)

selected_country = st.sidebar.selectbox(
    "订单国家",
    options=["全部"] + countries,
)

selected_segment = st.sidebar.selectbox(
    "客户分层",
    options=["全部"] + segments,
)

start_month, end_month = selected_months

base_orders = orders.loc[
    orders["order_month"].between(
        start_month,
        end_month,
    )
].copy()

if selected_country != "全部":
    base_orders = base_orders.loc[
        base_orders["country"] == selected_country
    ]

filtered_orders = base_orders.copy()

if selected_segment != "全部":
    filtered_orders = filtered_orders.loc[
        filtered_orders["segment_label"] == selected_segment
    ]

if filtered_orders.empty:
    st.warning("当前筛选条件没有匹配订单，请调整筛选条件。")
    st.stop()

if end_month == months[-1]:
    st.info(
        "最后一个月只包含截至 2011-12-09 的数据，"
        "不能直接与完整月份比较。"
    )


adjusted_sales = filtered_orders["adjusted_sales_amount"].sum()
observed_sales = filtered_orders["observed_sales_amount"].sum()
duplicate_impact = filtered_orders[
    "duplicate_candidate_amount"
].sum()
order_count = filtered_orders["invoice_no"].nunique()
known_customer_count = filtered_orders["customer_id"].nunique()
average_order_value = adjusted_sales / order_count

kpi_row_one = st.columns(3)
kpi_row_one[0].metric("调整后销售额", format_money(adjusted_sales))
kpi_row_one[1].metric("订单数", f"{order_count:,}")
kpi_row_one[2].metric("已知客户", f"{known_customer_count:,}")

kpi_row_two = st.columns(2)
kpi_row_two[0].metric("平均客单价", format_money(average_order_value))
kpi_row_two[1].metric("重复候选影响", format_money(duplicate_impact))

overview_tab, customer_tab, quality_tab = st.tabs(
    ["经营概览", "客户分层", "数据质量"]
)


with overview_tab:
    monthly = (
        filtered_orders
        .groupby("order_month", as_index=False)
        .agg(
            adjusted_sales_amount=(
                "adjusted_sales_amount",
                "sum",
            ),
            order_count=("invoice_no", "nunique"),
        )
    )

    chart_left, chart_right = st.columns(2)

    with chart_left:
        st.subheader("月度调整后销售额")
        monthly_figure = px.line(
            monthly,
            x="order_month",
            y="adjusted_sales_amount",
            markers=True,
            labels={
                "order_month": "月份",
                "adjusted_sales_amount": "销售额（英镑）",
            },
        )
        monthly_figure.update_traces(
            line_color="#0F766E",
            line_width=3,
        )
        monthly_figure.update_layout(
            hovermode="x unified",
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(
            monthly_figure,
            width="stretch",
            config={"displayModeBar": False},
        )

    with chart_right:
        st.subheader("月度订单数")
        order_figure = px.bar(
            monthly,
            x="order_month",
            y="order_count",
            labels={
                "order_month": "月份",
                "order_count": "订单数",
            },
            color_discrete_sequence=["#2563EB"],
        )
        order_figure.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
        )
        st.plotly_chart(
            order_figure,
            width="stretch",
            config={"displayModeBar": False},
        )

    st.subheader("国家销售额 Top 10")
    country_summary = (
        filtered_orders
        .groupby("country", as_index=False)
        .agg(
            adjusted_sales_amount=(
                "adjusted_sales_amount",
                "sum",
            )
        )
        .nlargest(10, "adjusted_sales_amount")
        .sort_values("adjusted_sales_amount")
    )

    country_figure = px.bar(
        country_summary,
        x="adjusted_sales_amount",
        y="country",
        orientation="h",
        labels={
            "country": "国家",
            "adjusted_sales_amount": "销售额（英镑）",
        },
        color="adjusted_sales_amount",
        color_continuous_scale="Teal",
    )
    country_figure.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(
        country_figure,
        width="stretch",
        config={"displayModeBar": False},
    )

    with st.expander("查看最近 100 张订单"):
        recent_orders = (
            filtered_orders
            .sort_values("order_start_time", ascending=False)
            .head(100)[
                [
                    "invoice_no",
                    "order_start_time",
                    "customer_id",
                    "country",
                    "segment_label",
                    "total_quantity",
                    "adjusted_sales_amount",
                ]
            ]
        )
        st.dataframe(
            recent_orders,
            hide_index=True,
            width="stretch",
        )


with customer_tab:
    st.caption(
        "本页展示客户整个数据窗口内的累计指标；月份筛选只影响顶部订单指标，"
        "不会重新计算历史 RFM。"
    )

    customer_view = customers.copy()

    if selected_country != "全部":
        customer_view = customer_view.loc[
            customer_view["latest_country"] == selected_country
        ]

    if selected_segment not in ("全部", SEGMENT_LABELS["anonymous"]):
        customer_view = customer_view.loc[
            customer_view["segment_label"] == selected_segment
        ]

    if selected_segment == SEGMENT_LABELS["anonymous"]:
        customer_view = customer_view.iloc[0:0]

    if customer_view.empty:
        st.warning("匿名订单没有客户编号，不能进入客户 RFM 分层。")
    else:
        segment_summary = (
            customer_view
            .groupby("segment_label", as_index=False)
            .agg(
                customer_count=("customer_id", "nunique"),
                adjusted_sales_amount=(
                    "adjusted_sales_amount",
                    "sum",
                ),
            )
            .sort_values("adjusted_sales_amount")
        )

        segment_left, segment_right = st.columns(2)

        with segment_left:
            st.subheader("各分层客户数量")
            customer_count_figure = px.bar(
                segment_summary,
                x="customer_count",
                y="segment_label",
                orientation="h",
                labels={
                    "segment_label": "客户分层",
                    "customer_count": "客户数",
                },
                color="segment_label",
                color_discrete_sequence=COLOR_SEQUENCE,
            )
            customer_count_figure.update_layout(
                showlegend=False,
                margin=dict(l=10, r=10, t=20, b=10),
            )
            st.plotly_chart(
                customer_count_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

        with segment_right:
            st.subheader("购买频次与累计消费")
            rfm_figure = px.scatter(
                customer_view,
                x="order_count",
                y="adjusted_sales_amount",
                color="segment_label",
                hover_data=[
                    "customer_id",
                    "recency_days",
                    "average_order_value",
                ],
                log_x=True,
                log_y=True,
                opacity=0.65,
                labels={
                    "order_count": "订单数（对数轴）",
                    "adjusted_sales_amount": "累计消费（英镑，对数轴）",
                    "segment_label": "客户分层",
                },
                color_discrete_sequence=COLOR_SEQUENCE,
            )
            rfm_figure.update_layout(
                margin=dict(l=10, r=10, t=20, b=10),
            )
            st.plotly_chart(
                rfm_figure,
                width="stretch",
                config={"displayModeBar": False},
            )

        st.dataframe(
            segment_summary.sort_values(
                "adjusted_sales_amount",
                ascending=False,
            ),
            hide_index=True,
            width="stretch",
        )


with quality_tab:
    if not QUALITY_REPORT_PATH.exists():
        st.warning("尚未生成数据质量报告，请先执行完整流水线。")
    else:
        quality_results = load_csv_report(
            str(QUALITY_REPORT_PATH),
            QUALITY_REPORT_PATH.stat().st_mtime_ns,
        )

        passed_tests = (
            quality_results["test_status"] == "PASS"
        ).sum()
        failed_tests = (
            quality_results["test_status"] == "FAIL"
        ).sum()

        quality_columns = st.columns(3)
        quality_columns[0].metric("测试总数", len(quality_results))
        quality_columns[1].metric("通过", int(passed_tests))
        quality_columns[2].metric("失败", int(failed_tests))

        if failed_tests == 0:
            st.success("当前 16 项数据质量测试全部通过。")
        else:
            st.error("存在未通过的数据质量测试。")

        st.dataframe(
            quality_results,
            hide_index=True,
            width="stretch",
        )

    if PIPELINE_REPORT_PATH.exists():
        st.subheader("最近一次流水线运行")
        pipeline_results = load_csv_report(
            str(PIPELINE_REPORT_PATH),
            PIPELINE_REPORT_PATH.stat().st_mtime_ns,
        )
        st.dataframe(
            pipeline_results,
            hide_index=True,
            width="stretch",
        )


st.divider()
st.caption(
    f"当前筛选观察销售额：{format_money(observed_sales)}；"
    f"调整后销售额：{format_money(adjusted_sales)}。"
    "调整值是重复候选敏感性结果，不代表已确认的数据错误。"
)
