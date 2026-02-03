import pandas as pd
import numpy as np

def add_speed_features(df):
    """
    スピード関連の特徴量を追加
    
    必須カラム:
    - distance: 距離（メートル）
    - time_sec: タイム（秒）
    - horse_name: 馬名
    """
    # 必須カラムの存在チェック
    required_cols = ["distance", "time_sec", "horse_name"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"      ⚠️  スピード特徴量: 必須カラムが不足 {missing_cols}")
        return df
    
    # 距離(m) / タイム(sec)
    df["speed"] = df["distance"] / df["time_sec"]

    # 無効値対策
    df["speed"] = df["speed"].replace([np.inf, -np.inf], np.nan)

    # 近走平均との差
    sort_cols = ["horse_name", "race_date"]
    
    # カラム存在チェック
    if not all(c in df.columns for c in sort_cols):
        # race_dateが無い場合は race_id などで代用するか、そのまま処理する
        available_sort = [c for c in sort_cols if c in df.columns]
        if available_sort:
            df = df.sort_values(available_sort)
    else:
        df = df.sort_values(sort_cols)

    # グルーピングも horse_name で行う
    df["speed_recent_avg_3"] = (
        df.groupby("horse_name")["speed"]
        .transform(lambda x: x.shift().rolling(3).mean())
    )

    df["speed_recent_diff_3"] = df["speed"] - df["speed_recent_avg_3"]

    return df
