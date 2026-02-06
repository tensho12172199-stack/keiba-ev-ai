# 🔧 Streamlit Cloud エラー対処ガイド

## ❌ よくあるエラーと解決方法

---

## エラー1: `supabase is not a valid editable requirement`

### エラーメッセージ
```
ERROR: supabase is not a valid editable requirement. 
It should either be a path to a local project or a VCS URL
```

### 原因
`requirements.txt`の記述が間違っています：
```
-e supabase  ← 間違い
```

### 解決方法

**requirements.txtを修正:**
```txt
streamlit
pandas
numpy
requests
beautifulsoup4
lxml
scikit-learn
joblib
lightgbm
supabase          ← 正しい
python-dotenv
pyyaml
```

**GitHubにプッシュ:**
```bash
git add requirements.txt
git commit -m "Fix: supabase package name"
git push
```

Streamlit Cloudが自動的に再デプロイします。

---

## エラー2: `ModuleNotFoundError: No module named 'xxx'`

### 原因
必要なパッケージが`requirements.txt`に記載されていない。

### 解決方法

**欠けているパッケージを追加:**
```txt
# 例: BeautifulSoup4が欠けている場合
beautifulsoup4
lxml
```

**GitHubにプッシュして再デプロイ。**

---

## エラー3: `FileNotFoundError: horse_racing_full_model.txt`

### 原因
モデルファイルがGitHubにプッシュされていない。

### 解決方法

#### 方法A: Git LFS使用（100MB以上）

```bash
# Git LFSをインストール
git lfs install

# 大きいファイルをLFS管理
git lfs track "*.txt"
git lfs track "*.pkl"
git add .gitattributes

# モデルファイルを追加
git add horse_racing_full_model.txt
git add feature_list.pkl
git commit -m "Add model files with Git LFS"
git push
```

#### 方法B: モデルを分割（代替案）

モデルが大きすぎる場合、学習パラメータを調整して小さくする。

---

## エラー4: 環境変数が読み込めない

### エラー
```python
KeyError: 'SUPABASE_URL'
```

### 原因
Streamlit CloudのSecretsが設定されていない。

### 解決方法

1. Streamlit Cloud → アプリ → 「Settings」
2. 「Secrets」タブ
3. 以下を追加：

```toml
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGci..."
```

4. 「Save」
5. アプリを再起動

**確認方法:**
```python
# app.pyに追加してデバッグ
import os
st.write(f"SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
```

---

## エラー5: `MemoryError` または `Killed`

### 原因
Streamlit Cloud Free tierのメモリ制限（1GB）を超えた。

### 解決方法

#### 方法1: シミュレーション回数を減らす

**app.py:**
```python
n_sim = st.slider(
    "シミュレーション回数",
    min_value=1000,
    max_value=10000,  # 50000 → 10000に変更
    value=5000,
    step=1000
)
```

#### 方法2: モデルサイズを削減

学習時に特徴量数を減らす。

#### 方法3: 有料プランにアップグレード

Streamlit Cloud Pro（4GB RAM）

---

## エラー6: Import エラー

### エラー
```python
ImportError: cannot import name 'xxx' from 'yyy'
```

### 原因
ファイルがGitHubにプッシュされていない。

### 解決方法

**必要なファイルを確認:**
```bash
git ls-files | grep ".py"
```

**欠けているファイルを追加:**
```bash
git add feature_engineering.py
git add add_*.py
git commit -m "Add missing Python files"
git push
```

---

## エラー7: Supabase接続エラー

### エラー
```
ConnectionError: Supabaseへの接続に失敗
```

### 原因
- URLまたはKeyが間違っている
- ネットワーク問題

### 解決方法

#### 1. URLとKeyを再確認

Supabase Dashboard → Settings → API

- **Project URL**: `https://xxxxx.supabase.co`
- **anon public key**: `eyJhbGci...`

#### 2. Streamlit Secretsを再設定

```toml
# ダブルクォートで囲む
SUPABASE_URL = "https://xxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

#### 3. Supabase RLSを確認

Supabase → Authentication → Policies

匿名アクセスが許可されているか確認。

---

## エラー8: 過去レースが取得できない

### 症状
```
✓ 過去レースが見つかった馬: 0頭
```

### 原因
- データがSupabaseにアップロードされていない
- テーブル名が間違っている

### 解決方法

#### 1. データを確認

Supabase → Table Editor → `race_results`

データが入っているか確認。

#### 2. データをアップロード

```python
from supabase_horse_history import SupabaseHorseHistoryDB
import os

os.environ["SUPABASE_URL"] = "..."
os.environ["SUPABASE_KEY"] = "..."

db = SupabaseHorseHistoryDB()
db.upload_directory_to_supabase("data")
```

#### 3. インデックスを確認

```sql
-- Supabase SQL Editor
SELECT indexname FROM pg_indexes WHERE tablename = 'race_results';
```

---

## デバッグ方法

### ログの確認

Streamlit Cloud → アプリ → 「Manage app」→ 「Logs」

エラーメッセージを確認。

### デバッグコードを追加

**app.py:**
```python
import streamlit as st
import os
import sys

# デバッグ情報を表示
with st.expander("🔍 デバッグ情報"):
    st.write("Python version:", sys.version)
    st.write("Working directory:", os.getcwd())
    st.write("Files:", os.listdir())
    st.write("SUPABASE_URL:", os.getenv("SUPABASE_URL", "NOT SET"))
    
    # モデルファイルの存在確認
    import pathlib
    model_path = pathlib.Path("horse_racing_full_model.txt")
    st.write(f"Model exists: {model_path.exists()}")
    if model_path.exists():
        st.write(f"Model size: {model_path.stat().st_size / 1024 / 1024:.2f} MB")
```

---

## チェックリスト

デプロイ前の確認：

- [ ] `requirements.txt`が正しい（`supabase`、`-e supabase`でない）
- [ ] モデルファイルがGitにプッシュされている
- [ ] Streamlit Secretsが設定されている
- [ ] Supabaseにデータがアップロードされている
- [ ] ローカルで動作確認済み

---

## 完全なrequirements.txt

```txt
streamlit
pandas
numpy
requests
beautifulsoup4
lxml
scikit-learn
joblib
lightgbm
supabase
python-dotenv
pyyaml
```

---

## 完全なStreamlit Secrets

```toml
# Streamlit Cloud → Settings → Secrets

SUPABASE_URL = "https://xxxxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6..."
```

**注意:**
- ダブルクォートで囲む
- 改行なし
- セミコロン不要

---

## よくある質問

### Q: デプロイに時間がかかる

**A:** 正常です。初回は5-10分かかります。

### Q: 再デプロイしたい

**A:** 
```bash
# 空コミットでプッシュ
git commit --allow-empty -m "Redeploy"
git push
```

または、Streamlit Cloud → Reboot app

### Q: ローカルでは動くがStreamlit Cloudでエラー

**A:** 
1. Python バージョンの違い
2. 環境変数の設定漏れ
3. ファイルパスの違い

**確認:**
```python
# 絶対パスではなく相対パスを使用
# ❌ /Users/xxx/project/model.txt
# ✅ model.txt
```

---

これで、ほとんどのStreamlit Cloudエラーが解決できます！🎊
