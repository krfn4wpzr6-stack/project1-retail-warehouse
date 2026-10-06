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
    / "quality"
    / "01_core_quality_checks.sql"
)

report_path = (
    project_root
    / "reports"
    / "11_data_quality_results.csv"
)

quality_sql = sql_path.read_text(
    encoding="utf-8"
)

with sqlite3.connect(database_path) as connection:
    results = pd.read_sql_query(
        quality_sql,
        connection,
    )

results.to_csv(
    report_path,
    index=False,
    encoding="utf-8-sig",
)

print("数据质量测试结果：")
print(results.to_string(index=False))

failed_tests = results.loc[
    results["test_status"] == "FAIL"
]

print("\n测试总数：")
print(len(results))

print("\n通过数量：")
print((results["test_status"] == "PASS").sum())

print("\n失败数量：")
print(len(failed_tests))

print("\n测试报告已保存到：")
print(report_path)

if not failed_tests.empty:
    print("\n以下测试失败：")
    print(failed_tests.to_string(index=False))

    raise AssertionError(
        f"存在 {len(failed_tests)} 项数据质量测试失败"
    )

print("\n全部数据质量测试通过。")