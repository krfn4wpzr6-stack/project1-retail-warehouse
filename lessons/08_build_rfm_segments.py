from pathlib import Path

import pandas as pd


project_root = Path(__file__).resolve().parents[1]

customer_path = (
    project_root
    / "data"
    / "mart"
    / "mart_customer_metrics.csv"
)

output_path = (
    project_root
    / "data"
    / "mart"
    / "mart_customer_rfm.csv"
)

print("正在读取客户指标表……")

customers = pd.read_csv(
    customer_path,
    parse_dates=[
        "first_order_time",
        "last_order_time",
        "analysis_reference_time",
    ],
)

# 计算真实数据中的四分位点。
recency_quantiles = customers["recency_days"].quantile(
    [0.25, 0.50, 0.75]
)

frequency_quantiles = customers["order_count"].quantile(
    [0.25, 0.50, 0.75]
)

monetary_quantiles = customers[
    "adjusted_sales_amount"
].quantile(
    [0.25, 0.50, 0.75]
)

r25 = recency_quantiles.loc[0.25]
r50 = recency_quantiles.loc[0.50]
r75 = recency_quantiles.loc[0.75]

f25 = frequency_quantiles.loc[0.25]
f50 = frequency_quantiles.loc[0.50]
f75 = frequency_quantiles.loc[0.75]

m25 = monetary_quantiles.loc[0.25]
m50 = monetary_quantiles.loc[0.50]
m75 = monetary_quantiles.loc[0.75]


def score_recency(value):
    """最近购买时间越近，分数越高。"""
    if value <= r25:
        return 4
    if value <= r50:
        return 3
    if value <= r75:
        return 2
    return 1


def score_frequency(value):
    """订单数量越多，分数越高。"""
    if value <= f25:
        return 1
    if value <= f50:
        return 2
    if value <= f75:
        return 3
    return 4


def score_monetary(value):
    """调整后消费金额越高，分数越高。"""
    if value <= m25:
        return 1
    if value <= m50:
        return 2
    if value <= m75:
        return 3
    return 4


customers["r_score"] = customers[
    "recency_days"
].apply(score_recency)

customers["f_score"] = customers[
    "order_count"
].apply(score_frequency)

customers["m_score"] = customers[
    "adjusted_sales_amount"
].apply(score_monetary)

customers["rfm_code"] = (
    customers["r_score"].astype(str)
    + customers["f_score"].astype(str)
    + customers["m_score"].astype(str)
)


def assign_segment(row):
    """
    根据 R、F、M 分数生成可解释的客户分层。

    这些标签是分析规则，不是机器学习预测结果。
    """
    r = row["r_score"]
    f = row["f_score"]
    m = row["m_score"]

    if r == 4 and f >= 3 and m >= 3:
        return "champions"

    if r >= 3 and f >= 3:
        return "loyal_customers"

    if r >= 3 and f == 2:
        return "potential_loyalists"

    if r == 4 and f == 1:
        return "new_customers"

    if r <= 2 and (f >= 3 or m >= 3):
        return "at_risk_high_value"

    if r == 1 and f <= 2:
        return "hibernating"

    return "needs_attention"


customers["customer_segment"] = customers.apply(
    assign_segment,
    axis=1,
)

customers.to_csv(
    output_path,
    index=False,
    encoding="utf-8-sig",
)

segment_counts = customers[
    "customer_segment"
].value_counts()

print("\nR 指标分位点：")
print(recency_quantiles)

print("\nF 指标分位点：")
print(frequency_quantiles)

print("\nM 指标分位点：")
print(monetary_quantiles)

print("\n客户分层数量：")
print(segment_counts)

print("\n前 10 名客户的 RFM 结果：")
print(
    customers[
        [
            "customer_id",
            "recency_days",
            "order_count",
            "adjusted_sales_amount",
            "r_score",
            "f_score",
            "m_score",
            "rfm_code",
            "customer_segment",
        ]
    ]
    .head(10)
    .to_string(index=False)
)

print("\nRFM 客户表已保存到：")
print(output_path)

# 自动验证。
assert len(customers) == 4338
assert customers["customer_id"].is_unique
assert customers["customer_segment"].notna().all()
assert customers["rfm_code"].str.len().eq(3).all()

for score_column in [
    "r_score",
    "f_score",
    "m_score",
]:
    assert customers[score_column].between(1, 4).all()

assert segment_counts.sum() == 4338