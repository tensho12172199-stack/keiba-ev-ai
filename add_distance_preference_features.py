import pandas as pd

def get_distance_band(dist):
    """距離帯の分類"""
    if dist <= 1400:
        return "short"
    elif dist <= 1800:
        return "mile"
    elif dist <= 2200:
        return "middle"
    else:
        return "long"

def add_distance_preference_features(df):
    """
    距離適性の特徴量を追加
    
    必須カラム:
    - distance: 距離（メートル）
    - speed: スピード（事前にadd_speed_features()で作成される）
    - horse_name: 馬名
    """
    # 必須カラムの存在チェック
    required_cols = ["distance", "speed", "horse_name"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        print(f"      ⚠️  距離適性特徴量: 必須カラムが不足 {missing_cols}")
        return df
    
    # 距離帯の分類
    df["distance_band"] = df["distance"].apply(get_distance_band)

    # ソート
    sort_cols = ["horse_name", "race_date"]
    available_sort = [c for c in sort_cols if c in df.columns]
    if available_sort:
        df = df.sort_values(available_sort)

    # 距離帯ごとの平均スピード
    df["speed_dist_avg"] = (
        df.groupby(["horse_name", "distance_band"])["speed"]
        .transform(lambda x: x.shift().expanding().mean())
    )

    df["speed_dist_diff"] = df["speed"] - df["speed_dist_avg"]

    # 得意距離フラグ
    df["is_favorite_distance"] = (df["speed_dist_diff"] > 0).astype(int)

    return df
