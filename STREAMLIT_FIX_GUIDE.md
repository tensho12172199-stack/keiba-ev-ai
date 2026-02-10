# 🎨 Streamlitアプリ修正ガイド

## 🎯 目的

特徴量不一致エラーを解消し、Streamlitアプリで正しく予測できるようにします。

---

## 📦 必要なファイル

```
streamlit_app/
├── app.py                          ← 修正が必要
├── streamlit_predict.py            ← 新規追加！
├── simple_weights.yaml             ← 学習時と同じもの
├── horse_racing_full_model.txt     ← 学習済みモデル
├── feature_list.pkl                ← 学習時の特徴量リスト
├── feature_metadata.json           ← メタデータ
├── supabase_horse_history.py
├── feature_engineering.py
├── add_passing_features.py
├── add_speed_features.py
└── その他の特徴量生成スクリプト
```

---

## 🔧 修正手順

### ステップ1: streamlit_predict.py を追加

**outputsフォルダからコピー:**
```powershell
copy outputs\streamlit_predict.py streamlit_app\
```

### ステップ2: app.py を修正

#### 修正前（エラーが出る）

```python
import predict_step2

# 予測実行
result = predict_step2.predict_race(race_df)
```

**問題:**
- 除外リストが学習時と違う
- 特徴量の数が合わない

#### 修正後（エラーなし）

```python
from streamlit_predict import predict_race_streamlit

# 予測実行
result = predict_race_streamlit(
    race_df,
    model_file="horse_racing_full_model.txt",
    feature_list_file="feature_list.pkl"
)
```

**改善点:**
- 学習時と同じ除外リスト使用
- 欠損特徴量を自動で0埋め
- エラー情報を画面に表示

---

## 📝 完全な app.py 修正例

### 最小限の修正

```python
import streamlit as st
import pandas as pd

# 予測関数をインポート（修正）
from streamlit_predict import predict_race_streamlit

# Supabase設定
from supabase_horse_history import SupabaseHorseHistoryDB, calculate_recent_features_supabase

st.title("🏇 競馬予測システム")

# レースURL入力
race_url = st.text_input("レースURLを入力")

if st.button("予測実行"):
    if not race_url:
        st.error("URLを入力してください")
    else:
        with st.spinner("データ取得中..."):
            # レースデータ取得
            race_df = fetch_race_data(race_url)
            
            # 前処理
            from feature_engineering import apply_all_features
            race_df = apply_all_features(race_df)
            
            # 通過順特徴量
            from add_passing_features import add_passing_features
            race_df = add_passing_features(race_df)
            
            # スピード特徴量
            from add_speed_features import add_speed_features
            race_df = add_speed_features(race_df)
            
            # 過去レース特徴量（Supabase）
            supabase_db = SupabaseHorseHistoryDB()
            race_df = calculate_recent_features_supabase(
                race_df, supabase_db, n_races=3
            )
        
        # 予測実行（修正版）
        result = predict_race_streamlit(
            race_df,
            model_file="horse_racing_full_model.txt",
            feature_list_file="feature_list.pkl"
        )
        
        if result is not None:
            # 結果表示
            st.success("✅ 予測完了！")
            
            st.subheader("🏆 予測結果 TOP3")
            
            top3 = result.head(3)
            
            for i, row in top3.iterrows():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{row['predicted_rank']}位: {row['horse_name']}**")
                
                with col2:
                    st.metric("予測スコア", f"{row['predicted_score']:.2f}")
                
                with col3:
                    if 'win_probability' in row:
                        st.metric("勝率", f"{row['win_probability']:.1%}")
            
            # 全結果を表示
            with st.expander("📊 全出走馬の予測"):
                display_cols = ['predicted_rank', 'horse_name', 'predicted_score']
                
                if 'win_probability' in result.columns:
                    display_cols.append('win_probability')
                
                st.dataframe(result[display_cols])
```

---

## 🎨 高度な修正例

### Plackett-Luce シミュレーション付き

```python
from streamlit_predict import predict_plackett_luce_streamlit

# 予測実行（確率計算付き）
result = predict_plackett_luce_streamlit(
    race_df,
    model_file="horse_racing_full_model.txt",
    feature_list_file="feature_list.pkl",
    n_simulations=50000  # シミュレーション回数
)

if result is not None:
    st.subheader("🏆 予測結果 TOP3")
    
    top3 = result.head(3)
    
    for i, row in top3.iterrows():
        st.markdown(f"### {row['predicted_rank']}位: {row['horse_name']}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("予測スコア", f"{row['predicted_score']:.2f}")
        
        with col2:
            st.metric("単勝率", f"{row['win_probability']:.1%}")
        
        with col3:
            st.metric("複勝率", f"{row['place_probability']:.1%}")
        
        with col4:
            st.metric("3着内率", f"{row['show_probability']:.1%}")
        
        st.markdown("---")
```

