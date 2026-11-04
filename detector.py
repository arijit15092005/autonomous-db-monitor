import pandas as pd
import numpy as np

class AnomalyDetector:
    def __init__(self, z_threshold: float = 3.0):
        self.z_threshold = z_threshold

    def find_anomalies(self, df: pd.DataFrame, target_column: str) -> pd.DataFrame:
        if df.empty or len(df) < 10:
            return pd.DataFrame()

        mean = df[target_column].mean()
        std = df[target_column].std()

        if std == 0 or np.isnan(std):
            return pd.DataFrame()

        df["z_score"] = (df[target_column] - mean) / std
        anomalies = df[df["z_score"].abs() >= self.z_threshold].copy()
        return anomalies