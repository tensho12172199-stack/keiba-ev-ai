"""
距離非依存スピード指数計算

距離に関係なく比較できるスピード指数を作成します。
基準タイムからの差分を使った競馬の標準的な指数化方法を採用。
"""

import pandas as pd
import numpy as np


def calculate_standard_time(distance, course_type='芝'):
    """
    距離別の基準タイムを計算（秒）
    
    実際の競馬データから算出した平均的なタイム
    
    Args:
        distance: 距離（メートル）
        course_type: コース種別（'芝' or 'ダート'）
    
    Returns:
        基準タイム（秒）
    """
    # 芝の基準タイム（メートル/秒）
    # 優秀な馬の平均: 約16.5-17.0 m/s
    if course_type == '芝':
        base_speed = 16.8  # m/s
    else:  # ダート
        base_speed = 16.2  # m/s（芝より遅い）
    
    # 基準タイム = 距離 / 基準スピード
    standard_time = distance / base_speed
    
    return standard_time


def calculate_speed_index(time_sec, distance, course_type='芝', 
                         track_condition='良', base_index=80):
    """
    スピード指数を計算
    
    指数 = base_index - (実際のタイム - 基準タイム) × 補正係数
    
    高い指数 = 速い
    低い指数 = 遅い
    
    Args:
        time_sec: 実際のタイム（秒）
        distance: 距離（メートル）
        course_type: コース種別
        track_condition: 馬場状態
        base_index: 基準指数（デフォルト80）
    
    Returns:
        スピード指数
    """
    if pd.isna(time_sec) or pd.isna(distance):
        return None
    
    if time_sec <= 0 or distance <= 0:
        return None
    
    # 基準タイムを取得
    standard_time = calculate_standard_time(distance, course_type)
    
    # タイム差（秒）
    time_diff = time_sec - standard_time
    
    # 馬場状態による補正
    condition_adjustment = {
        '良': 0.0,
        '稍重': 0.5,   # 稍重は約0.5秒遅くなる想定
        '重': 1.0,     # 重は約1.0秒遅くなる想定
        '不良': 1.5    # 不良は約1.5秒遅くなる想定
    }
    
    adjustment = condition_adjustment.get(track_condition, 0.0)
    
    # 補正後のタイム差
    adjusted_time_diff = time_diff - adjustment
    
    # スピード指数の計算
    # 1秒の差 = 指数1ポイントの差
    speed_index = base_index - adjusted_time_diff
    
    return speed_index


def add_speed_index_features(df):
    """
    DataFrameにスピード指数関連の特徴量を追加
    
    Args:
        df: レースデータのDataFrame
    
    Returns:
        スピード指数が追加されたDataFrame
    """
    df = df.copy()
    
    print("      ✓ スピード指数を計算中...")
    
    # コース種別のデフォルト値
    if 'course_type' not in df.columns:
        df['course_type'] = '芝'
    
    # 馬場状態のデフォルト値
    if 'track_condition' not in df.columns:
        df['track_condition'] = '良'
    
    # スピード指数を計算
    if 'time_sec' in df.columns and 'distance' in df.columns:
        df['speed_index'] = df.apply(
            lambda row: calculate_speed_index(
                row.get('time_sec'),
                row.get('distance'),
                row.get('course_type', '芝'),
                row.get('track_condition', '良')
            ),
            axis=1
        )
        
        # 無効値の処理
        df['speed_index'] = df['speed_index'].replace([np.inf, -np.inf], np.nan)
        
        # 統計情報
        valid_count = df['speed_index'].notna().sum()
        if valid_count > 0:
            print(f"         - {valid_count}/{len(df)} 頭のスピード指数を計算")
            print(f"         - 範囲: {df['speed_index'].min():.1f} ～ {df['speed_index'].max():.1f}")
            print(f"         - 平均: {df['speed_index'].mean():.1f}")
        else:
            print(f"         - ⚠️ スピード指数が計算できませんでした")
    
    # スピード指数の距離帯別統計
    if 'speed_index' in df.columns and 'distance' in df.columns:
        # 距離帯を定義
        df['distance_category'] = pd.cut(
            df['distance'],
            bins=[0, 1400, 1800, 2200, 2800, 10000],
            labels=['短距離', 'マイル', '中距離', '中長距離', '長距離']
        )
        
        # 距離帯別の平均スピード指数
        print(f"         - 距離帯別平均スピード指数:")
        for category in ['短距離', 'マイル', '中距離', '中長距離', '長距離']:
            cat_data = df[df['distance_category'] == category]['speed_index']
            if len(cat_data) > 0:
                print(f"            {category}: {cat_data.mean():.1f}")
    
    return df


