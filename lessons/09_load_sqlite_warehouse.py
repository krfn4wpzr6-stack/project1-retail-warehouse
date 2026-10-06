from pathlib import Path
import sqlite3

import pandas as pd


project_root = Path(__file__).resolve().parents[1]

staging_path = (
    project_root
    / "data"
    / "staging"
    / "online_retail_staging.csv"
)

orders_path = (
    project_root
    / "data"
    / "mart"
    / "fact_orders.csv"
)

customers_path = (
    project_root
    / "data"
    / "mart"
    / "mart_customer_rfm.csv"
)

warehouse_dir = project_root / "warehouse"
database_path = warehouse_dir / "retail_warehouse.db"

warehouse_dir.mkdir(parents=True, exist_ok=True)

print("正在读取 CSV 数据……")

staging = pd.read_csv(
    staging_path,
    parse_dates=["InvoiceDate"],
    low_memory=False,
)

orders = pd.read_csv(
    orders_path,
    parse_dates=[
        "order_start_time",
        "order_end_time",
    ],
)

customers = pd.read_csv(
    customers_path,
    parse_dates=[
        "first_order_time",
        "last_order_time",
        "analysis_reference_time",
    ],
)

# 恢复客户编号的整数含义。
staging["CustomerID"] = pd.to_numeric(
    staging["CustomerID"],
    errors="coerce",
).astype("Int64")

orders["customer_id"] = pd.to_numeric(
    orders["customer_id"],
    errors="coerce",
).astype("Int64")

customers["customer_id"] = pd.to_numeric(
    customers["customer_id"],
    errors="raise",
).astype("Int64")

print("正在连接 SQLite 数据库……")

with sqlite3.connect(database_path) as connection:
    print("正在写入暂存明细表……")

    staging.to_sql(
        "stg_retail_lines",
        connection,
        if_exists="replace",
        index=False,
        chunksize=5000,
    )

    print("正在写入订单事实表……")

    orders.to_sql(
        "fact_orders",
        connection,
        if_exists="replace",
        index=False,
        chunksize=5000,
    )

    print("正在写入客户 RFM 表……")

    customers.to_sql(
        "mart_customer_rfm",
        connection,
        if_exists="replace",
        index=False,
        chunksize=5000,
    )

    print("正在创建数据库索引……")

    connection.executescript(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
            ux_stg_retail_lines_source_row
        ON stg_retail_lines(source_row_number);

        CREATE INDEX IF NOT EXISTS
            ix_stg_retail_lines_invoice
        ON stg_retail_lines(InvoiceNo);

        CREATE INDEX IF NOT EXISTS
            ix_stg_retail_lines_customer
        ON stg_retail_lines(CustomerID);

        CREATE UNIQUE INDEX IF NOT EXISTS
            ux_fact_orders_invoice
        ON fact_orders(invoice_no);

        CREATE INDEX IF NOT EXISTS
            ix_fact_orders_customer
        ON fact_orders(customer_id);

        CREATE INDEX IF NOT EXISTS
            ix_fact_orders_time
        ON fact_orders(order_start_time);

        CREATE UNIQUE INDEX IF NOT EXISTS
            ux_customer_rfm_customer
        ON mart_customer_rfm(customer_id);

        CREATE INDEX IF NOT EXISTS
            ix_customer_rfm_segment
        ON mart_customer_rfm(customer_segment);
        """
    )

    connection.commit()

    table_counts = pd.read_sql_query(
        """
        SELECT
            'stg_retail_lines' AS table_name,
            COUNT(*) AS row_count
        FROM stg_retail_lines

        UNION ALL

        SELECT
            'fact_orders' AS table_name,
            COUNT(*) AS row_count
        FROM fact_orders

        UNION ALL

        SELECT
            'mart_customer_rfm' AS table_name,
            COUNT(*) AS row_count
        FROM mart_customer_rfm;
        """,
        connection,
    )

    duplicate_order_keys = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT invoice_no
            FROM fact_orders
            GROUP BY invoice_no
            HAVING COUNT(*) > 1
        );
        """
    ).fetchone()[0]

    orphan_customer_orders = connection.execute(
        """
        SELECT COUNT(*)
        FROM fact_orders AS orders
        LEFT JOIN mart_customer_rfm AS customers
            ON orders.customer_id = customers.customer_id
        WHERE orders.customer_id IS NOT NULL
          AND customers.customer_id IS NULL;
        """
    ).fetchone()[0]

    adjusted_sales = connection.execute(
        """
        SELECT ROUND(
            SUM(adjusted_sales_amount),
            2
        )
        FROM fact_orders;
        """
    ).fetchone()[0]

    segment_summary = pd.read_sql_query(
        """
        SELECT
            customer_segment,
            COUNT(*) AS customer_count,
            ROUND(
                SUM(adjusted_sales_amount),
                2
            ) AS adjusted_sales_amount,
            ROUND(
                AVG(average_order_value),
                2
            ) AS average_order_value
        FROM mart_customer_rfm
        GROUP BY customer_segment
        ORDER BY adjusted_sales_amount DESC;
        """,
        connection,
    )

print("\n数据库表行数：")
print(table_counts.to_string(index=False))

print("\n重复订单主键数量：")
print(duplicate_order_keys)

print("\n找不到客户的已知客户订单数：")
print(orphan_customer_orders)

print("\n调整后总销售额：")
print(adjusted_sales)

print("\n各客户分层汇总：")
print(segment_summary.to_string(index=False))

print("\nSQLite 数据仓库已保存到：")
print(database_path)

# 自动验证数据库结果。
count_map = dict(
    zip(
        table_counts["table_name"],
        table_counts["row_count"],
    )
)

assert count_map["stg_retail_lines"] == 541909
assert count_map["fact_orders"] == 19960
assert count_map["mart_customer_rfm"] == 4338
assert duplicate_order_keys == 0
assert orphan_customer_orders == 0
assert abs(adjusted_sales - 10642110.80) < 0.01