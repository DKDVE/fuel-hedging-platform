"""Unit normalization helpers for ratio/percent values."""


def normalize_ratio_value(raw_value: float | int | None) -> float:
    """Normalize numeric values that may be encoded as ratio or percent.

    Input examples:
    - 0.2324 -> 0.2324 (already ratio)
    - 23.24  -> 0.2324 (percent converted to ratio)
    """
    if raw_value is None:
        return 0.0
    value = float(raw_value)
    if value <= 1.0:
        return max(0.0, value)
    return max(0.0, value / 100.0)


def normalize_percent_value(raw_value: float | int | None) -> float:
    """Normalize numeric values that may be encoded as ratio or percent.

    Input examples:
    - 0.2324 -> 23.24
    - 23.24  -> 23.24
    """
    return normalize_ratio_value(raw_value) * 100.0
