from pathlib import Path

import pandas as pd


project_root = Path(__file__).resolve().parents[1]

orders_path = (
    project_root
    / "data"
    / "mart"
    / "fact_orders.csv"
)

output_path = (
    project_root
    / "data"
    / "mart"
    / "mart_customer_metrics.csv"
)

print("正在读取订单事实表……")

orders = pd.read_csv(
    orders_path,
    parse_dates=[
        "order_start_time",
        "order_end_time",
    ],
)

# 客户指标只能使用存在客户编号的订单。
known_orders = orders.loc[
    orders["customer_id"].notna()
].copy()

known_orders["customer_id"] = (
    pd.to_numeric(
        known_orders["customer_id"],
        errors="raise",
    )
    .astype("Int64")
)

# 排序之后，groupby 中的 last 才代表最近一次订单。
known_orders = known_orders.sort_values(
    [
        "customer_id",
        "order_start_time",
        "invoice_no",
    ]
)

customers = (
    known_orders
    .groupby("customer_id", as_index=False)
    .agg(
        first_order_time=("order_start_time", "min"),
        last_order_time=("order_start_time", "max"),
        latest_country=("country", "last"),
        country_count=("country", "nunique"),
        order_count=("invoice_no", "nunique"),
        total_quantity=("total_quantity", "sum"),
        observed_sales_amount=(
            "observed_sales_amount",
            "sum",
        ),
        duplicate_candidate_amount=(
            "duplicate_candidate_amount",
            "sum",
        ),
        adjusted_sales_amount=(
            "adjusted_sales_amount",
            "sum",
        ),
    )
)

# 历史数据不能用今天作为参考日期。
# 使用数据集中最后一次交易时间的下一天，保证结果可复现。
analysis_reference_time = (
    orders["order_start_time"].max()
    + pd.Timedelta(days=1)
)

customers["analysis_reference_time"] = (
    analysis_reference_time
)

customers["recency_days"] = (
    analysis_reference_time
    - customers["last_order_time"]
).dt.days

customers["customer_lifetime_days"] = (
    customers["last_order_time"]
    - customers["first_order_time"]
).dt.days

customers["average_order_value"] = (
    customers["adjusted_sales_amount"]
    / customers["order_count"]
)

customers["is_repeat_customer"] = (
    customers["order_count"] > 1
)

customers["is_multi_country"] = (
    customers["country_count"] > 1
)

amount_columns = [
    "observed_sales_amount",
    "duplicate_candidate_amount",
    "adjusted_sales_amount",
    "average_order_value",
]

customers[amount_columns] = (
    customers[amount_columns].round(2)
)

customers = customers[
    [
        "customer_id",
        "first_order_time",
        "last_order_time",
        "analysis_reference_time",
        "recency_days",
        "customer_lifetime_days",
        "latest_country",
        "country_count",
        "is_multi_country",
        "order_count",
        "is_repeat_customer",
        "total_quantity",
        "observed_sales_amount",
        "duplicate_candidate_amount",
        "adjusted_sales_amount",
        "average_order_value",
    ]
]

customers.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig",
)

observed_total = customers[
    "observed_sales_amount"
].sum()

adjusted_total = customers[
    "adjusted_sales_amount"
].sum()

print("\n客户数量：")
print(len(customers))

print("\n已知客户订单数：")
print(len(known_orders))

print("\n只购买过一次的客户数：")
print((customers["order_count"] == 1).sum())

print("\n复购客户数：")
print(customers["is_repeat_customer"].sum())

print("\n涉及多个国家的客户数：")
print(customers["is_multi_country"].sum())

print("\n客户观察销售额：")
print(round(observed_total, 2))

print("\n客户调整后销售额：")
print(round(adjusted_total, 2))

print("\n分析参考时间：")
print(analysis_reference_time)

print("\n前 5 名客户：")
print(customers.head().to_string(index=False))

print("\n客户指标表已保存到：")
print(output_path)

# 自动验证结果。
assert len(customers) == 4338
assert len(known_orders) == 18532
assert customers["customer_id"].is_unique
assert (customers["order_count"] == 1).sum() == 1493
assert customers["is_multi_country"].sum() == 8
assert abs(observed_total - 8911407.90) < 0.01
assert abs(adjusted_total - 8887208.89) < 0.01