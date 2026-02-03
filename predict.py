import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
from pathlib import Path
import warnings

# 自作モジュールのインポート
from feature_engineering import apply_all_features
from add_passing_features import add_passing_features
from add_jockey_style_features import add_jockey_style_features
from add_speed_features import add_speed_features
from add_distance_preference_features import add_distance_preference_features
from add_recent_diff_features import add_recent_diff_features

warnings.filterwarnings('ignore')

# =====================
# 設定
# =====================
class PredictConfig:
    """推論の設定"""
    MODEL_FILE = Path("outputs/horse_racing_lgbm_ranker.txt")
    FEATURE_LIST_FILE = Path("outputs/feature_list.pkl")
    OUTPUT_FILE = Path("outputs/predictions.csv")
    
    DATE_KEY = "race_date"
    RACE_ID = "race_id"
    HORSE_KEY = "horse_name"


def load_model_and_features():
    """学習済みモデルと特徴量リストの読み込み"""
    print("🔍 モデルを読み込んでいます...")
    
    if not PredictConfig.MODEL_FILE.exists():
        raise FileNotFoundError(
            f"モデルファイルが見つかりません: {PredictConfig.MODEL_FILE}\n"
            "先に train_lgbm_ranker_improved.py を実行してください。"
        )
    
    if not PredictConfig.FEATURE_LIST_FILE.exists():
        raise FileNotFoundError(
            f"特徴量リストが見つかりません: {PredictConfig.FEATURE_LIST_FILE}"
        )
    
    # モデル読み込み
    model = lgb.Booster(model_file=str(PredictConfig.MODEL_FILE))
    
    # 特徴量リスト読み込み
    features = joblib.load(PredictConfig.FEATURE_LIST_FILE)
    
    print(f"✅ モデル読み込み完了")
    print(f"   特徴量数: {len(features)}")
    
    return model, features


def preprocess_predict_data(df: pd.DataFrame) -> pd.DataFrame:
    """予測用データの前処理（学習時と同じ処理）"""
    print("\n🔧 データを前処理中...")
    
    # 日付型変換
    if PredictConfig.DATE_KEY in df.columns:
        df[PredictConfig.DATE_KEY] = pd.to_datetime(
            df[PredictConfig.DATE_KEY], 
            errors="coerce"
        )
    
    # 基本前処理
    df = apply_all_features(df)
    
    # horse_id がない場合は生成
    if "horse_id" not in df.columns and PredictConfig.HORSE_KEY in df.columns:
        df["horse_id"] = pd.factorize(df[PredictConfig.HORSE_KEY])[0]
    
    # ソート
    if PredictConfig.DATE_KEY in df.columns:
        df = df.sort_values([PredictConfig.DATE_KEY, PredictConfig.RACE_ID])
    
    # 特徴量生成
    if "passing" in df.columns:
        df = add_passing_features(df)
    
    if Path("jockey_profile.csv").exists():
        df = add_jockey_style_features(df, jockey_profile_path="jockey_profile.csv")
    
    df = add_speed_features(df)
    df = add_distance_preference_features(df)
    df = add_recent_diff_features(df, n_recent=3)
    
    print("✅ 前処理完了")
    
    return df


