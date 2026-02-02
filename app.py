# app.py
import streamlit as st
import lightgbm as lgb
import re
import time

from fetch_race import fetch_race_data
from preprocess_predict import preprocess_for_prediction
from fetch_odds import fetch_win_odds

MODEL_PATH = "horse_racing_full_model.txt"

# =========================
# ページ設定
# =========================
st.set_page_config(
    page_title="競馬予想AI（EVベース）",
    layout="wide"
)

st.title("🏇 競馬予想AI（単勝EV）")
st.write("netkeiba の **出馬表URL** を貼るだけで予測します")

st.info(
    "📌 netkeibaの出馬表ページ（shutuba.html）を開き、"
    "URLをそのまま貼り付けてください"
)

# =========================
# URLチェック
# =========================
def is_valid_shutuba_url(url):
    pattern = r"^https://race\.netkeiba\.com/race/shutuba\.html\?race_id=\d+$"
    return re.match(pattern, url) is not None

# =========================
# セッション管理
# =========================
if "df_result" not in st.session_state:
    st.session_state.df_result = None
if "last_url" not in st.session_state:
    st.session_state.last_url = None

# =========================
# 入力
# =========================
url = st.text_input(
    "出馬表URL",
    placeholder="https://race.netkeiba.com/race/shutuba.html?race_id=..."
)

col1, col2 = st.columns(2)
run = col1.button("▶ 予想する")
rerun = col2.button("🔄 再予測（最新情報）")

# =========================
# 実行処理
# =========================
def run_prediction(target_url):
    df = fetch_race_data(target_url)
    X = preprocess_for_prediction(df)

    model = lgb.Booster(model_file=MODEL_PATH)
    df["win_prob"] = model.predict(X)

    odds = fetch_win_odds(target_url)
    df["win_odds"] = df["horse_no"].map(odds)

    df["win_EV"] = df["win_prob"] * df["win_odds"]
    return df.sort_values("win_EV", ascending=False)

# =========================
# 初回予測
# =========================
if run:
    if not url:
        st.warning("URLを入力してください")
        st.stop()

    if not is_valid_shutuba_url(url):
        st.error("出馬表URL（shutuba.html）を入力してください")
        st.stop()

    with st.spinner("予測中…"):
        st.session_state.df_result = run_prediction(url)
        st.session_state.last_url = url

# =========================
# 再予測
# =========================
if rerun:
    if st.session_state.last_url is None:
        st.warning("先に予測を実行してください")
        st.stop()

    with st.spinner("最新情報で再予測中…"):
        # 少し待つ（オッズ更新想定）
        time.sleep(1)
        st.session_state.df_result = run_prediction(
            st.session_state.last_url
        )

# =========================
# 結果表示
# =========================
df = st.session_state.df_result

if df is not None:
    st.subheader("📊 単勝EVランキング")

    display_df = df[
        ["horse_no", "horse_name", "win_prob", "win_odds", "win_EV"]
    ].copy()

    display_df["win_prob"] = display_df["win_prob"].round(3)
    display_df["win_odds"] = display_df["win_odds"].round(1)
    display_df["win_EV"] = display_df["win_EV"].round(2)

    st.dataframe(display_df, use_container_width=True)

    st.subheader("💰 買い判断")

    buy_df = display_df[display_df["win_EV"] >= 1.0]

    if len(buy_df) == 0:
        st.info("見送り（EV ≥ 1.0 の馬なし）")
    else:
        st.success("買い候補あり")
        st.dataframe(buy_df, use_container_width=True)
