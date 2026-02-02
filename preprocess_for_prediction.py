# preprocess_predict.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

def preprocess_for_prediction(df):
    df = df.copy()

    # --- sex / age ---
    if 'sex' not in df.columns or 'age' not in df.columns:
        df['sex'] = df['sex'].astype(str)
        df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(0)

    # --- 数値変換 ---
    num_cols = ['bracket', 'horse_no', 'weight_carrier', 'age']
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # --- 馬体重（予測時は仮） ---
    df['weight'] = 0
    df['weight_diff'] = 0

    # --- キャリア数（仮） ---
    df['career_count'] = 0

    # --- 過去成績系（すべて仮埋め） ---
    fill_zero_cols = [
        'avg_speed_index', 'avg_last_3f', 'avg_run_style',
        'prev_rank', 'prev_speed_index', 'prev_last_3f',
        'dist_change', 'jockey_win_rate',
        'jockey_course_win_rate', 'bracket_win_rate'
    ]
    for c in fill_zero_cols:
        df[c] = 0

    # --- カテゴリ変数エンコード ---
    cat_cols = ['venue', 'surface', 'rotation', 'sex', 'jockey', 'horse_name']
    for c in cat_cols:
        le = LabelEncoder()
        df[c] = le.fit_transform(df[c].astype(str))

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
