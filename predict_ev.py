import itertools
import lightgbm as lgb
import pandas as pd
from fetch_race import fetch_race_data
from fetch_odds import fetch_odds_all

EV_TH = 1.15

def predict_all_ev(netkeiba_url):
    df = fetch_race_data(netkeiba_url)

    # 簡易前処理
    df = df.fillna(0)

    features = [...]  # 学習時と同じ
    model = lgb.Booster(model_file="horse_racing_full_model.txt")

    df["win_prob"] = model.predict(df[features])
    df["place_prob"] = (df["win_prob"] * 2.5).clip(upper=1.0)

    odds = fetch_odds_all(netkeiba_url)

    results = {
        "win": [],
        "quinella": [],
        "trio": []
    }

    # --- 単勝 ---
    for _, r in df.iterrows():
        odd = odds["win"].get(r["horse_no"])
        if odd:
            EV = r["win_prob"] * odd
            if EV >= EV_TH:
                results["win"].append(
                    (r["horse_no"], EV, odd)
                )

    # --- 馬連 ---
    for a, b in itertools.combinations(df.itertuples(), 2):
        key = f"{a.horse_no}-{b.horse_no}"
        odd = odds["quinella"].get(key)
        if odd:
            p = a.win_prob * b.place_prob + b.win_prob * a.place_prob
            EV = p * odd
            if EV >= EV_TH:
                results["quinella"].append(
                    (key, EV, odd)
                )

    # --- 三連複 ---
    for a, b, c in itertools.combinations(df.itertuples(), 3):
        key = f"{a.horse_no}-{b.horse_no}-{c.horse_no}"
        odd = odds["trio"].get(key)
        if odd:
            p = a.place_prob * b.place_prob * c.place_prob
            EV = p * odd
            if EV >= EV_TH:
                results["trio"].append(
                    (key, EV, odd)
                )

    return results
