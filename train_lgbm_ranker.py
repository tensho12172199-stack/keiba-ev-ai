import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
from pathlib import Path
import gc
import glob

# 自作モジュールのインポート
from feature_engineering import apply_all_features
from add_passing_features import add_passing_features
from add_jockey_style_features import add_jockey_style_features
from add_speed_features import add_speed_features
from add_distance_preference_features import add_distance_preference_features
from add_recent_diff_features import add_recent_diff_features

# =====================
# 設定
# =====================
DATA_DIR = Path("data")
OUT_DIR = Path("outputs")
MODEL_FILE = OUT_DIR / "horse_racing_lgbm_ranker.txt"
FEATURE_LIST_FILE = OUT_DIR / "feature_list.pkl"

# カラム名の定義（データセットに合わせて調整してください）
HORSE_KEY = "horse_name"
DATE_KEY = "race_date"
TARGET = "rank"

OUT_DIR.mkdir(exist_ok=True, parents=True)

# =====================
# 1. CSV読み込み
# =====================
print("csvファイルを読み込んでいます...")
csv_files = sorted(DATA_DIR.glob("*.csv"))

if not csv_files:
    # dataディレクトリがない場合のフォールバック（カレントディレクトリも探すなど）
    csv_files = sorted(glob.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError("CSVファイルが見つかりません。dataディレクトリを確認してください。")

dfs = [pd.read_csv(f) for f in csv_files]
df = pd.concat(dfs, ignore_index=True)
print(f"読み込み完了: {len(df):,} 行")

# =====================
# 2. 基本前処理 (feature_engineering.py)
# =====================
print("基本特徴量を処理中...")

# 順位の数値化と欠損除去（除外・中止などを削除）
df[TARGET] = pd.to_numeric(df[TARGET], errors="coerce")
df = df.dropna(subset=[TARGET])
df[TARGET] = df[TARGET].astype(int)

# 日付型変換
if DATE_KEY in df.columns:
    df[DATE_KEY] = pd.to_datetime(df[DATE_KEY], errors="coerce")

# 共通の前処理（年齢、性別、体重、タイム、上がり補正など）
df = apply_all_features(df)

# =====================
# 3. ID生成と並び替え
# =====================
# horse_id がない場合は horse_name から生成
if "horse_id" not in df.columns:
    print("horse_id を horse_name から生成します...")
    df["horse_id"] = pd.factorize(df["horse_name"])[0]

# 特徴量生成のために日付順、レースID順にソート
if DATE_KEY in df.columns:
    df = df.sort_values([DATE_KEY, "race_id"])

# =====================
# 4. 高度な特徴量生成
# =====================
print("通過順特徴量を追加中...")
if "passing" in df.columns:
    df = add_passing_features(df)

print("騎手傾向特徴量を追加中...")
# jockey_profile.csv があれば読み込む、なければ内部でスキップされるかエラーハンドリングが必要
# 実行時は同ディレクトリに jockey_profile.csv を置くことを推奨
if Path("jockey_profile.csv").exists():
    df = add_jockey_style_features(df, jockey_profile_path="jockey_profile.csv")
else:
    print("※ jockey_profile.csv が見つからないため、騎手特徴量はスキップします。")

print("スピード特徴量を追加中...")
df = add_speed_features(df)

print("距離適性特徴量を追加中...")
df = add_distance_preference_features(df)

print("近走差分特徴量を追加中...")
# 数値特徴量の近走平均との乖離を計算
df = add_recent_diff_features(df, n_recent=3)

# =====================
# 5. 人気（Popularity）情報の処理
# =====================
# ※重要度を下げるため、学習用特徴量には含めないが、
# 近走の人気傾向（過大評価/過小評価の推移）だけ計算して残す戦略もあり得る。
# ここではご要望通り「重要度を下げる」ため、あえて人気系の特徴量生成を最小限にし、
# 後のステップで除外リストに追加します。

if "popularity" in df.columns:
    df["popularity"] = pd.to_numeric(df["popularity"], errors="coerce")
    # 人気の変動などを見たい場合はここで計算するが、今回はシンプルにするため省略

# =====================
# 6. 学習用データセット作成
# =====================
print("学習用データを構築中...")

# 除外するカラム（ID、リーク情報、および人気情報）
ignore_cols = [
    "race_id", "race_name", "date", DATE_KEY, 
    "horse_name", "horse_id", "jockey", "trainer", "owner", 
    TARGET, # 正解ラベル
    # === リーク（結果）系 ===
    "time", "time_sec", "time_per_meter", "time_diff_race",
    "passing", "passing_1c", "passing_4c", "passing_gain", # 通過順そのものは結果なので除外
    "age_sex", "horse_weight", "horse_weight_diff",
    # === 重要度を下げるために除外する人気系 ===
    "popularity", "log_popularity", "odds",
    "popularity_recent_avg_3", "popularity_recent_diff_3", # 人気由来の指標も除外
]

# 数値型のみ抽出
numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()

# 特徴量リストの確定
features = [c for c in numeric_cols if c not in ignore_cols]

# LightGBM Ranker は「クエリ（レースID）」ごとにデータが並んでいる必要がある
df = df.sort_values("race_id")

X = df[features]
y = df[TARGET]

# グループ情報の作成（各レースの出走頭数リスト）
# クエリデータの作成（race_id単位でグループ化）
group = df.groupby("race_id").size().to_frame("size")["size"].to_numpy()

print(f"--- データセット情報 ---")
print(f"特徴量数: {len(features)}")
print(f"データ行数: {len(X)}")
print(f"レース数: {len(group)}")
print(f"除外された人気系カラム: popularity, odds 等")
print(f"使用される特徴量例: {features[:10]} ...")

# =====================
# 7. モデル学習 (LGBM Ranker)
# =====================
print("モデル学習開始...")

# Rankerの設定
# 人気要素を除外したため、純粋な能力比較になりやすい
model = lgb.LGBMRanker(
    objective="lambdarank",
    metric="ndcg",
    ndcg_eval_at=[1, 3, 5],
    num_leaves=31,
    learning_rate=0.05,
    n_estimators=800,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    importance_type="gain"
)

# 全データで学習
model.fit(
    X, 
    y, 
    group=group,
    # verbose=100
)

# =====================
# 8. 保存と確認
# =====================
# モデル保存
model.booster_.save_model(str(MODEL_FILE))
# 特徴量リスト保存
joblib.dump(features, FEATURE_LIST_FILE)

print(f"✅ 学習完了")
print(f"モデル保存先: {MODEL_FILE}")
print(f"特徴量リスト: {FEATURE_LIST_FILE}")

# 特徴量重要度の表示
importance = pd.DataFrame({
    "feature": features,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)

print("\n=== Feature Importance (Top 20) ===")
print(importance.head(20))