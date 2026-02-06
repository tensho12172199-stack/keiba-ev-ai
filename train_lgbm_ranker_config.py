"""
競馬予測モデル学習スクリプト（設定ファイル対応版）

training_config.yaml から設定を読み込み、
特徴量の重み付けや実験管理を簡単に行えます。

使用方法:
    # デフォルト設定で実行
    python train_lgbm_ranker_config.py
    
    # 実験を指定して実行
    python train_lgbm_ranker_config.py --experiment weak_recent
    
    # カスタム設定ファイルを使用
    python train_lgbm_ranker_config.py --config my_config.yaml
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
from pathlib import Path
import gc
import glob
import warnings
from datetime import datetime
from typing import List, Tuple
import argparse

# 自作モジュールのインポート
from feature_engineering import apply_all_features
from add_passing_features import add_passing_features
from add_jockey_style_features import add_jockey_style_features
from add_speed_features import add_speed_features
from add_distance_preference_features import add_distance_preference_features
from add_recent_diff_features import add_recent_diff_features
from config_utils import TrainingConfig
from feature_metadata import FeatureMetadata, extract_feature_metadata_from_training

warnings.filterwarnings('ignore')


def load_csv_files(data_dir: Path) -> pd.DataFrame:
    """CSVファイルの読み込み"""
    print("\n" + "="*60)
    print("📂 CSVファイルを読み込んでいます...")
    
    csv_files = sorted(data_dir.glob("*.csv"))
    
    if not csv_files:
        csv_files = sorted(glob.glob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(
                f"❌ CSVファイルが見つかりません。\n"
                f"   {data_dir} ディレクトリを確認してください。"
            )
    
    print(f"   見つかったファイル: {len(csv_files)}個")
    for f in csv_files:
        name = f.name if hasattr(f, 'name') else Path(f).name
        print(f"   - {name}")
    
    dfs = []
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            dfs.append(df)
        except Exception as e:
            name = f.name if hasattr(f, 'name') else Path(f).name
            print(f"⚠️  {name} の読み込みに失敗: {e}")
    
    if not dfs:
        raise ValueError("有効なCSVファイルがありません")
    
    df = pd.concat(dfs, ignore_index=True)
    print(f"✅ 読み込み完了: {len(df):,} 行")
    
    return df


def preprocess_basic(df: pd.DataFrame, target: str, date_key: str) -> pd.DataFrame:
    """基本的な前処理"""
    print("\n" + "="*60)
    print("🔧 基本前処理を実行中...")
    
    initial_rows = len(df)
    
    # 順位の数値化と欠損除去
    df[target] = pd.to_numeric(df[target], errors="coerce")
    df = df.dropna(subset=[target])
    df[target] = df[target].astype(int)
    
    removed_rows = initial_rows - len(df)
    if removed_rows > 0:
        print(f"   無効な順位データを除去: {removed_rows:,} 行")
    
    # 日付型変換
    if date_key in df.columns:
        df[date_key] = pd.to_datetime(df[date_key], errors="coerce")
        date_nulls = df[date_key].isna().sum()
        if date_nulls > 0:
            print(f"   ⚠️  日付が無効: {date_nulls:,} 行")
    
    # 共通の前処理
    df = apply_all_features(df)
    
    print(f"✅ 基本前処理完了: {len(df):,} 行")
    
    return df


def generate_features(df: pd.DataFrame, config: TrainingConfig) -> pd.DataFrame:
    """高度な特徴量生成"""
    print("\n" + "="*60)
    print("🎯 特徴量生成を実行中...")
    
    data_config = config.get_data_config()
    horse_key = data_config['horse_key']
    date_key = data_config['date_key']
    race_id = data_config['race_id']
    
    # horse_id がない場合は生成
    if "horse_id" not in df.columns and horse_key in df.columns:
        print(f"   horse_id を {horse_key} から生成")
        df["horse_id"] = pd.factorize(df[horse_key])[0]
    
    # ソート
    if date_key in df.columns:
        df = df.sort_values([date_key, race_id])
    
    # 各特徴量の追加
    n_recent = config.config['features']['n_recent']
    
    feature_funcs = [
        ("通過順特徴量", add_passing_features, ["passing"]),
        ("スピード特徴量", add_speed_features, ["distance", "time_sec"]),
        ("距離適性特徴量", add_distance_preference_features, ["distance", "speed"]),
        ("騎手傾向特徴量", lambda x: add_jockey_style_features(x, config.get_paths()['jockey_profile']), ["jockey"]),
        ("近走差分特徴量", lambda x: add_recent_diff_features(x, n_recent=n_recent), []),
    ]
    
    for name, func, required_cols in feature_funcs:
        try:
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"   ⚠️  {name}: 必須カラムが不足 {missing_cols} - スキップ")
                continue
            
            print(f"   ✓ {name} を追加中...")
            df = func(df)
        except Exception as e:
            print(f"   ⚠️  {name} の生成に失敗: {e}")
    
    print(f"✅ 特徴量生成完了")
    
    return df


def prepare_dataset(
    df: pd.DataFrame,
    config: TrainingConfig
) -> Tuple[List[str], pd.DataFrame, pd.DataFrame]:
    """学習用データセットの準備"""
    print("\n" + "="*60)
    print("📊 データセットを構築中...")
    
    data_config = config.get_data_config()
    date_key = data_config['date_key']
    race_id = data_config['race_id']
    train_end_date = data_config['train_end_date']
    
    # 数値型のみ抽出
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    
    # 設定ファイルに基づいて特徴量をフィルタ
    features = config.filter_features(numeric_cols)
    
    print(f"   特徴量数: {len(features)}")
    
    # データ分割
    if date_key in df.columns:
        train_end = pd.to_datetime(train_end_date)
        train_df = df[df[date_key] <= train_end].copy()
        valid_df = df[df[date_key] > train_end].copy()
        
        print(f"   訓練データ: {len(train_df):,} 行 (～{train_end_date})")
        print(f"   検証データ: {len(valid_df):,} 行 ({train_end_date}～)")
    else:
        print("   ⚠️  日付カラムがないため、ランダムに8:2分割")
        train_df = df.sample(frac=0.8, random_state=42)
        valid_df = df.drop(train_df.index)
        
        print(f"   訓練データ: {len(train_df):,} 行")
        print(f"   検証データ: {len(valid_df):,} 行")
    
    # レースIDでソート
    train_df = train_df.sort_values(race_id)
    valid_df = valid_df.sort_values(race_id)
    
    return features, train_df, valid_df


def create_ranker_dataset(
    df: pd.DataFrame,
    features: List[str],
    target: str,
    race_id: str,
    config: TrainingConfig
) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """LightGBM Ranker用のデータセット作成（重み付き）"""
    X = df[features].copy()
    
    # 特徴量の重み付けを適用
    X = config.apply_feature_weights(X)
    
    y = df[target]
    group = df.groupby(race_id).size().to_numpy()
    
    return X, y, group


def train_model(
    train_data: Tuple[pd.DataFrame, np.ndarray, np.ndarray],
    valid_data: Tuple[pd.DataFrame, np.ndarray, np.ndarray],
    features: List[str],
    config: TrainingConfig
) -> lgb.LGBMRanker:
    """モデルの学習"""
    print("\n" + "="*60)
    print("🚀 モデル学習を開始...")
    
    X_train, y_train, group_train = train_data
    X_valid, y_valid, group_valid = valid_data
    
    print(f"   訓練レース数: {len(group_train):,}")
    print(f"   検証レース数: {len(group_valid):,}")
    
    # LightGBMパラメータを取得
    lgbm_params = config.get_lgbm_params()
    
    # モデル初期化
    model = lgb.LGBMRanker(**lgbm_params)
    
    # 学習
    start_time = datetime.now()
    
    eval_period = config.config['logging']['log_evaluation_period']
    early_stopping = lgbm_params.get('early_stopping_rounds', 50)
    
    model.fit(
        X_train, y_train,
        group=group_train,
        eval_set=[(X_valid, y_valid)],
        eval_group=[group_valid],
        eval_metric="ndcg",
        callbacks=[
            lgb.log_evaluation(period=eval_period),
            lgb.early_stopping(stopping_rounds=early_stopping, verbose=True)
        ]
    )
    
    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n✅ 学習完了 (所要時間: {elapsed:.1f}秒)")
    
    return model


def evaluate_model(
    model: lgb.LGBMRanker,
    valid_data: Tuple[pd.DataFrame, np.ndarray, np.ndarray]
) -> pd.DataFrame:
    """モデルの評価"""
    print("\n" + "="*60)
    print("📈 モデル評価中...")
    
    X_valid, y_valid, group_valid = valid_data
    
    y_pred = model.predict(X_valid)
    
    metrics = []
    start_idx = 0
    
    for group_size in group_valid:
        end_idx = start_idx + group_size
        
        race_true = y_valid.iloc[start_idx:end_idx].values
        race_pred = y_pred[start_idx:end_idx]
        
        top3_pred_idx = np.argsort(race_pred)[:3]
        top3_true = race_true[top3_pred_idx]
        
        hit_top3 = np.sum(top3_true <= 3)
        
        metrics.append({
            "race_size": group_size,
            "hit_top3": hit_top3
        })
        
        start_idx = end_idx
    
    metrics_df = pd.DataFrame(metrics)
    
    accuracy_top3 = (metrics_df["hit_top3"] > 0).mean()
    avg_hit = metrics_df["hit_top3"].mean()
    
    print(f"   検証レース数: {len(metrics_df):,}")
    print(f"   Top3的中率: {accuracy_top3:.2%}")
    print(f"   平均的中頭数: {avg_hit:.2f}")
    
    return metrics_df


def save_artifacts(
    model: lgb.LGBMRanker,
    features: List[str],
    metrics: pd.DataFrame,
    config: TrainingConfig,
    train_df: pd.DataFrame = None
) -> None:
    """モデルと結果を保存"""
    print("\n" + "="*60)
    print("💾 モデルと結果を保存中...")
    
    paths = config.get_paths()
    out_dir = Path(paths['output_dir'])
    out_dir.mkdir(exist_ok=True, parents=True)
    
    # モデル保存
    joblib.dump(model, paths['model_file'])
    print(f"   ✓ モデル: {paths['model_file']}")
    
    # 特徴量リスト保存
    joblib.dump(features, paths['feature_list_file'])
    print(f"   ✓ 特徴量リスト: {paths['feature_list_file']}")
    
    # 特徴量メタデータ保存（NEW!）
    if train_df is not None:
        try:
            metadata = extract_feature_metadata_from_training(train_df, features, config)
            metadata.save("feature_metadata.json")
            print(f"   ✓ 特徴量メタデータ: feature_metadata.json")
        except Exception as e:
            print(f"   ⚠️  メタデータ保存エラー: {e}")
    
    # 特徴量重要度
    importance_df = pd.DataFrame({
        "feature": features,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    
    importance_file = out_dir / "feature_importance.csv"
    importance_df.to_csv(importance_file, index=False)
    print(f"   ✓ 特徴量重要度: {importance_file}")
    
    # 評価指標
    metrics_file = out_dir / "training_metrics.csv"
    metrics.to_csv(metrics_file, index=False)
    print(f"   ✓ 評価指標: {metrics_file}")
    
    # 重要度表示
    show_n = config.config['logging']['show_feature_importance']
    print(f"\n📊 特徴量重要度 (Top {show_n})")
    print("-" * 60)
    for idx, row in importance_df.head(show_n).iterrows():
        print(f"   {row['feature']:40s} {row['importance']:>10.1f}")


def main(args):
    """メイン実行関数"""
    print("\n" + "="*80)
    print("🏇 競馬予測モデル学習スクリプト（設定ファイル対応版）")
    print("="*80)
    
    try:
        # 設定読み込み
        config = TrainingConfig(args.config)
        
        # アクティブな実験を切り替え
        if args.experiment:
            config.config['active_experiment'] = args.experiment
            config._apply_experiment()
        
        config.print_summary()
        
        data_config = config.get_data_config()
        paths = config.get_paths()
        
        # データ読み込み
        df = load_csv_files(Path(paths['data_dir']))
        
        # 前処理
        df = preprocess_basic(df, data_config['target'], data_config['date_key'])
        
        # 特徴量生成
        df = generate_features(df, config)
        
        gc.collect()
        
        # データセット準備
        features, train_df, valid_df = prepare_dataset(df, config)
        
        # 学習データのコピーを保持（メタデータ用）
        train_df_for_metadata = train_df[features].copy()
        
        # Ranker用データセット作成（重み付き）
        train_data = create_ranker_dataset(
            train_df, features, data_config['target'], data_config['race_id'], config
        )
        valid_data = create_ranker_dataset(
            valid_df, features, data_config['target'], data_config['race_id'], config
        )
        
        del df, train_df, valid_df
        gc.collect()
        
        # 学習
        model = train_model(train_data, valid_data, features, config)
        
        # 評価
        metrics = evaluate_model(model, valid_data)
        
        # 保存（メタデータ付き）
        save_artifacts(model, features, metrics, config, train_df_for_metadata)
        
        print("\n" + "="*80)
        print("✅ すべての処理が完了しました！")
        print("="*80)
        
    except Exception as e:
        print("\n" + "="*80)
        print(f"❌ エラーが発生しました: {e}")
        print("="*80)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="競馬予測モデル学習（設定ファイル対応）")
    parser.add_argument(
        '--config',
        type=str,
        default='training_config.yaml',
        help='設定ファイルのパス（デフォルト: training_config.yaml）'
    )
    parser.add_argument(
        '--experiment',
        type=str,
        default=None,
        help='実験名を指定（例: weak_recent, balanced）'
    )
    
    args = parser.parse_args()
    main(args)
