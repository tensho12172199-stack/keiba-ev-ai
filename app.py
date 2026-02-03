"""
競馬予測 Streamlit Web アプリ

機能:
- レースURL/IDの柔軟な入力
- 単勝・複勝・三連単・三連複の予測
- 見やすい表示とダウンロード機能
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# カスタムモジュール
from predict_step2 import predict_race, extract_race_id

# ページ設定
st.set_page_config(
    page_title="🏇 競馬予測アプリ",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# スタイル
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .top-pick {
        background-color: #ffd700;
        padding: 0.5rem;
        border-radius: 0.3rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # ヘッダー
    st.markdown('<h1 class="main-header">🏇 競馬レース予測</h1>', unsafe_allow_html=True)
    
    # サイドバー
    with st.sidebar:
        st.header("⚙️ 設定")
        
        # シミュレーション回数
        n_sim = st.slider(
            "シミュレーション回数",
            min_value=1000,
            max_value=50000,
            value=30000,
            step=1000,
            help="回数が多いほど精度が上がりますが、時間がかかります"
        )
        
        st.markdown("---")
        
        # 使い方
        st.header("📖 使い方")
        st.markdown("""
        1. **レースURLまたはIDを入力**
           - netkeibaのURL
           - 12桁のレースID
        
        2. **予測実行ボタンをクリック**
        
        3. **結果を確認**
           - 単勝・複勝確率
           - 三連単・三連複の組み合わせ
        
        **対応URL形式:**
        - `https://race.netkeiba.com/race/shutuba.html?race_id=202406030811`
        - `https://db.netkeiba.com/race/202406030811`
        - `202406030811` (直接ID)
        """)
        
        st.markdown("---")
        st.info("💡 結果は参考値です。実際の投票は自己責任で行ってください。")
    
    # メインエリア
    col1, col2 = st.columns([3, 1])
    
    with col1:
        url_input = st.text_input(
            "🔗 レースURLまたはID",
            placeholder="https://race.netkeiba.com/race/shutuba.html?race_id=202406030811",
            help="netkeibaのレースURLまたは12桁のレースIDを入力"
        )
    
    with col2:
        st.write("")  # スペーサー
        st.write("")  # スペーサー
        predict_button = st.button("🎯 予測実行", type="primary", use_container_width=True)
    
    # 予測実行
    if predict_button and url_input:
        try:
            # レースID抽出チェック
            with st.spinner("レースIDを確認中..."):
                race_id = extract_race_id(url_input)
                st.success(f"✅ レースID: {race_id}")
            
            # 予測実行
            with st.spinner(f"予測を実行中... ({n_sim:,}回シミュレーション)"):
                df_race, df_trifecta, df_trio, df_quinella = predict_race(
                    url_input,
                    n_sim=n_sim
                )
            
            st.success("✅ 予測完了！")
            
            # 結果表示
            display_results(df_race, df_trifecta, df_trio, df_quinella)
            
        except ValueError as e:
            st.error(f"❌ エラー: {e}")
        except FileNotFoundError as e:
            st.error(f"❌ モデルファイルが見つかりません: {e}")
            st.info("モデルファイル `horse_racing_full_model.txt` をアップロードしてください")
        except Exception as e:
            st.error(f"❌ 予期しないエラー: {e}")
            with st.expander("詳細なエラー情報"):
                st.exception(e)
    
    elif predict_button:
        st.warning("⚠️ レースURLまたはIDを入力してください")
    
    # フッター
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: gray;'>"
        "Powered by LightGBM Ranker & Plackett-Luce Model"
        "</p>",
        unsafe_allow_html=True
    )


def display_results(df_race, df_trifecta, df_trio, df_quinella):
    """
    予測結果を表示
    """
    # タブで分割
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 単勝・複勝",
        "🎯 三連単",
        "🎲 三連複",
        "💰 複勝狙い"
    ])
    
    # タブ1: 単勝・複勝
    with tab1:
        st.header("🏆 単勝・複勝予測")
        
        # データ整形
        display_df = df_race[[
            "horse_no",
            "horse_name",
            "win_prob_sim",
            "place_prob"
        ]].copy()
        
        display_df["win_prob_pct"] = (display_df["win_prob_sim"] * 100).round(2)
        display_df["place_prob_pct"] = (display_df["place_prob"] * 100).round(2)
        
        display_df = display_df.sort_values("win_prob_sim", ascending=False).reset_index(drop=True)
        
        # TOP3をハイライト
        col1, col2, col3 = st.columns(3)
        
        with col1:
            top1 = display_df.iloc[0]
            st.metric(
                label=f"🥇 1番人気",
                value=f"{top1['horse_no']}番 {top1['horse_name']}",
                delta=f"{top1['win_prob_pct']:.1f}%"
            )
        
        with col2:
            top2 = display_df.iloc[1]
            st.metric(
                label=f"🥈 2番人気",
                value=f"{top2['horse_no']}番 {top2['horse_name']}",
                delta=f"{top2['win_prob_pct']:.1f}%"
            )
        
        with col3:
            top3 = display_df.iloc[2]
            st.metric(
                label=f"🥉 3番人気",
                value=f"{top3['horse_no']}番 {top3['horse_name']}",
                delta=f"{top3['win_prob_pct']:.1f}%"
            )
        
        st.markdown("---")
        
        # 全馬表示
        st.subheader("全出走馬")
        
        final_df = display_df[[
            "horse_no",
            "horse_name",
            "win_prob_pct",
            "place_prob_pct"
        ]].copy()
        final_df.columns = ["馬番", "馬名", "単勝確率(%)", "複勝確率(%)"]
        
        # スタイル付きで表示
        st.dataframe(
            final_df,
            hide_index=True,
            use_container_width=True,
            height=400
        )
        
        # ダウンロードボタン
        csv = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name="単勝複勝予測.csv",
            mime="text/csv"
        )
    
    # タブ2: 三連単
    with tab2:
        st.header("🎯 三連単 TOP10")
        st.caption("1着→2着→3着の順番通り")
        
        display_trifecta = df_trifecta.copy()
        display_trifecta["確率"] = display_trifecta["確率"].round(2)
        
        # 組み合わせ表示
        for idx, row in display_trifecta.iterrows():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(
                    f"**{idx+1}位:** "
                    f"{row['1着']}番 → {row['2着']}番 → {row['3着']}番"
                )
            
            with col2:
                st.markdown(f"**{row['確率']:.2f}%**")
        
        # ダウンロード
        csv = display_trifecta.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name="三連単TOP10.csv",
            mime="text/csv"
        )
    
    # タブ3: 三連複
    with tab3:
        st.header("🎲 三連複 TOP10")
        st.caption("1-2-3着（順不同）")
        
        display_trio = df_trio.copy()
        display_trio["確率"] = display_trio["確率"].round(2)
        
        # 組み合わせ表示
        for idx, row in display_trio.iterrows():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(
                    f"**{idx+1}位:** "
                    f"{row['馬番1']}番 - {row['馬番2']}番 - {row['馬番3']}番"
                )
            
            with col2:
                st.markdown(f"**{row['確率']:.2f}%**")
        
        # ダウンロード
        csv = display_trio.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name="三連複TOP10.csv",
            mime="text/csv"
        )
    
    # タブ4: 複勝狙い
    with tab4:
        st.header("💰 複勝狙い（馬連的中）TOP20")
        st.caption("両方が3着以内に入る可能性が高い組み合わせ")
        
        display_quinella = df_quinella.copy()
        display_quinella["確率"] = display_quinella["確率"].round(2)
        
        # 組み合わせ表示
        for idx, row in display_quinella.head(10).iterrows():
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(
                    f"**{idx+1}位:** "
                    f"{row['馬番1']}番 - {row['馬番2']}番"
                )
            
            with col2:
                st.markdown(f"**{row['確率']:.2f}%**")
        
        # 全データをテーブルで
        st.markdown("---")
        st.subheader("TOP20 一覧")
        st.dataframe(
            display_quinella,
            hide_index=True,
            use_container_width=True,
            height=300
        )
        
        # ダウンロード
        csv = display_quinella.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name="複勝狙いTOP20.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()
