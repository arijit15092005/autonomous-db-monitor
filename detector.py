import pandas as pd
import numpy as np


class AnomalyDetector:
    def __init__(self, z_threshold: float = 2.8, window_size: int = 20):
        self.z_threshold = z_threshold
        self.window_size = window_size

    def evaluate_transactions(
        self, df: pd.DataFrame, target_column: str = "response_time_ms"
    ) -> pd.DataFrame:
        """
        Calculates clean rolling baseline statistics (excluding the current row
        to prevent spike dilution) and flags latency anomalies or DB errors.
        """
        if df.empty:
            return df

        result = df.copy().sort_values("id").reset_index(drop=True)

        # Shift by 1 so the current transaction is judged against prior history
        shifted = result[target_column].shift(1)
        result["rolling_mean"] = shifted.rolling(
            window=self.window_size, min_periods=5
        ).mean()
        result["rolling_std"] = shifted.rolling(
            window=self.window_size, min_periods=5
        ).std()

        # Fallback to overall baseline for the first few warm-up rows
        overall_mean = result[target_column].mean()
        overall_std = result[target_column].std()
        if pd.isna(overall_std) or overall_std == 0:
            overall_std = 1.0

        result["rolling_mean"] = result["rolling_mean"].fillna(overall_mean)
        result["rolling_std"] = (
            result["rolling_std"].replace(0, np.nan).fillna(overall_std)
        )

        # Compute Z-score safely
        result["z_score"] = (
            (result[target_column] - result["rolling_mean"]) / result["rolling_std"]
        ).round(3)

        # Flag positive latency spikes OR database HTTP/SQL error codes (>= 400)
        is_latency_spike = result["z_score"] >= self.z_threshold
        is_db_error = result["status_code"] >= 400
        result["is_anomaly"] = (is_latency_spike | is_db_error).astype(int)

        # Assign severity and human-readable reason
        severities = []
        reasons = []
        for _, row in result.iterrows():
            if row["status_code"] >= 500:
                severities.append("CRITICAL")
                reasons.append(f"Database/Server Error (Status {int(row['status_code'])})")
            elif row["z_score"] >= self.z_threshold + 1.5:
                severities.append("CRITICAL")
                reasons.append(
                    f"Severe Latency Spike: {row[target_column]:.2f} ms (Z={row['z_score']:.2f})"
                )
            elif row["z_score"] >= self.z_threshold:
                severities.append("HIGH")
                reasons.append(
                    f"Latency Anomaly: {row[target_column]:.2f} ms vs baseline {row['rolling_mean']:.2f} ms (Z={row['z_score']:.2f})"
                )
            elif row["status_code"] >= 400:
                severities.append("WARNING")
                reasons.append(f"Client/Query Warning (Status {int(row['status_code'])})")
            else:
                severities.append("NORMAL")
                reasons.append("Within normal rolling baseline")

        result["severity"] = severities
        result["reason"] = reasons
        return result