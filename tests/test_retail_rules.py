import unittest

import pandas as pd

from lessons.retail_rules import (
    build_staging_data,
    classify_record,
    prepare_valid_sales,
)


class RetailRulesTestCase(unittest.TestCase):
    def setUp(self):
        self.raw_data = pd.DataFrame(
            [
                {
                    "InvoiceNo": "1001",
                    "StockCode": "A",
                    "Description": "Cup",
                    "Quantity": 2,
                    "InvoiceDate": "2011-01-01 10:00:00",
                    "UnitPrice": 10.0,
                    "CustomerID": 17850,
                    "Country": "United Kingdom",
                },
                {
                    "InvoiceNo": "1001",
                    "StockCode": "A",
                    "Description": "Cup",
                    "Quantity": 2,
                    "InvoiceDate": "2011-01-01 10:00:00",
                    "UnitPrice": 10.0,
                    "CustomerID": 17850,
                    "Country": "United Kingdom",
                },
                {
                    "InvoiceNo": "C1001",
                    "StockCode": "A",
                    "Description": "Cup",
                    "Quantity": -1,
                    "InvoiceDate": "2011-01-02 10:00:00",
                    "UnitPrice": 10.0,
                    "CustomerID": 17850,
                    "Country": "United Kingdom",
                },
                {
                    "InvoiceNo": "1002",
                    "StockCode": "B",
                    "Description": None,
                    "Quantity": -2,
                    "InvoiceDate": "2011-01-03 10:00:00",
                    "UnitPrice": 5.0,
                    "CustomerID": 17851,
                    "Country": "United Kingdom",
                },
                {
                    "InvoiceNo": "1003",
                    "StockCode": "C",
                    "Description": "Sample",
                    "Quantity": 1,
                    "InvoiceDate": "2011-01-04 10:00:00",
                    "UnitPrice": 0.0,
                    "CustomerID": 17852,
                    "Country": "United Kingdom",
                },
                {
                    "InvoiceNo": "1004",
                    "StockCode": "D",
                    "Description": "Notebook",
                    "Quantity": 3,
                    "InvoiceDate": "2011-01-05 10:00:00",
                    "UnitPrice": 5.0,
                    "CustomerID": None,
                    "Country": "United Kingdom",
                },
            ]
        )

    def test_record_classification_priority(self):
        expected = [
            "regular_purchase",
            "regular_purchase",
            "customer_cancellation",
            "inventory_adjustment_candidate",
            "nonpositive_price_candidate",
            "unknown_customer_purchase",
        ]

        actual = self.raw_data.apply(classify_record, axis=1).tolist()

        self.assertEqual(actual, expected)

    def test_staging_keeps_rows_and_adds_independent_flags(self):
        staging = build_staging_data(self.raw_data)

        self.assertEqual(len(staging), len(self.raw_data))
        self.assertEqual(
            staging["source_row_number"].tolist(),
            [2, 3, 4, 5, 6, 7],
        )
        self.assertTrue(staging["source_row_number"].is_unique)
        self.assertEqual(staging["is_exact_duplicate_extra"].sum(), 1)
        self.assertEqual(staging["is_negative_quantity"].sum(), 2)
        self.assertEqual(staging["is_missing_description"].sum(), 1)
        self.assertEqual(staging["is_missing_customer"].sum(), 1)
        self.assertEqual(str(staging["CustomerID"].dtype), "Int64")
        self.assertEqual(staging.loc[0, "line_amount"], 20.0)
        self.assertEqual(
            staging["record_type"].tolist(),
            [
                "regular_purchase",
                "regular_purchase",
                "customer_cancellation",
                "inventory_adjustment_candidate",
                "nonpositive_price_candidate",
                "unknown_customer_purchase",
            ],
        )

    def test_valid_sales_and_duplicate_amounts_reconcile(self):
        staging = build_staging_data(self.raw_data)
        valid_sales = prepare_valid_sales(staging)

        self.assertEqual(len(valid_sales), 3)
        self.assertEqual(valid_sales["line_amount"].sum(), 55.0)
        self.assertEqual(
            valid_sales["duplicate_candidate_amount"].sum(),
            20.0,
        )
        self.assertEqual(
            valid_sales["adjusted_line_amount"].sum(),
            35.0,
        )
        self.assertAlmostEqual(
            valid_sales["line_amount"].sum()
            - valid_sales["duplicate_candidate_amount"].sum(),
            valid_sales["adjusted_line_amount"].sum(),
        )


if __name__ == "__main__":
    unittest.main()
