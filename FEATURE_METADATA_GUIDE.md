# 📊 特徴量メタデータ活用ガイド

## 🎯 目的

学習時に使用した特徴量の情報を保存し、予測時に**完全に同じ特徴量を再現**します。

---

## 💡 なぜ必要か？

### 問題

学習と予測で特徴量生成のパラメータが異なると、精度が低下します。

```python
# 学習時
add_recent_diff_features(df, n_recent=5)  # 直近5走

# 予測時
add_recent_diff_features(df, n_recent=3)  # 直近3走 ← 不一致！
```

### 解決

特徴量メタデータを保存することで、学習時のパラメータを予測時に自動適用！

---

## 🏗️ システム構成

### 保存される情報

```json
{
  "feature_list": ["age", "sex", "speed", "speed_recent_avg_3", ...],
  "feature_groups": {
    "basic_features": ["age", "sex", "weight_carrier"],
    "speed_features": ["speed", "speed_recent_avg_3"],
    "recent_diff_features": ["speed_recent_diff_3", ...]
  },
  "preprocessing_params": {
    "n_recent": 3,
    "train_end_date": "2024-06-30"
  },
  "feature_stats": {
    "speed": {
      "mean": 14.5,
      "std": 1.2,
      "min": 10.1,
      "max": 18.3,
      "dtype": "float64"
    },
    ...
  },
  "config": {
    "features": {...},
    "lgbm": {...}
  }
}
```

---

## 🚀 使い方（自動）

### ステップ1: 学習時（自動保存）

```bash
python train_lgbm_ranker_config.py
```

**自動実行:**
```
💾 モデルと結果を保存中...
   ✓ モデル: horse_racing_full_model.txt
   ✓ 特徴量リスト: feature_list.pkl
   ✓ 特徴量メタデータ: feature_metadata.json  ← NEW!
```

### ステップ2: 予測時（自動読み込み）

```bash
python predict_step2.py 202406030811
```

**自動実行:**
```
🔧 特徴量を生成中...
   ✓ 特徴量メタデータを読み込みました
   ✓ 直近3走を使用  ← 学習時と同じパラメータ！
```

---

## 📦 生成されるファイル

### 学習時

```
project/
├── horse_racing_full_model.txt     # モデル本体
├── feature_list.pkl                # 特徴量リスト
├── feature_metadata.json           # メタデータ ← NEW!
└── outputs/
    ├── feature_importance.csv
    └── training_metrics.csv
```

### 予測時の読み込み順

1. `feature_metadata.json` → パラメータ取得
2. パラメータに基づいて特徴量生成
3. `feature_list.pkl` → 特徴量の順序確認
4. モデルで予測

---

## 🔍 メタデータの確認

### Pythonで確認

```python
from feature_metadata import FeatureMetadata

# 読み込み
metadata = FeatureMetadata.load("feature_metadata.json")

# サマリー表示
metadata.print_summary()
```

**出力:**
```
================================================================================
📊 特徴量メタデータ サマリー
================================================================================

📋 特徴量数: 104

🗂️  特徴量グループ:
   basic_features                : 6個
   speed_features                : 15個
   passing_features              : 8個
   jockey_features               : 12個
   recent_diff_features          : 63個

⚙️  前処理パラメータ:
   n_recent                      : 3
   train_end_date                : 2024-06-30

📈 統計情報（サンプル）:
   speed                         : mean=14.52, std=1.18
   age                           : mean=4.23, std=1.56
   weight_carrier                : mean=56.12, std=2.34
================================================================================
```

### 特定の特徴量の詳細

```python
# 特徴量の情報を取得
info = metadata.get_feature_info("speed_recent_avg_3")

print(info)
```

**出力:**
```python
{
  'name': 'speed_recent_avg_3',
  'stats': {
    'mean': 14.48,
    'std': 1.23,
    'min': 10.2,
    'max': 18.1,
    'dtype': 'float64',
    'null_count': 1234
  },
  'group': 'recent_diff_features'
}
```

---

## 💻 手動で活用する場合

### 学習時に手動保存

```python
from feature_metadata import extract_feature_metadata_from_training
from config_utils import TrainingConfig

# 学習後
config = TrainingConfig("training_config.yaml")
metadata = extract_feature_metadata_from_training(
    train_df,
    features,
    config
)

# 保存
metadata.save("feature_metadata.json")
```

