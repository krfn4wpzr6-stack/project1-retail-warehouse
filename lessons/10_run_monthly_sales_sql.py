from pathlib import Path
import sqlite3

import pandas as pd


project_root = Path(__file__).resolve().parents[1]

database_path = (
    project_root
    / "warehouse"
    / "retail_warehouse.db"
)

sql_path = (
    project_root
    / "sql"
    / "analysis"
    / "01_monthly_sales.sql"
)

report_path = (
    project_root
    / "reports"
    / "10_monthly_sales.csv"
)

sql_query = sql_path.read_text(
    encoding="utf-8"
)

with sqlite3.connect(database_path) as connection:
    monthly_sales = pd.read_sql_query(
        sql_query,
        connection,
    )

monthly_sales.to_csv(
    report_path,
    index=False,
    encoding="utf-8-sig",
)

total_orders = monthly_sales[
    "order_count"
].sum()

total_sales = monthly_sales[
    "adjusted_sales_amount"
].sum()

boundary_month_count = monthly_sales[
    "is_boundary_month"
].sum()

print("月度销售结果：")
print(monthly_sales.to_string(index=False))

print("\n月份数量：")
print(len(monthly_sales))

print("\n汇总订单数：")
print(total_orders)

print("\n汇总调整后销售额：")
print(round(total_sales, 2))

print("\n数据边界月份数量：")
print(boundary_month_count)

print("\n月度报告已保存到：")
print(report_path)

# 自动验证 SQL 汇总没有丢失订单或金额。
assert len(monthly_sales) == 13
assert total_orders == 19960
assert abs(total_sales - 10642110.80) < 0.01
assert boundary_month_count == 2