from pathlib import Path

import pandas as pd


project_root = Path(__file__).resolve().parents[1]
staging_path = (
    project_root
    / "data"
    / "staging"
    / "online_retail_staging.csv"
)

mart_dir = project_root / "data" / "mart"
output_path = mart_dir / "fact_orders.csv"

print("正在读取暂存层数据……")

data = pd.read_csv(
    staging_path,
    parse_dates=["InvoiceDate"],
    low_memory=False,
)

# 有效销售口径：
# 1. 不是顾客取消
# 2. 数量大于 0
# 3. 单价大于 0
valid_sales = data.loc[
    (~data["is_customer_cancellation"])
    & (data["Quantity"] > 0)
    & (data["UnitPrice"] > 0)
].copy()

# 计算“疑似重复数据”对金额的影响，但不直接删除原记录。
valid_sales["duplicate_candidate_amount"] = (
    valid_sales["line_amount"]
    .where(valid_sales["is_exact_duplicate_extra"], 0)
)

valid_sales["adjusted_line_amount"] = (
    valid_sales["line_amount"]
    .where(~valid_sales["is_exact_duplicate_extra"], 0)
)

# 按发票号聚合。
# 订单事实表的粒度：一行代表一张发票。
orders = (
    valid_sales
    .groupby("InvoiceNo", as_index=False)
    .agg(
        order_start_time=("InvoiceDate", "min"),
        order_end_time=("InvoiceDate", "max"),
        customer_id=("CustomerID", "first"),
        country=("Country", "first"),
        observed_line_count=("InvoiceNo", "size"),
        product_count=("StockCode", "nunique"),
        total_quantity=("Quantity", "sum"),
        observed_sales_amount=("line_amount", "sum"),
        duplicate_candidate_line_count=(
            "is_exact_duplicate_extra",
            "sum",
        ),
        duplicate_candidate_amount=(
            "duplicate_candidate_amount",
            "sum",
        ),
        adjusted_sales_amount=(
            "adjusted_line_amount",
            "sum",
        ),
    )
)

orders = orders.rename(
    columns={
        "InvoiceNo": "invoice_no",
    }
)

# 一个发票号可能跨越相邻的几分钟。
orders["order_duration_minutes"] = (
    orders["order_end_time"]
    - orders["order_start_time"]
).dt.total_seconds() / 60

orders["has_multiple_timestamps"] = (
    orders["order_start_time"]
    != orders["order_end_time"]
)

# 恢复客户编号的整数含义，同时允许缺失值。
orders["customer_id"] = (
    pd.to_numeric(orders["customer_id"], errors="coerce")
    .astype("Int64")
)

amount_columns = [
    "observed_sales_amount",
    "duplicate_candidate_amount",
    "adjusted_sales_amount",
]

orders[amount_columns] = orders[amount_columns].round(2)

# 调整列的排列顺序。
orders = orders[
    [
        "invoice_no",
        "order_start_time",
        "order_end_time",
        "order_duration_minutes",
        "has_multiple_timestamps",
        "customer_id",
        "country",
        "observed_line_count",
        "duplicate_candidate_line_count",
        "product_count",
        "total_quantity",
        "observed_sales_amount",
        "duplicate_candidate_amount",
        "adjusted_sales_amount",
    ]
]

mart_dir.mkdir(parents=True, exist_ok=True)
orders.to_csv(output_path, index=False, encoding="utf-8-sig")

observed_total = orders["observed_sales_amount"].sum()
adjusted_total = orders["adjusted_sales_amount"].sum()

print("\n有效销售明细数：")
print(len(valid_sales))

print("\n订单数：")
print(len(orders))

print("\n已知客户数：")
print(orders["customer_id"].nunique())

print("\n缺失客户编号的订单数：")
print(orders["customer_id"].isna().sum())

print("\n包含多个交易时间的订单数：")
print(orders["has_multiple_timestamps"].sum())

print("\n原始观察销售额：")
print(round(observed_total, 2))

print("\n排除额外重复候选后的销售额：")
print(round(adjusted_total, 2))

print("\n重复候选造成的金额差异：")
print(round(observed_total - adjusted_total, 2))

print("\n前 5 张订单：")
print(orders.head().to_string(index=False))

print("\n订单事实表已保存到：")
print(output_path)

# 自动验证事实表。
assert len(valid_sales) == 530104
assert len(orders) == 19960
assert orders["invoice_no"].is_unique
assert orders["has_multiple_timestamps"].sum() == 42
assert orders["customer_id"].nunique() == 4338
assert abs(observed_total - 10666684.54) < 0.01
assert abs(adjusted_total - 10642110.80) < 0.01