### 予測時に手動読み込み

```python
from feature_metadata import FeatureMetadata

# メタデータ読み込み
metadata = FeatureMetadata.load("feature_metadata.json")

# パラメータを取得
n_recent = metadata.preprocessing_params['n_recent']

# 特徴量生成に使用
df = add_recent_diff_features(df, n_recent=n_recent)
```

---

## 🎯 活用例

### 例1: 直近N走の数を確認

```python
metadata = FeatureMetadata.load("feature_metadata.json")
n_recent = metadata.preprocessing_params.get('n_recent', 3)

print(f"学習時は直近{n_recent}走を使用")
```

### 例2: 特徴量グループごとの数を確認

```python
metadata = FeatureMetadata.load("feature_metadata.json")

for group_name, features in metadata.feature_groups.items():
    print(f"{group_name}: {len(features)}個")
```

**出力:**
```
basic_features: 6個
speed_features: 15個
passing_features: 8個
jockey_features: 12個
recent_diff_features: 63個
```

### 例3: 欠損値が多い特徴量を確認

```python
metadata = FeatureMetadata.load("feature_metadata.json")

# 欠損値が多い特徴量を抽出
high_null = []
for feature, stats in metadata.feature_stats.items():
    if stats.get('null_count', 0) > 1000:
        high_null.append((feature, stats['null_count']))

# ソートして表示
high_null.sort(key=lambda x: x[1], reverse=True)
for feature, null_count in high_null[:10]:
    print(f"{feature}: {null_count}個")
```

---

## 🔧 トラブルシューティング

### Q: feature_metadata.json が見つからない

```
⚠️  メタデータなし（デフォルトパラメータを使用）
```

**原因:**
- 学習スクリプトを古いバージョンで実行した
- メタデータの保存に失敗した

**解決策:**
```bash
# 最新の学習スクリプトで再学習
python train_lgbm_ranker_config.py
```

### Q: メタデータの内容が間違っている

**確認方法:**
```python
metadata = FeatureMetadata.load("feature_metadata.json")
metadata.print_summary()

# 特徴量数が正しいか確認
print(f"特徴量数: {len(metadata.feature_list)}")

# パラメータが正しいか確認
print(f"n_recent: {metadata.preprocessing_params.get('n_recent')}")
```

**修正方法:**
学習をやり直して、メタデータを再生成。

### Q: 予測時にメタデータが使われていない

**確認方法:**
```python
# preprocess_predict.py 内でログを確認
# "✓ 特徴量メタデータを読み込みました" が表示されるか？
```

**解決策:**
```python
# metadata_path を明示的に指定
X = preprocess_for_prediction(
    df_race,
    metadata_path="feature_metadata.json"
)
```

---

## 📈 メリット

### Before（メタデータなし）

```python
# 学習時
add_recent_diff_features(df, n_recent=3)

# 予測時（手動でパラメータ指定）
add_recent_diff_features(df, n_recent=3)  # 間違えやすい
```

**問題:**
- パラメータを手動で合わせる必要がある
- 間違えると精度が低下
- 再現性が低い

### After（メタデータあり）

```python
# 学習時
metadata.save("feature_metadata.json")  # 自動保存

# 予測時
metadata = FeatureMetadata.load("feature_metadata.json")  # 自動読み込み
n_recent = metadata.preprocessing_params['n_recent']  # 自動取得
add_recent_diff_features(df, n_recent=n_recent)  # 確実
```

**メリット:**
- ✅ パラメータが自動で一致
- ✅ 再現性が高い
- ✅ 間違えない

---

## 📚 まとめ

### 自動で動作

1. **学習**: `python train_lgbm_ranker_config.py`
   - `feature_metadata.json` を自動保存

2. **予測**: `python predict_step2.py 202406030811`
   - `feature_metadata.json` を自動読み込み
   - 学習時と同じパラメータで特徴量生成

### 手動で確認

```python
from feature_metadata import FeatureMetadata

metadata = FeatureMetadata.load("feature_metadata.json")
metadata.print_summary()
```

これで、学習と予測で完全に同じ特徴量を再現できます！🎊
