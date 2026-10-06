WITH date_bounds AS (
    SELECT
        SUBSTR(MIN(order_start_time), 1, 7) AS first_month,
        SUBSTR(MAX(order_start_time), 1, 7) AS last_month
    FROM fact_orders
),

monthly_sales AS (
    SELECT
        SUBSTR(order_start_time, 1, 7) AS order_month,
        MIN(DATE(order_start_time)) AS first_transaction_date,
        MAX(DATE(order_start_time)) AS last_transaction_date,
        COUNT(DISTINCT DATE(order_start_time)) AS trading_day_count,
        COUNT(*) AS order_count,
        SUM(
            CASE
                WHEN customer_id IS NULL THEN 1
                ELSE 0
            END
        ) AS anonymous_order_count,
        COUNT(DISTINCT customer_id) AS active_known_customer_count,
        SUM(total_quantity) AS total_quantity,
        ROUND(SUM(observed_sales_amount), 2) AS observed_sales_amount,
        ROUND(SUM(duplicate_candidate_amount), 2) AS duplicate_candidate_amount,
        ROUND(SUM(adjusted_sales_amount), 2) AS adjusted_sales_amount,
        ROUND(AVG(adjusted_sales_amount), 2) AS average_order_value
    FROM fact_orders
    GROUP BY SUBSTR(order_start_time, 1, 7)
)

SELECT
    monthly_sales.*,
    CASE
        WHEN monthly_sales.order_month IN (
            date_bounds.first_month,
            date_bounds.last_month
        )
        THEN 1
        ELSE 0
    END AS is_boundary_month
FROM monthly_sales
CROSS JOIN date_bounds
ORDER BY monthly_sales.order_month;
