# preprocess_predict.py
import pandas as pd
from sklearn.preprocessing import LabelEncoder


def preprocess_for_prediction(df):
    """
    当日レース予測用の前処理
    学習時と「列名・順序」を完全一致させる
    """
    df = df.copy()

    # =========================
    # 基本数値
    # =========================
    num_cols = ["bracket", "horse_no", "weight_carrier", "age", "distance"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        else:
            df[c] = 0

    # =========================
    # 学習時はあるが予測時に無い列（仮埋め）
    # =========================
    fill_zero_cols = [
        "weight", "weight_diff", "career_count",
        "avg_speed_index", "avg_last_3f", "avg_run_style",
        "prev_rank", "prev_speed_index", "prev_last_3f",
        "dist_change", "jockey_win_rate",
        "jockey_course_win_rate", "bracket_win_rate"
    ]

    for c in fill_zero_cols:
        df[c] = 0

    # =========================
    # カテゴリ変数
    # =========================
    cat_cols = ["venue", "surface", "rotation", "sex", "jockey", "horse_name"]
    for c in cat_cols:
        if c not in df.columns:
            df[c] = "unknown"

        le = LabelEncoder()
        df[c] = le.fit_transform(df[c].astype(str))

    # =========================
    # 学習時と完全一致の特徴量
    # =========================
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

    return df[FEATURES]
