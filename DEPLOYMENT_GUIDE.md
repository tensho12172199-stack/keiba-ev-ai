# 🚀 GitHub反映とStreamlitデプロイガイド

## 📋 目次

1. [GitHub反映手順](#github反映手順)
2. [Streamlit Cloudデプロイ](#streamlit-cloudデプロイ)
3. [トラブルシューティング](#トラブルシューティング)

---

## 🔄 GitHub反映手順

### ステップ1: リポジトリの準備

#### 新規リポジトリの場合

```bash
# GitHubで新規リポジトリを作成（Webブラウザで）
# リポジトリ名: horse-racing-prediction (例)

# ローカルで初期化
cd your_project_directory
git init
```

#### 既存リポジトリの場合

```bash
cd your_project_directory
```

### ステップ2: ファイルの配置

以下のファイルが必要です：

```
project/
├── app.py                          # Streamlitアプリ ✅
├── predict_step2.py                # 予測スクリプト ✅
├── plackett_luce.py                # シミュレーション ✅
├── fetch_race.py                   # データ取得 (要準備)
├── preprocess_predict.py           # 前処理 (要準備)
├── horse_racing_full_model.txt     # モデル (要配置)
├── requirements.txt                # 依存関係 ✅
├── README.md                       # ドキュメント ✅
└── .gitignore                      # Git除外設定 ✅
```

### ステップ3: Gitコミット

```bash
# ファイルを追加
git add app.py
git add predict_step2.py
git add plackett_luce.py
git add requirements.txt
git add README.md
git add .gitignore

# fetch_race.py と preprocess_predict.py も追加
git add fetch_race.py
git add preprocess_predict.py

# モデルファイル（大きい場合はGit LFSを使用）
git add horse_racing_full_model.txt

# コミット
git commit -m "Initial commit: 競馬予測アプリv1.0

- Streamlit Webアプリ
- URL柔軟対応
- 三連単・三連複・複勝予測機能
- Plackett-Luceシミュレーション
"
```

### ステップ4: GitHubにプッシュ

```bash
# リモートリポジトリを追加
git remote add origin https://github.com/YOUR_USERNAME/horse-racing-prediction.git

# メインブランチにプッシュ
git branch -M main
git push -u origin main
```

---

## ☁️ Streamlit Cloudデプロイ

### ステップ1: Streamlit Cloudにサインイン

1. [Streamlit Cloud](https://streamlit.io/cloud) にアクセス
2. GitHubアカウントでサインイン
3. 「New app」をクリック

### ステップ2: アプリの設定

1. **Repository**: `YOUR_USERNAME/horse-racing-prediction`
2. **Branch**: `main`
3. **Main file path**: `app.py`

### ステップ3: デプロイ

「Deploy!」ボタンをクリック

数分後、アプリがデプロイされます。

### ステップ4: URL確認

デプロイが完了すると、以下のようなURLが発行されます：
```
https://your-app-name.streamlit.app
```

---

## 📦 モデルファイルの扱い

### 問題: モデルファイルが大きすぎる

GitHubは100MBを超えるファイルを拒否します。

### 解決策1: Git LFS使用

```bash
# Git LFSをインストール
git lfs install

# モデルファイルをLFS管理に
git lfs track "*.txt"
git add .gitattributes
git add horse_racing_full_model.txt
git commit -m "Add model with Git LFS"
git push
```

### 解決策2: Streamlit Secretsで外部URL

1. モデルをGoogle DriveやDropboxにアップロード
2. Streamlit Secretsに URL を設定
3. アプリ起動時にダウンロード

**app.py に追加:**
```python
import streamlit as st
import requests

@st.cache_resource
def download_model():
    url = st.secrets["model_url"]
    response = requests.get(url)
    with open("horse_racing_full_model.txt", "wb") as f:
        f.write(response.content)
    return "horse_racing_full_model.txt"

# 使用
model_path = download_model()
```

**Streamlit Cloud で Secrets設定:**
1. アプリの設定画面
2. 「Secrets」タブ
3. 以下を追加:
```toml
model_url = "https://your-storage-url/horse_racing_full_model.txt"
```

---

## 🔧 トラブルシューティング

### ❌ モジュールが見つからない

```
ModuleNotFoundError: No module named 'fetch_race'
```

**解決策:**
- `fetch_race.py` がリポジトリに含まれているか確認
- Streamlit Cloudで再デプロイ

### ❌ モデルファイルが見つからない

```
FileNotFoundError: horse_racing_full_model.txt
```

**解決策:**
- Git LFS を使用しているか確認
- または外部URLからダウンロードする方式に変更

### ❌ requirements.txtのエラー

```
ERROR: Could not find a version that satisfies the requirement
```

**解決策:**
- `requirements.txt` のバージョンを確認
- 不要なライブラリを削除

**最小限のrequirements.txt:**
```
streamlit==1.30.0
pandas==2.0.3
numpy==1.24.3
lightgbm==4.1.0
scikit-learn==1.3.2
joblib==1.3.2
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
```

### ❌ メモリ不足

```
MemoryError
```

**解決策:**
- シミュレーション回数を減らす（30000 → 10000）
- モデルサイズを削減

---

## 📝 更新手順

コードを更新してGitHubに反映：

```bash
# ファイルを編集
nano app.py

# 変更を確認
git status
git diff

# コミット
git add app.py
git commit -m "Update: UI改善"

# プッシュ
git push
```

Streamlit Cloudが自動的に再デプロイします。

---

## 🎯 チェックリスト

デプロイ前の確認事項：

- [ ] すべての必要なファイルがリポジトリにある
- [ ] `requirements.txt` が正しい
- [ ] モデルファイルが配置されている（またはダウンロード機能がある）
- [ ] `.gitignore` で不要なファイルを除外
- [ ] `README.md` が充実している
- [ ] ローカルで動作確認済み

---

## 🔗 参考リンク

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-community-cloud)
- [Git LFS](https://git-lfs.github.com/)
- [GitHub Documentation](https://docs.github.com/)

---

## 💡 Tips

### 開発環境とプロダクション環境の分離

```python
# app.py
import os

# 環境判定
IS_PRODUCTION = os.getenv("STREAMLIT_SHARING") is not None

if IS_PRODUCTION:
    MODEL_PATH = download_model()  # 外部からダウンロード
else:
    MODEL_PATH = "horse_racing_full_model.txt"  # ローカルファイル
```

### デバッグモード

```python
# app.py
DEBUG = st.sidebar.checkbox("デバッグモード")

if DEBUG:
    st.write("デバッグ情報:")
    st.write(f"モデルパス: {MODEL_PATH}")
    st.write(f"Python: {sys.version}")
    st.write(f"環境変数: {dict(os.environ)}")
```

---

以上でGitHub反映とStreamlitデプロイが完了です！🎉
