"""
競馬予測Streamlitアプリ（修正版）

特徴量不一致エラーを解消し、正しく予測できるようにした版
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
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
    
    elif not all_ok:
        st.error("❌ 必要なファイルが不足しています。サイドバーを確認してください。")
    
    else:
        try:
            # プログレスバー
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1. レースデータ取得
            status_text.text("📥 レースデータ取得中...")
            progress_bar.progress(10)
            
            try:
                from fetch_race import fetch_race_data
                race_df = fetch_race_data(race_url)
                
                if race_df is None or len(race_df) == 0:
                    st.error("❌ レースデータの取得に失敗しました")
                    st.stop()
                
                st.success(f"✅ {len(race_df)}頭のデータを取得")
                
            except ImportError:
                st.error("❌ fetch_race.py が見つかりません")
                st.stop()
            except Exception as e:
                st.error(f"❌ データ取得エラー: {e}")
                st.stop()
            
            progress_bar.progress(30)
            
            # 2. 前処理
            status_text.text("🔧 前処理実行中...")
            
            try:
                from feature_engineering import apply_all_features
                from add_passing_features import add_passing_features
                from add_speed_features import add_speed_features
                
                race_df = apply_all_features(race_df)
                
                if 'passing' in race_df.columns:
                    race_df = add_passing_features(race_df)
                
                if 'distance' in race_df.columns and 'time_sec' in race_df.columns:
                    race_df = add_speed_features(race_df)
                
            except ImportError as e:
                st.error(f"❌ 特徴量生成モジュールが見つかりません: {e}")
                st.stop()
            except Exception as e:
                st.warning(f"⚠️ 前処理の一部でエラー: {e}")
            
            progress_bar.progress(50)
            
            # 3. 過去レース特徴量
            status_text.text("🔍 過去レースデータ取得中...")
            
            if supabase_url and supabase_key:
                try:
                    from supabase_horse_history import (
                        SupabaseHorseHistoryDB,
                        calculate_recent_features_supabase
                    )
                    
                    supabase_db = SupabaseHorseHistoryDB(
                        url=supabase_url,
                        key=supabase_key
                    )
                    
                    race_df = calculate_recent_features_supabase(
                        race_df,
                        supabase_db,
                        n_races=3
                    )
                    
                    st.success("✅ 過去レースデータを取得")
                    
                except ImportError:
                    st.warning("⚠️ supabase_horse_history.py が見つかりません")
                except Exception as e:
                    st.warning(f"⚠️ 過去レースデータ取得エラー: {e}")
            else:
                st.info("ℹ️ Supabaseが未設定のため、過去レースデータなしで予測します")
            
            progress_bar.progress(70)
            
            # 4. 予測実行
            status_text.text("🔮 予測計算中...")
            
            try:
                from streamlit_predict import (
                    predict_race_streamlit,
                    predict_plackett_luce_streamlit
                )
                
                if use_simulation:
                    # シミュレーション付き
                    result = predict_plackett_luce_streamlit(
                        race_df,
                        model_file="horse_racing_full_model.txt",
                        feature_list_file="feature_list.pkl",
                        n_simulations=n_simulations
                    )
                else:
                    # 基本予測のみ
                    result = predict_race_streamlit(
                        race_df,
                        model_file="horse_racing_full_model.txt",
                        feature_list_file="feature_list.pkl"
                    )
                
                if result is None:
                    st.error("❌ 予測に失敗しました")
                    st.stop()
                
            except ImportError:
                st.error("❌ streamlit_predict.py が見つかりません")
                st.stop()
            except Exception as e:
                st.error(f"❌ 予測エラー: {e}")
                import traceback
                with st.expander("詳細なエラー情報"):
                    st.code(traceback.format_exc())
                st.stop()
            
            progress_bar.progress(100)
            status_text.text("✅ 予測完了！")
            
            # プログレスバーを消す
            progress_bar.empty()
            status_text.empty()
            
            # ==========================================
            # 結果表示
            # ==========================================
            
            st.markdown("---")
            st.markdown("## 🏆 予測結果")
            
            # TOP3表示
            top3 = result.head(3)
            
            for idx, (i, row) in enumerate(top3.iterrows(), 1):
                if idx == 1:
                    # 1位は特別表示
                    st.markdown(f"""
                    <div class="top-prediction">
                        <h2>🥇 1位予想: {row['horse_name']}</h2>
                        <p style="font-size: 1.5rem; margin: 0.5rem 0;">
                            予測スコア: {row['predicted_score']:.2f}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if use_simulation and 'win_probability' in row:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("🎯 単勝確率", f"{row['win_probability']:.1%}")
                        
                        with col2:
                            st.metric("🎯 複勝確率", f"{row['place_probability']:.1%}")
                        
                        with col3:
                            st.metric("🎯 3着内確率", f"{row['show_probability']:.1%}")
                
                else:
                    # 2位・3位
                    medal = "🥈" if idx == 2 else "🥉"
                    
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"### {medal} {idx}位予想: {row['horse_name']}")
                    
                    with col2:
                        st.metric("予測スコア", f"{row['predicted_score']:.2f}")
                    
                    if use_simulation and 'win_probability' in row:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("単勝確率", f"{row['win_probability']:.1%}")
                        
                        with col2:
                            st.metric("複勝確率", f"{row['place_probability']:.1%}")
                        
                        with col3:
                            st.metric("3着内確率", f"{row['show_probability']:.1%}")
                
                st.markdown("---")
            
            # 全出走馬の結果
            with st.expander("📊 全出走馬の予測結果"):
                # 表示用のDataFrameを作成
                display_cols = ['predicted_rank', 'horse_name', 'predicted_score']
                
                if 'age' in result.columns:
                    display_cols.append('age')
                
                if 'weight_carrier' in result.columns:
                    display_cols.append('weight_carrier')
                
                if use_simulation and 'win_probability' in result.columns:
                    display_cols.extend(['win_probability', 'place_probability'])
                
                # 存在するカラムのみ選択
                display_cols = [c for c in display_cols if c in result.columns]
                
                display_df = result[display_cols].copy()
                
                # カラム名を日本語に
                rename_dict = {
                    'predicted_rank': '予測順位',
                    'horse_name': '馬名',
                    'predicted_score': '予測スコア',
                    'age': '年齢',
                    'weight_carrier': '斤量',
                    'win_probability': '単勝確率',
                    'place_probability': '複勝確率'
                }
                
                display_df = display_df.rename(columns=rename_dict)
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )
            
            # 買い目推奨
            if use_simulation and 'win_probability' in result.columns:
                with st.expander("💰 買い目推奨"):
                    st.subheader("単勝")
                    
                    top_win = result.nlargest(1, 'win_probability').iloc[0]
                    st.write(f"**推奨:** {top_win['horse_name']} (確率: {top_win['win_probability']:.1%})")
                    
                    st.subheader("複勝")
                    
                    top_place = result.nlargest(3, 'place_probability')
                    st.write("**推奨:**")
                    for i, row in top_place.iterrows():
                        st.write(f"- {row['horse_name']} (確率: {row['place_probability']:.1%})")
                    
                    st.subheader("馬連・ワイド")
                    
                    top2 = result.head(2)
                    if len(top2) >= 2:
                        st.write(f"**推奨:** {top2.iloc[0]['horse_name']} - {top2.iloc[1]['horse_name']}")
        
        except Exception as e:
            st.error(f"❌ 予期しないエラー: {e}")
            
            with st.expander("詳細なエラー情報"):
                import traceback
                st.code(traceback.format_exc())

# フッター
st.markdown("---")
st.caption("🏇 競馬予測システム | Powered by LightGBM & Streamlit")
