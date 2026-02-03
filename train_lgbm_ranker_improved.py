import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
from pathlib import Path
import gc
import glob
import warnings
from datetime import datetime
from typing import List, Tuple, Optional

# 自作モジュールのインポート
from feature_engineering import apply_all_features
from add_passing_features import add_passing_features
from add_jockey_style_features import add_jockey_style_features
from add_speed_features import add_speed_features
from add_distance_preference_features import add_distance_preference_features
from add_recent_diff_features import add_recent_diff_features

warnings.filterwarnings('ignore')

# =====================
# 設定クラス
# =====================
class Config:
    """学習の設定を一元管理"""
    
    # パス設定
    DATA_DIR = Path("data")
    OUT_DIR = Path("outputs")
    MODEL_FILE = OUT_DIR / "horse_racing_lgbm_ranker.txt"
    FEATURE_LIST_FILE = OUT_DIR / "feature_list.pkl"
    IMPORTANCE_FILE = OUT_DIR / "feature_importance.csv"
    METRICS_FILE = OUT_DIR / "training_metrics.csv"
    
    # データカラム
    HORSE_KEY = "horse_name"
    DATE_KEY = "race_date"
    TARGET = "rank"
    RACE_ID = "race_id"
    
    # 学習パラメータ
    LGBM_PARAMS = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_eval_at": [1, 3, 5],
        "num_leaves": 31,
        "learning_rate": 0.05,
        "n_estimators": 800,
        "min_child_samples": 20,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "importance_type": "gain",
        "verbose": -1
    }
    
    # データ分割（日付ベース）
    TRAIN_END_DATE = "2024-06-30"  # この日付までを訓練データ
    
    # 除外カラム
    IGNORE_COLS = [
        "race_id", "race_name", "date", DATE_KEY,
        "horse_name", "horse_id", "jockey", "trainer", "owner",
        TARGET,
        # リーク（結果）系
        "time", "time_sec", "time_per_meter", "time_diff_race",
        "passing", "passing_1c", "passing_4c", "passing_gain",
        "age_sex", "horse_weight", "horse_weight_diff",
        # 人気系（重要度を下げるため除外）
        "popularity", "log_popularity", "odds",
        "popularity_recent_avg_3", "popularity_recent_diff_3",
    ]


# =====================
# ユーティリティ関数
# =====================
def setup_directories() -> None:
    """出力ディレクトリの作成"""
    Config.OUT_DIR.mkdir(exist_ok=True, parents=True)
    print(f"📁 出力ディレクトリ: {Config.OUT_DIR}")


def load_csv_files() -> pd.DataFrame:
    """CSVファイルの読み込み"""
    print("\n" + "="*60)
    print("📂 CSVファイルを読み込んでいます...")
    
    csv_files = sorted(Config.DATA_DIR.glob("*.csv"))
    
    if not csv_files:
        # フォールバック: カレントディレクトリも探す
        csv_files = sorted(glob.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(
                f"❌ CSVファイルが見つかりません。\n"
                f"   {Config.DATA_DIR} ディレクトリを確認してください。"
            )
    
    print(f"   見つかったファイル: {len(csv_files)}個")
    for f in csv_files:
        print(f"   - {f.name}")
    
    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            print(f"⚠️  {f.name} の読み込みに失敗: {e}")
    
    if not dfs:
        raise ValueError("有効なCSVファイルがありません")
    
    df = pd.concat(dfs, ignore_index=True)
    print(f"✅ 読み込み完了: {len(df):,} 行")
    
    return df


def preprocess_basic(df: pd.DataFrame) -> pd.DataFrame:
    """基本的な前処理"""
    print("\n" + "="*60)
    print("🔧 基本前処理を実行中...")
    
    initial_rows = len(df)
    
    # 順位の数値化と欠損除去
    df[Config.TARGET] = pd.to_numeric(df[Config.TARGET], errors="coerce")
    df = df.dropna(subset=[Config.TARGET])
    df[Config.TARGET] = df[Config.TARGET].astype(int)
    
    removed_rows = initial_rows - len(df)
    if removed_rows > 0:
        print(f"   無効な順位データを除去: {removed_rows:,} 行")
    
    # 日付型変換
    if Config.DATE_KEY in df.columns:
        df[Config.DATE_KEY] = pd.to_datetime(df[Config.DATE_KEY], errors="coerce")
        date_nulls = df[Config.DATE_KEY].isna().sum()
        if date_nulls > 0:
            print(f"   ⚠️  日付が無効: {date_nulls:,} 行")
    
    # 共通の前処理
    df = apply_all_features(df)
    
    print(f"✅ 基本前処理完了: {len(df):,} 行")
    
    return df


def generate_features(df: pd.DataFrame) -> pd.DataFrame:
    """高度な特徴量生成"""
    print("\n" + "="*60)
    print("🎯 特徴量生成を実行中...")
    
    # horse_id がない場合は生成
    if "horse_id" not in df.columns and Config.HORSE_KEY in df.columns:
        print(f"   horse_id を {Config.HORSE_KEY} から生成")
        df["horse_id"] = pd.factorize(df[Config.HORSE_KEY])[0]
    
    # ソート
    if Config.DATE_KEY in df.columns:
        df = df.sort_values([Config.DATE_KEY, Config.RACE_ID])
    
    # 各特徴量の追加（必須カラムの定義を拡張）
    feature_funcs = [
        ("通過順特徴量", add_passing_features, ["passing"]),
        ("騎手傾向特徴量", lambda x: add_jockey_style_features(x, "jockey_profile.csv"), []),
        ("スピード特徴量", add_speed_features, ["distance", "time_sec"]),
        ("距離適性特徴量", add_distance_preference_features, ["distance", "speed"]),
        ("近走差分特徴量", lambda x: add_recent_diff_features(x, n_recent=3), []),
    ]
    
    for name, func, required_cols in feature_funcs:
        try:
            # 必須カラムのチェック
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"   ⚠️  {name}: 必須カラムが不足 {missing_cols} - スキップ")
                continue
            
            print(f"   ✓ {name} を追加中...")
            df = func(df)
        except Exception as e:
            print(f"   ⚠️  {name} の生成に失敗: {e}")
            import traceback
            print(f"      詳細: {traceback.format_exc()[:200]}")
    
    print(f"✅ 特徴量生成完了")
    
    return df


