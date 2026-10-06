WITH quality_results AS (
    SELECT
        '01_staging_row_count' AS test_name,
        CASE
            WHEN (
                SELECT COUNT(*)
                FROM stg_retail_lines
            ) = 541909
            THEN 0
            ELSE 1
        END AS failed_rows

    UNION ALL

    SELECT
        '02_staging_source_row_unique',
        (
            SELECT
                COUNT(*)
                - COUNT(DISTINCT source_row_number)
            FROM stg_retail_lines
        )

    UNION ALL

    SELECT
        '03_staging_line_amount',
        COUNT(*)
    FROM stg_retail_lines
    WHERE line_amount IS NULL
       OR ABS(
            line_amount
            - Quantity * UnitPrice
       ) > 0.001

    UNION ALL

    SELECT
        '04_staging_record_type',
        COUNT(*)
    FROM stg_retail_lines
    WHERE record_type IS NULL
       OR record_type NOT IN (
            'regular_purchase',
            'unknown_customer_purchase',
            'customer_cancellation',
            'inventory_adjustment_candidate',
            'nonpositive_price_candidate'
       )

    UNION ALL

    SELECT
        '05_cancellation_flag',
        COUNT(*)
    FROM stg_retail_lines
    WHERE (
        is_customer_cancellation = 1
        AND UPPER(CAST(InvoiceNo AS TEXT)) NOT LIKE 'C%'
    )
    OR (
        is_customer_cancellation = 0
        AND UPPER(CAST(InvoiceNo AS TEXT)) LIKE 'C%'
    )

    UNION ALL

    SELECT
        '06_fact_order_row_count',
        CASE
            WHEN (
                SELECT COUNT(*)
                FROM fact_orders
            ) = 19960
            THEN 0
            ELSE 1
        END

    UNION ALL

    SELECT
        '07_fact_order_key_unique',
        (
            SELECT
                COUNT(*)
                - COUNT(DISTINCT invoice_no)
            FROM fact_orders
        )

    UNION ALL

    SELECT
        '08_fact_positive_adjusted_sales',
        COUNT(*)
    FROM fact_orders
    WHERE adjusted_sales_amount <= 0
       OR adjusted_sales_amount IS NULL

    UNION ALL

    SELECT
        '09_fact_amount_reconciliation',
        COUNT(*)
    FROM fact_orders
    WHERE ABS(
        observed_sales_amount
        - adjusted_sales_amount
        - duplicate_candidate_amount
    ) > 0.011

    UNION ALL

    SELECT
        '10_customer_row_count',
        CASE
            WHEN (
                SELECT COUNT(*)
                FROM mart_customer_rfm
            ) = 4338
            THEN 0
            ELSE 1
        END

    UNION ALL

    SELECT
        '11_customer_key_unique',
        (
            SELECT
                COUNT(*)
                - COUNT(DISTINCT customer_id)
            FROM mart_customer_rfm
        )

    UNION ALL

    SELECT
        '12_customer_referential_integrity',
        COUNT(*)
    FROM fact_orders AS orders
    LEFT JOIN mart_customer_rfm AS customers
        ON orders.customer_id = customers.customer_id
    WHERE orders.customer_id IS NOT NULL
      AND customers.customer_id IS NULL

    UNION ALL

    SELECT
        '13_rfm_score_range',
        COUNT(*)
    FROM mart_customer_rfm
    WHERE r_score NOT BETWEEN 1 AND 4
       OR f_score NOT BETWEEN 1 AND 4
       OR m_score NOT BETWEEN 1 AND 4
       OR r_score IS NULL
       OR f_score IS NULL
       OR m_score IS NULL

    UNION ALL

    SELECT
        '14_customer_segment_not_null',
        COUNT(*)
    FROM mart_customer_rfm
    WHERE customer_segment IS NULL
       OR TRIM(customer_segment) = ''

    UNION ALL

    SELECT
        '15_customer_amount_reconciliation',
        COUNT(*)
    FROM mart_customer_rfm
    WHERE ABS(
        observed_sales_amount
        - adjusted_sales_amount
        - duplicate_candidate_amount
    ) > 0.011

    UNION ALL

    SELECT
        '16_total_sales_regression',
        CASE
            WHEN ABS(
                (
                    SELECT SUM(adjusted_sales_amount)
                    FROM fact_orders
                ) - 10642110.80
            ) < 0.01
            THEN 0
            ELSE 1
        END
)

SELECT
    test_name,
    failed_rows,
    CASE
        WHEN failed_rows = 0 THEN 'PASS'
        ELSE 'FAIL'
    END AS test_status
FROM quality_results
ORDER BY test_name;