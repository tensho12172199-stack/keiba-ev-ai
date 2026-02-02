# predict_step2.py
import lightgbm as lgb
from fetch_race import fetch_race_data
from preprocess_predict import preprocess_for_prediction

MODEL_PATH = "horse_racing_full_model.txt"

def predict_race(netkeiba_url):
    # ① 出走表取得
    df_race = fetch_race_data(netkeiba_url)

    # ② 前処理（予測用）
    X_pred = preprocess_for_prediction(df_race)

    # ③ モデル読み込み
    model = lgb.Booster(model_file=MODEL_PATH)

    # ④ 予測
    df_race["win_prob"] = model.predict(X_pred)

    # 見やすく並び替え
    return df_race.sort_values("win_prob", ascending=False)


if __name__ == "__main__":
    url = input("netkeibaのURLを入力: ").strip()
    result = predict_race(url)

    print("\n=== 予測結果 ===")
    print(
        result[
            ["horse_no", "horse_name", "jockey", "win_prob"]
        ].to_string(index=False)
    )