def prepare_dataset(df: pd.DataFrame) -> Tuple[List[str], pd.DataFrame, pd.DataFrame]:
    """学習用データセットの準備"""
    print("\n" + "="*60)
    print("📊 データセットを構築中...")
    
    # 数値型のみ抽出
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    
    # 特徴量リストの確定
    features = [c for c in numeric_cols if c not in Config.IGNORE_COLS]
    
    print(f"   特徴量数: {len(features)}")
    print(f"   除外カラム数: {len(Config.IGNORE_COLS)}")
    
    # データ分割（日付ベース）
    if Config.DATE_KEY in df.columns:
        train_end = pd.to_datetime(Config.TRAIN_END_DATE)
        train_df = df[df[Config.DATE_KEY] <= train_end].copy()
        valid_df = df[df[Config.DATE_KEY] > train_end].copy()
        
        print(f"   訓練データ: {len(train_df):,} 行 (～{Config.TRAIN_END_DATE})")
        print(f"   検証データ: {len(valid_df):,} 行 ({Config.TRAIN_END_DATE}～)")
    else:
        # 日付がない場合は8:2で分割
        print("   ⚠️  日付カラムがないため、ランダムに8:2分割")
        train_df = df.sample(frac=0.8, random_state=42)
        valid_df = df.drop(train_df.index)
        
        print(f"   訓練データ: {len(train_df):,} 行")
        print(f"   検証データ: {len(valid_df):,} 行")
    
    # レースIDでソート
    train_df = train_df.sort_values(Config.RACE_ID)
    valid_df = valid_df.sort_values(Config.RACE_ID)
    
    return features, train_df, valid_df