def predict_races(df: pd.DataFrame, model, features: list) -> pd.DataFrame:
    """各レースの予測を実行"""
    print("\n🎯 予測を実行中...")
    
    # 必要な特徴量が揃っているかチェック
    missing_features = [f for f in features if f not in df.columns]
    if missing_features:
        print(f"⚠️  不足している特徴量: {len(missing_features)}個")
        print(f"   例: {missing_features[:5]}")
        # 不足している特徴量は0埋め
        for f in missing_features:
            df[f] = 0
    
    # 予測用データ準備
    X = df[features]
    
    # 予測実行
    predictions = model.predict(X)
    
    # 結果をDataFrameに追加
    df["prediction_score"] = predictions
    
    # レース内でのランキング
    df["predicted_rank"] = (
        df.groupby(PredictConfig.RACE_ID)["prediction_score"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    
    print(f"✅ 予測完了: {len(df)} 頭")
    
    return df


def format_predictions(df: pd.DataFrame) -> pd.DataFrame:
    """予測結果を見やすく整形"""
    
    # 必要なカラムのみ抽出
    output_cols = [
        PredictConfig.RACE_ID,
        PredictConfig.HORSE_KEY,
        "predicted_rank",
        "prediction_score",
    ]
    
    # オプショナルなカラム
    optional_cols = [
        PredictConfig.DATE_KEY,
        "jockey",
        "odds",
        "popularity",
        "horse_weight_base",
    ]
    
    for col in optional_cols:
        if col in df.columns:
            output_cols.append(col)
    
    result_df = df[output_cols].copy()
    
    # レースごとにソート
    result_df = result_df.sort_values(
        [PredictConfig.RACE_ID, "predicted_rank"]
    )
    
    return result_df


def display_predictions(df: pd.DataFrame, top_n: int = 3) -> None:
    """予測結果をコンソールに表示"""
    print("\n" + "="*80)
    print("📊 予測結果（各レースのTOP3）")
    print("="*80)
    
    race_ids = df[PredictConfig.RACE_ID].unique()[:5]  # 最初の5レースのみ表示
    
    for race_id in race_ids:
        race_df = df[df[PredictConfig.RACE_ID] == race_id].head(top_n)
        
        print(f"\n🏇 レースID: {race_id}")
        print("-" * 80)
        
        for idx, row in race_df.iterrows():
            rank = int(row["predicted_rank"])
            horse = row[PredictConfig.HORSE_KEY]
            score = row["prediction_score"]
            
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
            
            line = f"{medal} {rank}位: {horse:20s} (スコア: {score:>8.3f}"
            
            if "jockey" in row:
                line += f", 騎手: {row['jockey']}"
            if "odds" in row and pd.notna(row["odds"]):
                line += f", オッズ: {row['odds']:.1f}"
            
            line += ")"
            print(f"   {line}")
    
    if len(race_ids) < df[PredictConfig.RACE_ID].nunique():
        remaining = df[PredictConfig.RACE_ID].nunique() - len(race_ids)
        print(f"\n... 他 {remaining} レース")


def save_predictions(df: pd.DataFrame) -> None:
    """予測結果をCSVに保存"""
    print(f"\n💾 予測結果を保存中...")
    
    PredictConfig.OUTPUT_FILE.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(PredictConfig.OUTPUT_FILE, index=False, encoding="utf-8-sig")
    
    print(f"✅ 保存完了: {PredictConfig.OUTPUT_FILE}")


# =====================
# メイン処理
# =====================
def main(input_csv: str):
    """
    メイン実行関数
    
    Args:
        input_csv: 予測対象のCSVファイルパス
    """
    print("\n" + "="*80)
    print("🔮 競馬予測スクリプト")
    print("="*80)
    
    try:
        # 1. モデル読み込み
        model, features = load_model_and_features()
        
        # 2. データ読み込み
        print(f"\n📂 データを読み込んでいます: {input_csv}")
        df = pd.read_csv(input_csv)
        print(f"   レース数: {df[PredictConfig.RACE_ID].nunique()}")
        print(f"   出走頭数: {len(df)}")
        
        # 3. 前処理
        df = preprocess_predict_data(df)
        
        # 4. 予測
        df = predict_races(df, model, features)
        
        # 5. 整形
        result_df = format_predictions(df)
        
        # 6. 表示
        display_predictions(result_df)
        
        # 7. 保存
        save_predictions(result_df)
        
        print("\n" + "="*80)
        print("✅ 予測完了！")
        print("="*80)
        
        return result_df
        
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ エラーが発生しました: {e}")
        print("="*80)
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("使用方法: python predict.py <予測対象のCSVファイル>")
        print("例: python predict.py data/race_2024_predict.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not Path(input_file).exists():
        print(f"❌ ファイルが見つかりません: {input_file}")
        sys.exit(1)
    
    main(input_file)