def calculate_past_speed_index_average(df, horse_key='horse_name', date_key='race_date', n_races=3):
    """
    過去レースの平均スピード指数を計算
    
    Args:
        df: レースデータ
        horse_key: 馬を識別するカラム
        date_key: 日付カラム
        n_races: 参照する過去レース数
    
    Returns:
        過去平均スピード指数が追加されたDataFrame
    """
    df = df.copy()
    
    if 'speed_index' not in df.columns:
        print("      ⚠️ speed_indexカラムがありません")
        return df
    
    print(f"      ✓ 過去{n_races}走の平均スピード指数を計算中...")
    
    # 日付でソート
    df = df.sort_values([horse_key, date_key])
    
    # 過去N走の平均
    df['speed_index_avg_past'] = (
        df.groupby(horse_key)['speed_index']
        .transform(lambda x: x.shift().rolling(n_races, min_periods=1).mean())
    )
    
    # 過去最高スピード指数
    df['speed_index_max_past'] = (
        df.groupby(horse_key)['speed_index']
        .transform(lambda x: x.shift().rolling(n_races, min_periods=1).max())
    )
    
    # 直近との差分
    df['speed_index_diff'] = df['speed_index'] - df['speed_index_avg_past']
    
    valid_count = df['speed_index_avg_past'].notna().sum()
    print(f"         - {valid_count}/{len(df)} 頭の過去平均を計算")
    
    return df


# 互換性のための従来関数
def add_speed_features(df):
    """
    スピード特徴量を追加（互換性維持）
    
    Args:
        df: レースデータ
    
    Returns:
        特徴量が追加されたDataFrame
    """
    df = df.copy()
    
    # 距離非依存のスピード指数を計算
    df = add_speed_index_features(df)
    
    # 過去平均スピード指数を計算
    if 'horse_name' in df.columns and 'race_date' in df.columns:
        df = calculate_past_speed_index_average(df)
    
    # 従来の speed カラム（距離/時間）も一応作成（除外リストに入れる）
    if 'distance' in df.columns and 'time_sec' in df.columns:
        df['speed_raw'] = df['distance'] / df['time_sec']
        df['speed_raw'] = df['speed_raw'].replace([np.inf, -np.inf], np.nan)
    
    return df


if __name__ == "__main__":
    # テスト
    print("スピード指数計算テスト")
    
    # サンプルデータ
    sample_data = {
        'horse_name': ['馬A', '馬A', '馬B'],
        'race_date': pd.to_datetime(['2024-01-01', '2024-02-01', '2024-01-15']),
        'distance': [2000, 1800, 2400],
        'time_sec': [120.5, 107.8, 147.2],
        'course_type': ['芝', '芝', 'ダート'],
        'track_condition': ['良', '稍重', '良']
    }
    
    df = pd.DataFrame(sample_data)
    
    print("\n元データ:")
    print(df)
    
    # スピード指数計算
    df = add_speed_features(df)
    
    print("\n結果:")
    print(df[['horse_name', 'distance', 'time_sec', 'speed_index', 'speed_index_avg_past']])
    
    print("\nスピード指数の説明:")
    print("- 80が基準（平均的な馬）")
    print("- 90以上: 非常に優秀")
    print("- 70-80: 平均的")
    print("- 70以下: 平均以下")
