"""
過去レース特徴量の欠損チェック＆補完

calculate_recent_features_supabase で一部の特徴量が生成されない場合の対策
"""

import pandas as pd
import numpy as np


def ensure_past_race_features(df):
    """
    過去レース特徴量が確実に存在するようにする
    
    Args:
        df: DataFrame
    
    Returns:
        過去レース特徴量が補完されたDataFrame
    """
    print("\n📋 過去レース特徴量の確認・補完")
    
    # 必須の過去レース特徴量リスト
    required_features = {
        'past_races_count': 0,
        'recent_avg_rank': 0,
        'recent_best_rank': 0,
        'recent_avg_time_sec': 0,
        'recent_avg_speed': 0,          # ← 欠損しやすい
        'recent_win_rate': 0,
        'recent_top3_rate': 0,
        'days_since_last_race': 0,      # ← 欠損しやすい
        'recent_avg_pos_4c': 0          # ← 欠損しやすい
    }
    
    added_count = 0
    
    for feat, default_value in required_features.items():
        if feat not in df.columns:
            df[feat] = default_value
            added_count += 1
            print(f"   ✓ {feat} を追加（デフォルト値: {default_value}）")
    
    if added_count == 0:
        print("   ✓ すべての過去レース特徴量が存在します")
    else:
        print(f"   ✓ {added_count}個の特徴量を追加しました")
    
    return df


def fix_object_columns(df):
    """
    object型のカラムを数値型に変換
    
    Args:
        df: DataFrame
    
    Returns:
        修正されたDataFrame
    """
    print("\n🔧 データ型の修正")
    
    # sex, age を確実に数値型に
    if 'sex' in df.columns:
        if df['sex'].dtype == 'object':
            df['sex'] = pd.to_numeric(df['sex'], errors='coerce').fillna(0).astype(int)
            print("   ✓ sex を数値型に変換")
    
    if 'age' in df.columns:
        if df['age'].dtype == 'object':
            df['age'] = pd.to_numeric(df['age'], errors='coerce').fillna(0).astype(int)
            print("   ✓ age を数値型に変換")
    
    # その他のobject型カラムをチェック
    object_cols = df.select_dtypes(include=['object']).columns
    
    # 識別情報以外は数値に変換
    exclude_cols = ['race_id', 'race_name', 'horse_name', 'jockey', 'trainer',
                   'sex_age', 'horse_weight', 'time', 'passing', 'weather',
                   'track_condition', 'course_type', 'track_direction']
    
    converted_count = 0
    
    for col in object_cols:
        if col not in exclude_cols:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                converted_count += 1
                print(f"   ✓ {col} を数値型に変換")
            except:
                pass
    
    if converted_count == 0:
        print("   ✓ object型カラムの変換は不要です")
    
    return df


if __name__ == "__main__":
    # テスト
    print("過去レース特徴量チェッカー")
    
    # サンプルデータ
    sample_df = pd.DataFrame({
        'horse_name': ['馬A', '馬B'],
        'age': [4, 5],
        'sex': ['0', '1'],  # object型
        'recent_avg_rank': [2.3, 3.5]
        # past_races_count などが欠損
    })
    
    print("\n元のDataFrame:")
    print(sample_df.dtypes)
    
    # 修正
    sample_df = ensure_past_race_features(sample_df)
    sample_df = fix_object_columns(sample_df)
    
    print("\n修正後:")
    print(sample_df.dtypes)
    print(sample_df.columns.tolist())
