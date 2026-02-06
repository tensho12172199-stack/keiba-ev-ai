"""
競馬レース予測スクリプト（改善版）

改善点:
- レースIDの柔軟な抽出（様々なURL形式に対応）
- 複勝確率の計算
- 三連複（トリオ）確率の追加
- エラーハンドリングの強化
- Supabaseから過去レースデータを取得
"""

import numpy as np
import pandas as pd
import joblib
import re
import os
from pathlib import Path

from fetch_race import fetch_race_data
from preprocess_predict import preprocess_for_prediction
from plackett_luce import simulate_plackett_luce

# Supabase過去レースDB
try:
    from supabase_horse_history import SupabaseHorseHistoryDB, calculate_recent_features_supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️  supabase_horse_history.py が見つかりません")

MODEL_PATH = "horse_racing_full_model.txt"


def extract_race_id(url_or_id):
    """
    様々な形式のURLからレースIDを抽出
    
    対応形式:
    - https://race.netkeiba.com/race/shutuba.html?race_id=202406030811
    - https://race.netkeiba.com/race/result.html?race_id=202406030811
    - https://db.netkeiba.com/race/202406030811
    - 202406030811 (直接ID)
    
    Args:
        url_or_id: URL文字列またはレースID
    
    Returns:
        レースID (12桁の数字)
    """
    # すでにレースIDの場合
    if re.match(r'^\d{12}$', str(url_or_id)):
        return str(url_or_id)
    
    # URLからレースIDを抽出
    patterns = [
        r'race_id=(\d{12})',           # race_id=パラメータ
        r'/race/(\d{12})',              # /race/12345形式
        r'/shutuba\.html.*?(\d{12})',   # shutuba.htmlの後
        r'/result\.html.*?(\d{12})',    # result.htmlの後
        r'(\d{12})',                    # 12桁の数字
    ]
    
    for pattern in patterns:
        match = re.search(pattern, str(url_or_id))
        if match:
            return match.group(1)
    
    raise ValueError(
        f"レースIDを抽出できませんでした: {url_or_id}\n"
        f"有効な形式:\n"
        f"  - https://race.netkeiba.com/race/shutuba.html?race_id=202406030811\n"
        f"  - https://db.netkeiba.com/race/202406030811\n"
        f"  - 202406030811 (12桁の数字)"
    )


def softmax(x):
    """
    スコアを確率に変換（Softmax関数）
    """
    x = np.array(x, dtype=float)
    x = x - np.max(x)  # オーバーフロー対策
    exp_x = np.exp(x)
    return exp_x / exp_x.sum()


def calculate_quinella_place(place_probs, horse_ids, top_n=20):
    """
    複勝（馬連的中）確率を計算
    
    Args:
        place_probs: 各馬の3着以内確率
        horse_ids: 馬番リスト
        top_n: 上位何組を返すか
    
    Returns:
        DataFrame with columns: horse1, horse2, prob
    """
    results = []
    n = len(horse_ids)
    
    for i in range(n):
        for j in range(i + 1, n):
            # 両方が3着以内に入る確率（簡易計算）
            prob = place_probs[horse_ids[i]] * place_probs[horse_ids[j]]
            results.append({
                "馬番1": horse_ids[i],
                "馬番2": horse_ids[j],
                "確率": prob
            })
    
    df = pd.DataFrame(results)
    return df.sort_values("確率", ascending=False).head(top_n).reset_index(drop=True)


