# predict_step3.py
import lightgbm as lgb
from fetch_race import fetch_race_data
from preprocess_predict import preprocess_for_prediction
from fetch_odds import fetch_win_odds

MODEL_PATH = "horse_racing_full_model.txt"

def predict_with_ev(url):
    # 出走表
    df = fetch_race_data(url)

    # 予測用前処理
    X = preprocess_for_prediction(df)

    # モデル読み込み
    model = lgb.Booster(model_file=MODEL_PATH)

    # 勝率予測
    df["win_prob"] = model.predict(X)

    # 単勝オッズ取得
    odds = fetch_win_odds(url)
    df["win_odds"] = df["horse_no"].map(odds)

    # EV計算
    df["win_EV"] = df["win_prob"] * df["win_odds"]

    # 見やすく
    return df.sort_values("win_EV", ascending=False)


if __name__ == "__main__":
    url = input("netkeiba 出馬表URL: ").strip()
    df = predict_with_ev(url)

    print("\n=== 単勝EV 上位 ===")
    print(
        df[
            ["horse_no", "horse_name", "win_prob", "win_odds", "win_EV"]
        ].to_string(index=False)
    )
