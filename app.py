"""
競馬予測Streamlitアプリ（修正版）

特徴量不一致エラーを解消し、正しく予測できるようにした版
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import re  # 新規追加
from datetime import datetime

# ページ設定
st.set_page_config(
    page_title="競馬予測システム",
    page_icon="🏇",
    layout="wide"
)

# CSS（見た目の改善）
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem;
    }
    .prediction-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }
    .top-prediction {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.markdown('<p class="main-header">🏇 競馬予測システム</p>', unsafe_allow_html=True)
st.markdown("---")

# サイドバー
with st.sidebar:
    st.header("⚙️ 設定")
    
    # モデルファイル確認
    st.subheader("📁 ファイル確認")
    
    from pathlib import Path
    
    files_status = {
        "モデルファイル": "horse_racing_full_model.txt",
        "特徴量リスト": "feature_list.pkl",
        "設定ファイル": "simple_weights.yaml",
        "予測スクリプト": "streamlit_predict.py"
    }
    
    all_ok = True
    for name, file in files_status.items():
        if Path(file).exists():
            st.success(f"✓ {name}")
        else:
            st.error(f"❌ {name}")
            all_ok = False
    
    if not all_ok:
        st.warning("⚠️ 必要なファイルが不足しています")
    
    st.markdown("---")
    
    # Supabase接続確認
    st.subheader("🔌 Supabase接続")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if supabase_url and supabase_key:
        st.success("✓ 接続済み")
    else:
        st.warning("⚠️ 未接続")
        st.caption("過去レースデータを使用しない場合は問題ありません")
    
    st.markdown("---")
    
    # シミュレーション設定
    st.subheader("🎲 シミュレーション設定")
    use_simulation = st.checkbox("Plackett-Luceシミュレーション", value=True)
    
    if use_simulation:
        n_simulations = st.slider(
            "シミュレーション回数",
            min_value=10000,
            max_value=100000,
            value=50000,
            step=10000
        )
    else:
        n_simulations = 0

# ユーティリティ関数（レースID抽出）
def extract_race_id_from_url(race_url):
    
    """
    netkeibaのURLからレースIDを抽出する
    """
    match = re.search(r"race_id=(\d+)", race_url)
    if match:
        return match.group(1)
    return None

# メインエリア
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📌 レース情報入力")
    race_url = st.text_input(
        "レースURLを入力してください",
        placeholder="https://race.netkeiba.com/race/shutuba.html?race_id=..."
    )

with col2:
    st.subheader("💡 使い方")
    st.caption("1. netkeibaのレースURLを入力")
    st.caption("2. 予測実行ボタンをクリック")
    st.caption("3. 結果を確認")

# 予測実行ボタン
predict_button = st.button("🔮 予測実行", type="primary", use_container_width=True)

if predict_button:
    if not race_url:
        st.error("❌ レースURLを入力してください")
    else:
        # レースIDを抽出
        race_id = extract_race_id_from_url(race_url)
        if not race_id:
            st.error("❌ 有効なレースURLを入力してください")
        elif not all_ok:
            st.error("❌ 必要なファイルが不足しています。サイドバーを確認してください。")
        else:
            try:
                st.success(f"✅ 抽出されたレースID: {race_id}")
                # ここでレースIDを用いてデータを取得する処理に変更します
                from fetch_race import fetch_race_data_by_id
                race_df = fetch_race_data_by_id(race_id)  # 修正箇所
                
                if race_df is None or len(race_df) == 0:
                    st.error("❌ レースデータの取得に失敗しました")
                    st.stop()

                st.success(f"✅ {len(race_df)}頭のデータを取得")
                
            except ImportError:
                st.error("❌ データ取得モジュールが見つかりません")
                st.stop()
            except Exception as e:
                st.error(f"❌ データ取得エラー: {e}")
                st.stop()