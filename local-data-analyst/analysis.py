import json
import importlib
from typing import Any


pd: Any = importlib.import_module("pandas")


def get_profile(df):
    """Return basic information and a small preview of the dataset."""
    return {
        "rows": int(len(df)),
        "columns": [str(column) for column in df.columns],
        "data_types": {
            str(column): str(dtype)
            for column, dtype in df.dtypes.items()
        },
        "missing_values": {
            str(column): int(count)
            for column, count in df.isna().sum().items()
        },
        "preview": json.loads(
            df.head(8).to_json(orient="records", date_format="iso")
        ),
    }


def summarize_column(df, column):
    """Summarize one column, after checking that it exists."""
    if column not in df.columns:
        return f"Column '{column}' is not in the dataset."

    series = df[column]

    if pd.api.types.is_numeric_dtype(series):
        return series.describe().to_string()

    return series.value_counts(dropna=False).head(10).to_string()


def get_missing_values(df):
    """Return missing-value counts for all columns."""
    return df.isna().sum().to_string()


def group_and_aggregate(df, group_column, value_column, aggregation):
    """Group by one column and calculate an allowed aggregation."""
    if group_column not in df.columns:
        return f"Column '{group_column}' is not in the dataset."

    if value_column not in df.columns:
        return f"Column '{value_column}' is not in the dataset."

    allowed_aggregations = {"sum", "mean", "count", "min", "max"}
    if aggregation not in allowed_aggregations:
        return (
            "Unsupported aggregation. Choose sum, mean, count, min, or max."
        )

    try:
        result = (
            df.groupby(group_column, dropna=False)[value_column]
            .agg(aggregation)
            .sort_values(ascending=False)
            .head(30)
        )
        return result.to_string()
    except Exception as error:
        return f"Could not calculate that aggregation: {error}"