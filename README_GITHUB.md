# 🏇 競馬予測アプリ

LightGBM RankerとPlackett-Luceモデルを使用した競馬レース予測システム

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

## 🎯 機能

### 予測機能
- **単勝予測** - 各馬の1着確率
- **複勝予測** - 各馬の3着以内確率
- **三連単予測** - 1着→2着→3着の組み合わせTOP10
- **三連複予測** - 1-2-3着（順不同）の組み合わせTOP10
- **複勝狙い** - 両方が3着以内に入る確率の高い馬連TOP20

### URL柔軟対応
以下の形式に対応：
- `https://race.netkeiba.com/race/shutuba.html?race_id=202406030811`
- `https://race.netkeiba.com/race/result.html?race_id=202406030811`
- `https://db.netkeiba.com/race/202406030811`
- `202406030811` (12桁のレースID直接入力)

## 🚀 クイックスタート

### Streamlitアプリの起動

```bash
# 依存ライブラリのインストール
pip install -r requirements.txt

# アプリ起動
streamlit run app.py
```

### コマンドラインで予測

```bash
# URLで予測
python predict_step2.py https://race.netkeiba.com/race/shutuba.html?race_id=202406030811

# レースIDで予測
python predict_step2.py 202406030811
```

## 📦 必要なファイル

```
project/
├── app.py                          # Streamlitアプリ
├── predict_step2.py                # 予測メインスクリプト
├── plackett_luce.py                # Plackett-Luceシミュレーション
├── fetch_race.py                   # レースデータ取得
├── preprocess_predict.py           # 前処理
├── horse_racing_full_model.txt     # 学習済みモデル (※要配置)
└── requirements.txt                # 依存ライブラリ
```

## 🔧 環境構築

### 必要なライブラリ

```bash
pip install -r requirements.txt
```

**requirements.txt:**
```
streamlit
pandas
numpy
requests
beautifulsoup4
lxml
scikit-learn
joblib
lightgbm
```

### Pythonバージョン
- Python 3.8以上推奨

## 📊 使い方

### 1. Webアプリ（推奨）

```bash
streamlit run app.py
```

1. ブラウザが自動で開く
2. レースURLまたはIDを入力
3. 「予測実行」ボタンをクリック
4. 結果を確認

### 2. コマンドライン

```bash
python predict_step2.py <URL or レースID>
```

**出力例:**
```
🏇 レースID: 202406030811
📊 データ取得中...
✓ 出走頭数: 18頭
🔧 特徴量を生成中...
🤖 モデルをロード...
🎯 予測を実行中...
🎲 30,000回シミュレーション中...
✅ 予測完了！

🏇 単勝・複勝予測
================================================================================
 馬番 馬名           単勝確率  複勝確率
    3 スターホース      18.45    52.34
    7 サンダー号        15.23    48.91
   12 ライトニング      12.67    45.12
   ...

🎯 三連単 TOP10
================================================================================
  1着  2着  3着    確率
    3    7   12   2.34
    3   12    7   1.89
    7    3   12   1.67
   ...
```

## 🧠 技術スタック

### モデル
- **LightGBM Ranker** - ランキング学習
- **Plackett-Luce Model** - 着順シミュレーション

### 特徴量
- 通過順特徴量（脚質分析）
- スピード指数
- 距離適性
- 騎手傾向
- 近走成績

### データ取得
- netkeiba.com からスクレイピング
- Beautiful Soup 4使用

## 📈 予測精度

**検証データでの性能:**
- Top3的中率: 約67%
- NDCG@3: 0.78

※過去データでの評価結果。実際のレースでは異なる場合があります。

## ⚠️ 注意事項

- **予測は参考値です** - 実際の投票は自己責任で行ってください
- **スクレイピング** - netkeiba.comの利用規約を遵守してください
- **モデル更新** - 定期的な再学習を推奨します

## 🔄 モデルの学習

学習用スクリプトは別リポジトリで管理：

```bash
# データ前処理
python preprocess_race_data.py horse_race_data_2019.csv

# 学習
python train_lgbm_ranker_improved.py
```

詳細は `docs/TRAINING.md` を参照

## 📁 ファイル構成

```
project/
├── app.py                      # Streamlit Webアプリ
├── predict_step2.py            # 予測メインスクリプト
├── plackett_luce.py            # Plackett-Luceシミュレーション
├── fetch_race.py               # データ取得
├── preprocess_predict.py       # 前処理
├── requirements.txt            # 依存ライブラリ
├── README.md                   # このファイル
├── .gitignore                  # Git除外設定
└── models/
    └── horse_racing_full_model.txt  # 学習済みモデル
```

## 🐛 トラブルシューティング

### モデルファイルが見つからない

```
❌ モデルファイルが見つかりません: horse_racing_full_model.txt
```

**解決策:**
1. 学習済みモデルをダウンロード
2. プロジェクトルートに配置

### レースデータが取得できない

```
❌ 出走馬データが取得できませんでした
```

**原因:**
- URLが間違っている
- レースがまだ出走表が公開されていない
- ネットワークエラー

**解決策:**
- URLを確認
- 出走表公開後に再実行

## 🤝 貢献

Issue、Pull Request歓迎！

## 📄 ライセンス

MIT License

## 👤 作成者

あなたの名前

## 🔗 リンク

- [Streamlit Documentation](https://docs.streamlit.io/)
- [LightGBM Documentation](https://lightgbm.readthedocs.io/)
- [netkeiba.com](https://www.netkeiba.com/)