---

## 🔍 デバッグ方法

### エラーが出たら確認すべきこと

#### 1. ファイルの存在確認

```python
import streamlit as st
from pathlib import Path

st.subheader("📁 ファイル確認")

files_to_check = [
    "horse_racing_full_model.txt",
    "feature_list.pkl",
    "simple_weights.yaml",
    "streamlit_predict.py"
]

for file in files_to_check:
    if Path(file).exists():
        st.success(f"✓ {file}")
    else:
        st.error(f"❌ {file}")
```

#### 2. 特徴量の確認

```python
import joblib

st.subheader("🔍 特徴量情報")

# 学習時の特徴量
feature_list = joblib.load("feature_list.pkl")
st.write(f"学習時の特徴量数: {len(feature_list)}")

with st.expander("学習時の特徴量リスト"):
    for i, feat in enumerate(feature_list, 1):
        st.write(f"{i}. {feat}")

# 予測時の特徴量
from streamlit_predict import load_exclude_list_streamlit, select_features_streamlit

exclude_list = load_exclude_list_streamlit()
st.write(f"除外リスト数: {len(exclude_list)}")

if race_df is not None:
    available = select_features_streamlit(race_df, exclude_list)
    st.write(f"予測時の特徴量数: {len(available)}")
```

#### 3. 差分の確認

```python
import joblib
from streamlit_predict import select_features_streamlit, load_exclude_list_streamlit

st.subheader("⚖️ 特徴量の差分")

# 学習時
feature_list = joblib.load("feature_list.pkl")

# 予測時
exclude_list = load_exclude_list_streamlit()
available = select_features_streamlit(race_df, exclude_list)

# 差分
missing = set(feature_list) - set(race_df.columns)
extra = set(race_df.columns) - set(feature_list)

st.write(f"**欠損特徴量:** {len(missing)}個")
with st.expander("欠損リスト"):
    for feat in missing:
        st.write(f"- {feat}")

st.write(f"**余分な特徴量:** {len(extra)}個")
with st.expander("余分リスト"):
    for feat in extra:
        st.write(f"- {feat}")
```

---

## ⚠️ よくあるエラーと対処法

### エラー1: ModuleNotFoundError: No module named 'streamlit_predict'

**原因:**
streamlit_predict.py がない

**対処:**
```powershell
copy outputs\streamlit_predict.py streamlit_app\
```

### エラー2: FileNotFoundError: horse_racing_full_model.txt

**原因:**
モデルファイルがない

**対処:**
```powershell
# 学習を実行
python train_simple.py

# モデルをStreamlitフォルダにコピー
copy horse_racing_model.txt streamlit_app\horse_racing_full_model.txt
copy feature_list.pkl streamlit_app\
copy simple_weights.yaml streamlit_app\
```

### エラー3: 特徴量数が合わない

**原因:**
simple_weights.yaml が古い

**対処:**
```powershell
# 最新のsimple_weights.yamlをコピー
copy simple_weights.yaml streamlit_app\
```

### エラー4: 過去レース特徴量がない

**原因:**
calculate_recent_features_supabase を呼んでいない

**対処:**
```python
# app.py に追加
from supabase_horse_history import calculate_recent_features_supabase

race_df = calculate_recent_features_supabase(
    race_df, supabase_db, n_races=3
)
```

---

## 📊 動作確認

### 正常に動作している場合

```
✓ モデル読み込み完了（学習時の特徴量: 44個）
✅ 予測用データ準備完了（特徴量: 44個）
🔮 予測計算中...
✅ 予測完了！

🏆 予測結果 TOP3
1位: ドウデュース
   予測スコア: 8.52
   単勝率: 35.2%

2位: イクイノックス
   予測スコア: 7.89
   単勝率: 28.7%

3位: ソールオリエンス
   予測スコア: 7.34
   単勝率: 18.9%
```

---

## 🎯 チェックリスト

### デプロイ前

- [ ] streamlit_predict.py を配置
- [ ] simple_weights.yaml を配置
- [ ] horse_racing_full_model.txt を配置
- [ ] feature_list.pkl を配置
- [ ] app.py で streamlit_predict をインポート
- [ ] ローカルで動作確認

### デプロイ後

- [ ] Streamlit Cloud でファイルが見つかるか確認
- [ ] エラーログを確認
- [ ] 予測が実行できるか確認

---

これで、Streamlitアプリで正しく予測できます！🎊
