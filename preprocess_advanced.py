import pandas as pd
import numpy as np
import re
from sklearn.preprocessing import LabelEncoder

# -------------------------
# 補助関数
# -------------------------

def convert_time_to_seconds(time_str):
    """ 1:34.5 → 94.5 """
    try:
        if pd.isna(time_str):
            return np.nan
        t = str(time_str)
        if ":" in t:
            m, s = t.split(":")
            return float(m) * 60 + float(s)
        return float(t)
    except:
        return np.nan


def classify_leg_type(passing_str):
    """
    通過順から脚質を簡易分類
    0 = 前（逃げ・先行）
    1 = 後（差し・追込）
    """
    try:
        if pd.isna(passing_str):
            return np.nan
        first = int(str(passing_str).split("-")[0])
        return 0 if first <= 4 else 1
    except:
        return np.nan


# -------------------------
# 学習用前処理（本体）
# -------------------------

def preprocess_advanced(df):
    df = df.copy()

    # ========= 0. 基本整形 =========

    # 着順
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df = df.dropna(subset=["rank"])
    df["target"] = (df["rank"] == 1).astype(int)

    # sex / age（age_sex から生成）
    if "sex" not in df.columns or "age" not in df.columns:
        df["sex"] = df["age_sex"].astype(str).str[0]
        df["age"] = (
            df["age_sex"]
            .astype(str)
            .str[1:]
            .str.extract(r"(\d+)")[0]
            .astype(float)
        )

    # ========= 1. タイム系 =========

    df["seconds"] = df["time"].apply(convert_time_to_seconds)
    df = df.dropna(subset=["seconds"])

    df["last_3f"] = pd.to_numeric(df["last_3f"], errors="coerce")

    # ========= 2. レース条件 =========

    # 競馬場（race_id から）
    df["venue"] = df["race_id"].astype(str).str[4:6]

    # 芝・ダ
    df["surface"] = df["race_details"].str.extract(r"([芝ダ])")

    # 距離
    df["distance"] = pd.to_numeric(
        df["race_details"].str.extract(r"(\d+)")[0],
        errors="coerce"
    )

    # 回り
    df["rotation"] = df["race_details"].str.extract(r"(右|左|直)")
    df["rotation"] = df["rotation"].fillna("不明")

    # コースID
    df["course_id"] = (
        df["venue"] + "_" +
        df["surface"] + "_" +
        df["distance"].astype(str) + "_" +
        df["rotation"]
    )

    # ========= 3. 馬体重 =========

    def split_weight(w):
        """
        480(+4) → weight=480, diff=4
        """
        try:
            m = re.search(r"(\d+)\(([-+]?\d+)\)", str(w))
            if m:
                return float(m.group(1)), float(m.group(2))
            m2 = re.search(r"(\d+)", str(w))
            if m2:
                return float(m2.group(1)), 0.0
        except:
            pass
        return np.nan, 0.0

    df["weight"], df["weight_diff"] = zip(*df["horse_weight"].apply(split_weight))

    # ========= 4. スピード指数 =========

    g = df.groupby("course_id")["seconds"]
    mean_t = g.transform("mean")
    std_t = g.transform("std").replace(0, 1)

    df["speed_index"] = 50 + 10 * (mean_t - df["seconds"]) / std_t
    df["speed_index"] = df["speed_index"].fillna(50)

    # ========= 5. 前走・キャリア =========

    df = df.sort_values(["horse_name", "race_id"])
    g_horse = df.groupby("horse_name")

    df["prev_rank"] = g_horse["rank"].shift(1)
    df["prev_speed_index"] = g_horse["speed_index"].shift(1)
    df["prev_last_3f"] = g_horse["last_3f"].shift(1)
    df["prev_distance"] = g_horse["distance"].shift(1)

    df["dist_change"] = df["distance"] - df["prev_distance"]
    df["dist_change"] = df["dist_change"].fillna(0)

    df["career_count"] = g_horse.cumcount() + 1

    df["avg_speed_index"] = g_horse["speed_index"].transform("mean")
    df["avg_last_3f"] = g_horse["last_3f"].transform("mean")

    # ========= 6. 騎手・枠・脚質 =========

    df["run_type"] = df["passing"].apply(classify_leg_type)
    df["avg_run_style"] = g_horse["run_type"].transform("mean")

    df["jockey_win_rate"] = df.groupby("jockey")["target"].transform("mean")
    df["jockey_course_win_rate"] = (
        df.groupby(["jockey", "course_id"])["target"].transform("mean")
    )
    df["bracket_win_rate"] = (
        df.groupby(["course_id", "bracket"])["target"].transform("mean")
    )

    # ========= 7. エンコード =========

    cat_cols = ["venue", "surface", "rotation", "sex", "jockey", "horse_name"]
    for c in cat_cols:
        le = LabelEncoder()
        df[c] = le.fit_transform(df[c].astype(str))

    # ========= 8. 最終特徴量 =========

    FEATURES = [
        'bracket', 'horse_no', 'age', 'sex', 'weight_carrier',
        'weight', 'weight_diff', 'career_count',
        'venue', 'surface', 'distance', 'rotation',
        'avg_speed_index', 'avg_last_3f', 'avg_run_style',
        'prev_rank', 'prev_speed_index', 'prev_last_3f', 'dist_change',
        'jockey_win_rate',
        'jockey_course_win_rate',
        'bracket_win_rate'
    ]

    X = df[FEATURES].fillna(0)
    y = df["target"]

    return X, y, FEATURES