def create_ranker_dataset(
    df: pd.DataFrame,
    features: List[str]
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """LightGBM Ranker用のデータセット作成"""
    X = df[features]
    y = df[Config.TARGET]
    group = df.groupby(Config.RACE_ID).size().to_numpy()
    
    return X, y, group


def train_model(
    train_data: Tuple[pd.DataFrame, np.ndarray, np.ndarray],
    valid_data: Tuple[pd.DataFrame, np.ndarray, np.ndarray],
    features: List[str]
) -> lgb.LGBMRanker:
    """モデルの学習"""
    print("\n" + "="*60)
    print("🚀 モデル学習を開始...")
    
    X_train, y_train, group_train = train_data
    X_valid, y_valid, group_valid = valid_data
    
    print(f"   訓練レース数: {len(group_train):,}")
    print(f"   検証レース数: {len(group_valid):,}")
    
    # モデル初期化
    model = lgb.LGBMRanker(**Config.LGBM_PARAMS)
    
    # 学習
    start_time = datetime.now()
    
    model.fit(
        X_train, y_train,
        group=group_train,
        eval_set=[(X_valid, y_valid)],
        eval_group=[group_valid],
        eval_metric="ndcg",
        callbacks=[
            lgb.log_evaluation(period=100),
            lgb.early_stopping(stopping_rounds=50, verbose=True)
        ]
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ 学習完了 (所要時間: {elapsed:.1f}秒)")
    
    return model


def evaluate_model(
    model: lgb.LGBMRanker,
    valid_data: Tuple[pd.DataFrame, np.ndarray, np.ndarray],
    features: List[str]
) -> pd.DataFrame:
    """モデルの評価"""
    print("\n" + "="*60)
    print("📈 モデル評価中...")
    
    X_valid, y_valid, group_valid = valid_data
    
    # 予測
    y_pred = model.predict(X_valid)
    
    # レース単位での評価
    metrics = []
    start_idx = 0
    
    for group_size in group_valid:
        end_idx = start_idx + group_size
        
        race_true = y_valid.iloc[start_idx:end_idx].values
        race_pred = y_pred[start_idx:end_idx]
        
        # NDCG@3の計算（簡易版）
        top3_pred_idx = np.argsort(race_pred)[:3]
        top3_true = race_true[top3_pred_idx]
        
        # 上位3着に入っているかカウント
        hit_top3 = np.sum(top3_true <= 3)
        
        metrics.append({
            "race_size": group_size,
            "hit_top3": hit_top3
        })
        
        start_idx = end_idx
    
    metrics_df = pd.DataFrame(metrics)
    
    # 統計表示
    accuracy_top3 = (metrics_df["hit_top3"] > 0).mean()
    avg_hit = metrics_df["hit_top3"].mean()
    
    print(f"   検証レース数: {len(metrics_df):,}")
    print(f"   Top3的中率: {accuracy_top3:.2%}")
    print(f"   平均的中頭数: {avg_hit:.2f}")
    
    return metrics_df


def save_artifacts(
    model: lgb.LGBMRanker,
    features: List[str],
    metrics: pd.DataFrame
) -> None:
    """モデルと関連ファイルの保存"""
    print("\n" + "="*60)
    print("💾 モデルと結果を保存中...")
    
    # モデル保存
    model.booster_.save_model(str(Config.MODEL_FILE))
    print(f"   ✓ モデル: {Config.MODEL_FILE}")
    
    # 特徴量リスト保存
    joblib.dump(features, Config.FEATURE_LIST_FILE)
    print(f"   ✓ 特徴量リスト: {Config.FEATURE_LIST_FILE}")
    
    # 特徴量重要度
    importance_df = pd.DataFrame({
        "feature": features,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    
    importance_df.to_csv(Config.IMPORTANCE_FILE, index=False)
    print(f"   ✓ 特徴量重要度: {Config.IMPORTANCE_FILE}")
    
    # 評価指標
    metrics.to_csv(Config.METRICS_FILE, index=False)
    print(f"   ✓ 評価指標: {Config.METRICS_FILE}")
    
    # 重要度Top20表示
    print("\n📊 特徴量重要度 (Top 20)")
    print("-" * 60)
    for idx, row in importance_df.head(20).iterrows():
        print(f"   {row['feature']:40s} {row['importance']:>10.1f}")


# =====================
# メイン処理
# =====================
def main():
    """メイン実行関数"""
    print("\n" + "="*60)
    print("🏇 競馬予測モデル学習スクリプト")
    print("="*60)
    
    try:
        # 1. 準備
        setup_directories()
        
        # 2. データ読み込み
        df = load_csv_files()
        
        # 3. 前処理
        df = preprocess_basic(df)
        
        # 4. 特徴量生成
        df = generate_features(df)
        
        # メモリ解放
        gc.collect()
        
        # 5. データセット準備
        features, train_df, valid_df = prepare_dataset(df)
        
        # 6. Ranker用データセット作成
        train_data = create_ranker_dataset(train_df, features)
        valid_data = create_ranker_dataset(valid_df, features)
        
        # メモリ解放
        del df, train_df, valid_df
        gc.collect()
        
        # 7. 学習
        model = train_model(train_data, valid_data, features)
        
        # 8. 評価
        metrics = evaluate_model(model, valid_data, features)
        
        # 9. 保存
        save_artifacts(model, features, metrics)
        
        print("\n" + "="*60)
        print("✅ すべての処理が完了しました！")
        print("="*60)
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ エラーが発生しました: {e}")
        print("="*60)
        raise


if __name__ == "__main__":
    main()