def predict_race(url_or_id, model_path=MODEL_PATH, n_sim=30000, use_supabase=True):
    """
    レース予測を実行
    
    Args:
        url_or_id: netkeibaのURLまたはレースID
        model_path: モデルファイルのパス
        n_sim: Plackett-Luceシミュレーション回数
        use_supabase: Supabaseから過去レースを取得するか
    
    Returns:
        df_race: 各馬の予測結果
        df_trifecta: 三連単TOP10
        df_trio: 三連複TOP10
        df_quinella_place: 複勝（馬連的中）TOP20
    """
    # ===== ① レースID抽出 =====
    race_id = extract_race_id(url_or_id)
    print(f"🏇 レースID: {race_id}")
    
    # ===== ② レースデータ取得 =====
    # URLを再構築（統一形式）
    standard_url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
    
    print(f"📊 データ取得中: {standard_url}")
    df_race = fetch_race_data(standard_url)
    
    if df_race.empty:
        raise ValueError("出走馬データが取得できませんでした")
    
    print(f"✓ 出走頭数: {len(df_race)}頭")
    
    # ===== ③ Supabaseから過去レースデータを取得 =====
    if use_supabase and SUPABASE_AVAILABLE:
        try:
            print("📚 Supabaseから過去レースデータを取得中...")
            
            # Supabase接続（環境変数から）
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_KEY")
            
            if supabase_url and supabase_key:
                supabase_db = SupabaseHorseHistoryDB(url=supabase_url, key=supabase_key)
                
                # レース日付を取得（リーク防止）
                race_date = None
                if 'race_date' in df_race.columns:
                    race_date = df_race['race_date'].iloc[0]
                
                # 過去レース特徴量を追加
                df_race = calculate_recent_features_supabase(
                    df_race, 
                    supabase_db, 
                    n_races=3
                )
                print("✓ 過去レース特徴量を追加しました")
            else:
                print("⚠️  環境変数 SUPABASE_URL と SUPABASE_KEY が設定されていません")
                print("   過去レースデータなしで続行します")
        except Exception as e:
            print(f"⚠️  Supabaseからの取得に失敗: {e}")
            print("   過去レースデータなしで続行します")
    
    # ===== ④ 前処理 =====
    print("🔧 特徴量を生成中...")
    X = preprocess_for_prediction(df_race)
    
    # ===== ⑤ モデルロード =====
    if not Path(model_path).exists():
        raise FileNotFoundError(f"モデルファイルが見つかりません: {model_path}")
    
    print(f"🤖 モデルをロード: {model_path}")
    model = joblib.load(model_path)
    
    # ===== ⑥ Rankerスコア予測 =====
    print("🎯 予測を実行中...")
    scores = model.predict(X)
    
    # ===== ⑦ スコア → 勝率変換 =====
    df_race["win_prob"] = softmax(scores)
    
    # ===== ⑧ Plackett–Luce シミュレーション =====
    print(f"🎲 {n_sim:,}回シミュレーション中...")
    horse_ids = df_race["horse_no"].tolist()
    win_probs = df_race["win_prob"].values
    
    win_sim, place_prob, trifecta_prob, trio_prob = simulate_plackett_luce(
        horse_ids=horse_ids,
        win_probs=win_probs,
        n_sim=n_sim
    )
    
    df_race["win_prob_sim"] = df_race["horse_no"].map(win_sim)
    df_race["place_prob"] = df_race["horse_no"].map(place_prob)
    
    # ===== ⑨ 三連単 TOP10 =====
    df_trifecta = (
        pd.DataFrame([
            {"1着": k[0], "2着": k[1], "3着": k[2], "確率": v}
            for k, v in trifecta_prob.items()
        ])
        .sort_values("確率", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    df_trifecta["確率"] = df_trifecta["確率"] * 100  # パーセント表示
    
    # ===== ⑩ 三連複 TOP10 =====
    df_trio = (
        pd.DataFrame([
            {"馬番1": k[0], "馬番2": k[1], "馬番3": k[2], "確率": v}
            for k, v in trio_prob.items()
        ])
        .sort_values("確率", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    df_trio["確率"] = df_trio["確率"] * 100  # パーセント表示
    
    # ===== ⑪ 複勝（馬連的中）TOP20 =====
    df_quinella_place = calculate_quinella_place(place_prob, horse_ids, top_n=20)
    df_quinella_place["確率"] = df_quinella_place["確率"] * 100  # パーセント表示
    
    print("✅ 予測完了！")
    
    return df_race, df_trifecta, df_trio, df_quinella_place


def display_predictions(df_race, df_trifecta, df_trio, df_quinella_place):
    """
    予測結果を見やすく表示
    """
    print("\n" + "="*80)
    print("🏇 単勝・複勝予測")
    print("="*80)
    
    display_df = df_race[[
        "horse_no",
        "horse_name",
        "win_prob_sim",
        "place_prob"
    ]].copy()
    
    display_df.columns = ["馬番", "馬名", "単勝確率", "複勝確率"]
    display_df["単勝確率"] = (display_df["単勝確率"] * 100).round(2)
    display_df["複勝確率"] = (display_df["複勝確率"] * 100).round(2)
    
    print(display_df.sort_values("単勝確率", ascending=False).to_string(index=False))
    
    print("\n" + "="*80)
    print("🎯 三連単 TOP10")
    print("="*80)
    print(df_trifecta.to_string(index=False))
    
    print("\n" + "="*80)
    print("🎲 三連複 TOP10")
    print("="*80)
    print(df_trio.to_string(index=False))
    
    print("\n" + "="*80)
    print("💰 複勝狙い（馬連的中）TOP20")
    print("="*80)
    print(df_quinella_place.head(10).to_string(index=False))


if __name__ == "__main__":
    # コマンドライン実行
    import sys
    
    if len(sys.argv) > 1:
        url_or_id = sys.argv[1]
    else:
        print("="*80)
        print("🏇 競馬レース予測")
        print("="*80)
        print("\nURLまたはレースIDを入力してください")
        print("例:")
        print("  - https://race.netkeiba.com/race/shutuba.html?race_id=202406030811")
        print("  - https://db.netkeiba.com/race/202406030811")
        print("  - 202406030811")
        print()
        url_or_id = input("入力: ").strip()
    
    try:
        df_race, df_trifecta, df_trio, df_quinella = predict_race(url_or_id)
        display_predictions(df_race, df_trifecta, df_trio, df_quinella)
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
