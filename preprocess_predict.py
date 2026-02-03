"""
予測用データの前処理スクリプト

学習時と同じ特徴量を生成します。
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path

# 学習時と同じ特徴量生成関数をインポート
from feature_engineering import apply_all_features
from add_passing_features import add_passing_features
from add_jockey_style_features import add_jockey_style_features
from add_speed_features import add_speed_features
from add_distance_preference_features import add_distance_preference_features
from add_recent_diff_features import add_recent_diff_features


def preprocess_for_prediction(df_race, feature_list_path="feature_list.pkl"):
    """
    予測用のデータを前処理
    
    学習時と同じ特徴量を生成し、学習時の特徴量リストに合わせる。
    
    Args:
        df_race: レースデータ（出走表）
        feature_list_path: 学習時の特徴量リストファイル
    
    Returns:
        X: 予測用の特徴量DataFrame
    """
    
    # データのコピー
    df = df_race.copy()
    
    # ========================================
    # 1. 基本的な前処理
    # ========================================
    print("   🔧 基本特徴量を生成中...")
    
    # feature_engineering.pyの処理を適用
    # ただし、予測時には rank, time などの結果データがないため、
    # 欠損値として処理される
    df = apply_all_features(df)
    
    # ========================================
    # 2. horse_id の生成
    # ========================================
    if "horse_id" not in df.columns and "horse_name" in df.columns:
        df["horse_id"] = pd.factorize(df["horse_name"])[0]
    
    # ========================================
    # 3. 高度な特徴量生成
    # ========================================
    
    # 3-1. 通過順特徴量
    # 注意: 予測時には過去レースの通過順がないため、
    # この特徴量は過去レースデータベースから取得する必要がある
    # ここではダミーとして処理（実装時は過去レースDB参照）
    print("   ✓ 通過順特徴量...")
    if "passing" in df.columns:
        df = add_passing_features(df)
    else:
        # 通過順がない場合はデフォルト値
        df["passing_1c"] = np.nan
        df["passing_4c"] = np.nan
        df["passing_gain"] = np.nan
        df["style_front"] = 0
        df["style_stalker"] = 0
        df["style_closer"] = 0
    
    # 3-2. スピード特徴量
    print("   ✓ スピード特徴量...")
    # 予測時にはtime_secがないため、過去レースの平均値を使用
    if "distance" in df.columns:
        # 暫定: 標準的なスピード値を設定
        if "time_sec" not in df.columns or df["time_sec"].isna().all():
            # 距離から推定タイム（芝の場合）
            df["time_sec"] = df["distance"] / 15.0  # 約15m/s
        
        df = add_speed_features(df)
    else:
        df["speed"] = np.nan
        df["speed_recent_avg_3"] = np.nan
        df["speed_recent_diff_3"] = np.nan
    
    # 3-3. 距離適性特徴量
    print("   ✓ 距離適性特徴量...")
    if "distance" in df.columns and "speed" in df.columns:
        df = add_distance_preference_features(df)
    else:
        df["distance_band"] = "mile"
        df["speed_dist_avg"] = np.nan
        df["speed_dist_diff"] = np.nan
        df["is_favorite_distance"] = 0
    
    # 3-4. 騎手特徴量
    print("   ✓ 騎手特徴量...")
    if "jockey" in df.columns:
        df = add_jockey_style_features(df, "jockey_profile.csv")
    
    # 3-5. 近走差分特徴量
    print("   ✓ 近走差分特徴量...")
    # 注意: 同一レース内のデータしかないため、近走差分は計算できない
    # 本来は過去レースデータを含めて計算する必要がある
    # ここでは欠損値として処理
    df = add_recent_diff_features(df, n_recent=3)
    
    # ========================================
    # 4. 学習時の特徴量リストに合わせる
    # ========================================
    print(f"   📋 学習時の特徴量リストを読み込み: {feature_list_path}")
    
    if not Path(feature_list_path).exists():
        raise FileNotFoundError(
            f"特徴量リストファイルが見つかりません: {feature_list_path}\n"
            f"学習スクリプト（train_lgbm_ranker_improved.py）を実行して、"
            f"feature_list.pkl を生成してください。"
        )
    
    # 学習時の特徴量リストを読み込み
    feature_list = joblib.load(feature_list_path)
    
    print(f"   ✓ 学習時の特徴量数: {len(feature_list)}")
    print(f"   ✓ 現在の特徴量数: {len([c for c in df.columns if c in feature_list])}")
    
    # 不足している特徴量を0で埋める
    missing_features = set(feature_list) - set(df.columns)
    if missing_features:
        print(f"   ⚠️  不足している特徴量: {len(missing_features)}個")
        for feat in missing_features:
            df[feat] = 0
    
    # 学習時の特徴量のみを抽出（順序も保持）
    X = df[feature_list]
    
    print(f"   ✅ 最終特徴量数: {len(X.columns)}")
    
    return X


def load_past_race_data(horse_name, n_races=5):
    """
    過去レースデータを取得（将来の実装用）
    
    Args:
        horse_name: 馬名
        n_races: 取得する過去レース数
    
    Returns:
        過去レースのDataFrame
    """
    # TODO: データベースやファイルから過去レースデータを取得
    # 現在はダミー実装
    return pd.DataFrame()


if __name__ == "__main__":
    # テスト用
    print("予測用前処理スクリプトのテスト")
    
    # サンプルデータ
    sample_data = {
        "horse_no": [1, 2, 3],
        "horse_name": ["テストホース1", "テストホース2", "テストホース3"],
        "jockey": ["武豊", "岩田康誠", "川田将雅"],
        "age_sex": ["4牡", "5牡", "3牝"],
        "weight_carrier": [58, 57, 54],
        "horse_weight": ["480(+2)", "470(-3)", "450(+5)"],
        "distance": [1800, 1800, 1800],
    }
    
    df = pd.DataFrame(sample_data)
    
    try:
        X = preprocess_for_prediction(df)
        print(f"\n✅ 成功！特徴量形状: {X.shape}")
        print(f"特徴量: {X.columns.tolist()[:10]}...")
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
