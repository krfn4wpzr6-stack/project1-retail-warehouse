import pandas as pd


def classify_record(row):
    """按约定的优先级给交易明细分类。"""
    invoice = str(row["InvoiceNo"]).upper()

    if invoice.startswith("C"):
        return "customer_cancellation"

    if row["Quantity"] < 0:
        return "inventory_adjustment_candidate"

    if row["UnitPrice"] <= 0:
        return "nonpositive_price_candidate"

    if pd.isna(row["CustomerID"]):
        return "unknown_customer_purchase"

    return "regular_purchase"


def classify_records(data):
    """使用向量化规则批量分类，规则优先级与 classify_record 一致。"""
    record_type = pd.Series(
        "regular_purchase",
        index=data.index,
        dtype="object",
    )

    record_type.loc[data["CustomerID"].isna()] = (
        "unknown_customer_purchase"
    )
    record_type.loc[data["UnitPrice"] <= 0] = (
        "nonpositive_price_candidate"
    )
    record_type.loc[data["Quantity"] < 0] = (
        "inventory_adjustment_candidate"
    )
    record_type.loc[
        data["InvoiceNo"]
        .astype(str)
        .str.upper()
        .str.startswith("C")
    ] = "customer_cancellation"

    return record_type


def build_staging_data(data):
    """保留原始明细，并增加可追溯的质量标记。"""
    result = data.copy()
    original_columns = list(result.columns)

    result.insert(
        0,
        "source_row_number",
        range(2, len(result) + 2),
    )

    invoice_text = result["InvoiceNo"].astype(str).str.upper()

    result["is_customer_cancellation"] = (
        invoice_text.str.startswith("C")
    )
    result["is_negative_quantity"] = result["Quantity"] < 0
    result["is_nonpositive_price"] = result["UnitPrice"] <= 0
    result["is_missing_customer"] = result["CustomerID"].isna()
    result["is_missing_description"] = result["Description"].isna()
    result["is_exact_duplicate_extra"] = result.duplicated(
        subset=original_columns,
        keep="first",
    )

    result["line_amount"] = (
        result["Quantity"] * result["UnitPrice"]
    )
    result["CustomerID"] = result["CustomerID"].astype("Int64")
    result["record_type"] = classify_records(result)

    return result


def prepare_valid_sales(data):
    """筛选有效销售，并计算重复候选的金额影响。"""
    valid_sales = data.loc[
        (~data["is_customer_cancellation"])
        & (data["Quantity"] > 0)
        & (data["UnitPrice"] > 0)
    ].copy()

    valid_sales["duplicate_candidate_amount"] = (
        valid_sales["line_amount"]
        .where(valid_sales["is_exact_duplicate_extra"], 0)
    )
    valid_sales["adjusted_line_amount"] = (
        valid_sales["line_amount"]
        .where(~valid_sales["is_exact_duplicate_extra"], 0)
    )

    return valid_sales
