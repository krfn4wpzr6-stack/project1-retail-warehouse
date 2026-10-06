from datetime import datetime
from hashlib import sha256
from pathlib import Path
import csv
import subprocess
import sys
import time


project_root = Path(__file__).resolve().parent
lessons_dir = project_root / "lessons"
reports_dir = project_root / "reports"

raw_data_path = (
    project_root
    / "data"
    / "raw"
    / "Online Retail.xlsx"
)

summary_path = (
    reports_dir
    / "12_pipeline_run_summary.csv"
)

expected_sha256 = (
    "43465A06F2CCF7C8B5BD2892BC7DEFB52F97487934FE93B16AE4C3936424676D"
)

pipeline_steps = [
    (
        "构建暂存层",
        lessons_dir / "05_build_staging_data.py",
    ),
    (
        "构建订单事实表",
        lessons_dir / "06_build_order_fact.py",
    ),
    (
        "构建客户指标表",
        lessons_dir / "07_build_customer_mart.py",
    ),
    (
        "构建 RFM 客户分层",
        lessons_dir / "08_build_rfm_segments.py",
    ),
    (
        "装载 SQLite 数据仓库",
        lessons_dir / "09_load_sqlite_warehouse.py",
    ),
    (
        "生成月度销售报告",
        lessons_dir / "10_run_monthly_sales_sql.py",
    ),
    (
        "执行数据质量测试",
        lessons_dir / "11_run_data_quality_tests.py",
    ),
]


def calculate_sha256(file_path):
    """分块读取文件并计算 SHA-256。"""
    digest = sha256()

    with file_path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest().upper()


def save_run_summary(run_results):
    """保存本次流水线的执行记录。"""
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "step_number",
        "step_name",
        "script_name",
        "started_at",
        "duration_seconds",
        "return_code",
        "status",
    ]

    with summary_path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(run_results)


print("正在执行流水线启动检查……")

if not raw_data_path.exists():
    raise FileNotFoundError(
        f"找不到原始数据文件：{raw_data_path}"
    )

actual_sha256 = calculate_sha256(
    raw_data_path
)

if actual_sha256 != expected_sha256:
    raise ValueError(
        "原始数据文件的 SHA-256 与预期不一致。\n"
        f"预期：{expected_sha256}\n"
        f"实际：{actual_sha256}"
    )

print("原始数据文件校验通过。")
print("SHA-256：", actual_sha256)

run_results = []
pipeline_started = time.perf_counter()

for step_number, (step_name, script_path) in enumerate(
    pipeline_steps,
    start=1,
):
    print("\n" + "=" * 60)
    print(
        f"[{step_number}/{len(pipeline_steps)}] "
        f"{step_name}"
    )
    print("脚本：", script_path.name)
    print("=" * 60)

    step_started_at = datetime.now().isoformat(
        timespec="seconds"
    )

    step_timer = time.perf_counter()

    completed_process = subprocess.run(
        [
            sys.executable,
            str(script_path),
        ],
        cwd=project_root,
    )

    duration_seconds = round(
        time.perf_counter() - step_timer,
        2,
    )

    if completed_process.returncode == 0:
        status = "PASS"
    else:
        status = "FAIL"

    run_results.append(
        {
            "step_number": step_number,
            "step_name": step_name,
            "script_name": script_path.name,
            "started_at": step_started_at,
            "duration_seconds": duration_seconds,
            "return_code": completed_process.returncode,
            "status": status,
        }
    )

    save_run_summary(run_results)

    print(
        f"\n步骤结果：{status}，"
        f"耗时 {duration_seconds} 秒"
    )

    if status == "FAIL":
        print(
            "\n流水线已停止，"
            f"失败步骤：{step_name}"
        )
        print(
            "已完成步骤的记录保存在：",
            summary_path,
        )

        raise SystemExit(
            completed_process.returncode
        )

total_duration = round(
    time.perf_counter() - pipeline_started,
    2,
)

print("\n" + "=" * 60)
print("流水线全部执行成功。")
print("成功步骤：", len(run_results))
print("总耗时：", total_duration, "秒")
print("执行记录：", summary_path)
print("=" * 60)