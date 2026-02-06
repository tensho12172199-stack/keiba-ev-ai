"""
予測用データの前処理スクリプト

学習時と同じ特徴量を生成します。
過去レースデータから直近3走の特徴量も追加。
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

# 過去レースデータ管理
try:
    from horse_history_db import HorseHistoryDB, calculate_recent_features
    HISTORY_AVAILABLE = True
except ImportError:
    HISTORY_AVAILABLE = False
    print("⚠️  horse_history_db.py が見つかりません。過去レース機能は無効です。")

# 特徴量メタデータ
try:
    from feature_metadata import FeatureMetadata
    METADATA_AVAILABLE = True
except ImportError:
    METADATA_AVAILABLE = False
    print("⚠️  feature_metadata.py が見つかりません。メタデータ機能は無効です。")


def preprocess_for_prediction(df_race, feature_list_path="feature_list.pkl",
                              use_history=True, history_csv="data/race_history.csv",
                              metadata_path="feature_metadata.json"):
    """
    予測用のデータを前処理
    
    学習時と同じ特徴量を生成し、学習時の特徴量リストに合わせる。
    
    Args:
        df_race: レースデータ（出走表）
        feature_list_path: 学習時の特徴量リストファイル
        use_history: 過去レースデータを使用するか
        history_csv: 過去レースデータのCSVファイル
        metadata_path: 特徴量メタデータのJSONファイル
    
    Returns:
        X: 予測用の特徴量DataFrame
    """
    
    # ========================================
    # 0. 特徴量メタデータの読み込み
    # ========================================
    metadata = None
    if METADATA_AVAILABLE and Path(metadata_path).exists():
        try:
            metadata = FeatureMetadata.load(metadata_path)
            print("   ✓ 特徴量メタデータを読み込みました")
            
            # メタデータから前処理パラメータを取得
            n_recent = metadata.preprocessing_params.get('n_recent', 3)
            print(f"   ✓ 直近{n_recent}走を使用")
        except Exception as e:
            print(f"   ⚠️  メタデータ読み込みエラー: {e}")
            n_recent = 3
    else:
        print("   ℹ️  メタデータなし（デフォルトパラメータを使用）")
        n_recent = 3
    
    # データのコピー
    df = df_race.copy()
    
    # ========================================
    # 1. 過去レースデータの取得と統合
    # ========================================
    if use_history and HISTORY_AVAILABLE:
        print("   📚 過去レースデータを取得中...")
        try:
            history_db = HorseHistoryDB(history_csv=history_csv)
            df = calculate_recent_features(df, history_db, n_races=3)
            print("   ✓ 過去レース特徴量を追加")
        except Exception as e:
            print(f"   ⚠️  過去レースデータの取得に失敗: {e}")
            print("   → 過去レース特徴量なしで続行")
    elif use_history and not HISTORY_AVAILABLE:
        print("   ⚠️  horse_history_db.py が利用できません")
    
    # ========================================
    # 2. 基本的な前処理
    # ========================================
    print("   🔧 基本特徴量を生成中...")
    
    # feature_engineering.pyの処理を適用
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
        df["distance_band"] = 1  # デフォルトはmile（数値）
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
    
    # ========================================
    # 5. データ型の最終検証と修正
    # ========================================
    print(f"   🔍 データ型を検証中...")
    
    # object型のカラムをチェック
    object_cols = X.select_dtypes(include=['object']).columns.tolist()
    if object_cols:
        print(f"   ⚠️  object型カラムを検出: {object_cols}")
        for col in object_cols:
            # 数値変換を試みる
            try:
                X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0)
                print(f"      ✓ {col} を数値化")
            except:
                # Label Encoding
                X[col] = pd.factorize(X[col])[0]
                print(f"      ✓ {col} をLabel Encoding")
    
    # NaN/Infチェック
    if X.isna().any().any():
        print(f"   ⚠️  NaNを検出 - 0で埋めます")
        X = X.fillna(0)
    
    if np.isinf(X.select_dtypes(include=[np.number])).any().any():
        print(f"   ⚠️  無限大を検出 - 0で置換")
        X = X.replace([np.inf, -np.inf], 0)
    
    print(f"   ✅ 最終特徴量数: {len(X.columns)}")
    print(f"   ✅ データ型: {X.dtypes.unique()}")
    
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
