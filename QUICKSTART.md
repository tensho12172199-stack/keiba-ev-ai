# 🏇 競馬予測モデル クイックスタートガイド

## 📦 セットアップ（初回のみ）

### 1. 必要なライブラリをインストール

```bash
pip install pandas numpy lightgbm scikit-learn joblib pyyaml
```

### 2. ファイル構成を確認

```
your_project/
├── data/                              # 📁 学習データ置き場
│   ├── race_2023.csv
│   └── race_2024.csv
├── jockey_profile.csv                 # 🏇 騎手プロファイル（オプション）
│
├── train_lgbm_ranker_improved.py      # 🎓 学習スクリプト（NEW!）
├── predict.py                         # 🔮 予測スクリプト（NEW!）
├── config.yaml                        # ⚙️ 設定ファイル（NEW!）
│
├── feature_engineering.py             # 既存モジュール
├── add_passing_features.py
├── add_jockey_style_features.py
├── add_speed_features.py
├── add_distance_preference_features.py
└── add_recent_diff_features.py
```

## 🚀 使い方（4ステップ）

### ステップ0️⃣: データの前処理（distanceカラムがない場合）

**あなたのデータに`distance`カラムがない場合、まずこのステップを実行：**

```bash
# race_detailsから距離を抽出
python preprocess_race_data.py horse_race_data_2019.csv
```

**何が起こる？**
- `race_details`から距離、コース種別、天候などを自動抽出
- `horse_race_data_2019_processed.csv`が作成される
- 47,574行すべてで100%成功！

**複数年のデータを一括処理：**
```bash
python batch_preprocess.py horse_race_data_*.csv
```

**詳しくは：** [DATA_PREPROCESSING_GUIDE.md](DATA_PREPROCESSING_GUIDE.md) を参照

---

### ステップ1️⃣: モデルの学習

```bash
python train_lgbm_ranker_improved.py
```

**何が起こる？**
- `data/`フォルダのCSVを全部読み込む
- 特徴量を自動生成
- モデルを学習
- `outputs/`に結果を保存

**確認ポイント：**
```
✅ 学習完了 (所要時間: 45.3秒)
   Top3的中率: 67.23%
   ↑ この数値が60%以上なら良好！
```

### ステップ2️⃣: 予測の実行

```bash
python predict.py data/race_2024_new.csv
```

**何が起こる？**
- 新しいレースデータを読み込む
- 学習済みモデルで予測
- `outputs/predictions.csv`に結果を保存

### ステップ3️⃣: 結果の確認

```bash
# CSVファイルで確認
cat outputs/predictions.csv

# または Excel で開く
# outputs/predictions.csv をダブルクリック
```

## 📊 出力ファイルの見方

### outputs/predictions.csv

| race_id | horse_name | predicted_rank | prediction_score | jockey |
|---------|-----------|----------------|------------------|--------|
| R001    | スターホース | 1 | 8.234 | 武豊 |
| R001    | サンダー号 | 2 | 7.891 | 岩田康誠 |
| R001    | ライトニング | 3 | 7.456 | 川田将雅 |

- **predicted_rank**: 予測順位（1が最も勝つ可能性が高い）
- **prediction_score**: 予測スコア（高いほど強い）

## 🎨 カスタマイズ

### パラメータを変更したい

`train_lgbm_ranker_improved.py`の`Config`クラスを編集：

```python
class Config:
    # 訓練データの期間を変更
    TRAIN_END_DATE = "2024-08-31"  # ← ここを変更
    
    # LightGBMのパラメータ調整
    LGBM_PARAMS = {
        "learning_rate": 0.03,     # 遅くすると精度UP、時間かかる
        "num_leaves": 63,          # 大きくすると複雑なモデル
        "n_estimators": 1000,      # 増やすと学習時間↑
        # ...
    }
```

### 除外する特徴量を追加

```python
IGNORE_COLS = [
    # ... 既存のリスト ...
    "my_custom_column",  # ← 追加
]
```

## 🔍 トラブルシューティング

### ❓ distanceカラムが見つからない

```
⚠️  スピード特徴量: 必須カラムが不足 ['distance'] - スキップ
```

**解決策：**

元のCSVに`distance`カラムがない場合、`race_details`から抽出します：

```bash
# 自動抽出スクリプトを実行
python preprocess_race_data.py your_data.csv
```

これで`your_data_processed.csv`が作成され、`distance`カラムが追加されます。

**詳しい手順：** [DATA_PREPROCESSING_GUIDE.md](DATA_PREPROCESSING_GUIDE.md)

---

### ❓ CSVファイルが見つからない

```
❌ CSVファイルが見つかりません。
   data ディレクトリを確認してください。
```

**解決策：**
1. `data/`フォルダを作成
2. CSVファイルを`data/`に配置

---

### ❓ 特徴量が不足している

```
⚠️  不足している特徴量: 5個
```

**原因：**
- 予測データに必要なカラムがない
- 過去レースのデータがない（近走特徴量が作れない）

**解決策：**
- 予測データに過去3レース分のデータを含める
- または、不足分は自動で0埋めされるので無視してもOK

---

### ❓ メモリ不足エラー

```
MemoryError: Unable to allocate...
```

**解決策：**
1. データを分割して学習
2. パラメータを調整：
```python
LGBM_PARAMS = {
    "max_bin": 128,  # デフォルト255から削減
    "n_estimators": 500,  # 削減
}
```

---

### ❓ 精度が低い（的中率50%以下）

**チェックリスト：**
- [ ] データ量は十分？（最低1000レース以上推奨）
- [ ] `jockey_profile.csv`は用意した？
- [ ] 訓練データの期間は適切？
- [ ] 予測データと訓練データの競馬場は同じ？

**改善方法：**
1. データを増やす
2. 特徴量を追加（新しいアイデアを実装）
3. パラメータチューニング（Optuna使用を検討）

## 💡 次のステップ

### レベル1: 基本の使いこなし ✅
- [x] データ読み込み
- [x] モデル学習
- [x] 予測実行

### レベル2: カスタマイズ
- [ ] パラメータ調整で精度向上
- [ ] 新しい特徴量の追加
- [ ] グラフで結果を可視化

### レベル3: 高度な活用
- [ ] ハイパーパラメータ自動最適化（Optuna）
- [ ] アンサンブル学習（複数モデル組み合わせ）
- [ ] リアルタイム予測API化

## 📚 参考情報

### コードの設計思想

このコードは以下の原則で設計されています：

1. **関数型プログラミング**
   - 小さな関数の組み合わせ
   - データの不変性を意識

2. **オブジェクト指向**
   - Configクラスで設定を管理
   - 責任の分離

3. **可読性重視**
   - 絵文字とコメントで分かりやすく
   - エラーメッセージを丁寧に

→ あなたの「段階的に処理を組み立てる」思考スタイルに最適化！

### よくある質問（FAQ）

**Q: 学習にどれくらい時間がかかる？**
A: データ量による。目安：
- 1万レース → 30秒～1分
- 5万レース → 2～3分
- 10万レース → 5～10分

**Q: GPUは必要？**
A: 不要。CPUで十分速い。

**Q: Windowsで動く？**
A: はい、Mac/Linux/Windows すべてOK

**Q: オッズや人気を予測に使いたい**
A: `Config.IGNORE_COLS`から除外すればOK
   ただし過学習に注意

## 🤝 サポート

困ったことがあれば：
1. エラーメッセージを確認
2. このガイドのトラブルシューティングを確認
3. ログ全体を保存して相談

Happy Predicting! 🎉
