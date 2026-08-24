import pandas as pd
import pytest

from indusense.features.temporal import add_temporal_features


def test_temporal_features_do_not_use_current_value():
    df = pd.DataFrame(
        {
            "machine": ["MACH-01"] * 4,
            "timestamp": pd.date_range("2025-01-01", periods=4, freq="h"),
            "temperature": [10.0, 20.0, 30.0, 40.0],
            "pressure_bar": [195.0, 196.0, 197.0, 198.0],
        }
    )
    out = add_temporal_features(df, value_cols=("temperature",), lags=(1,), windows=(2,))

    assert out["temperature_lag1"].isna().iloc[0]
    assert out["temperature_roll2_mean"].iloc[2] == 15.0


def test_temporal_features_sort_by_machine_and_time():
    df = pd.DataFrame(
        {
            "machine": ["MACH-01", "MACH-02", "MACH-01", "MACH-02"],
            "timestamp": pd.to_datetime(
                ["2025-01-01 01:00", "2025-01-01 00:00", "2025-01-01 00:00", "2025-01-01 01:00"]
            ),
            "temperature": [11.0, 20.0, 10.0, 21.0],
            "pressure_bar": [196.0, 205.0, 195.0, 206.0],
        }
    )
    out = add_temporal_features(df, value_cols=("temperature",), lags=(1,), windows=(2,))

    m1 = out[out["machine"] == "MACH-01"].reset_index(drop=True)
    assert m1.loc[1, "temperature_lag1"] == 10.0


def test_temporal_features_missing_column_raises():
    df = pd.DataFrame({"machine": ["MACH-01"], "timestamp": pd.to_datetime(["2025-01-01"])})
    with pytest.raises(ValueError):
        add_temporal_features(df, value_cols=("temperature",))
