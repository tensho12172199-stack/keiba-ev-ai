import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import psycopg2

# ==============================
# 環境変数（GitHub Actions）
# ==============================
DB_URL = os.environ["DB_URL"]

# ==============================
# 保存フォルダ
# ==============================
SAVE_DIR = "race_csv"
os.makedirs(SAVE_DIR, exist_ok=True)

# ==============================
# DB接続
# ==============================
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# ==============================
# レース取得
# ==============================
def scrape_race(race_id):
    url = f"https://db.netkeiba.com/race/{race_id}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.encoding = "EUC-JP"

    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", class_="race_table_01")
    if table is None:
        return None

    rows = table.find_all("tr")[1:]
    results = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 15:
            continue

        horse_no = cols[2].text.strip()
        horse_name = cols[3].text.strip()
        rank_text = cols[0].text.strip()

        odds_text = cols[12].text.strip()
        odds = float(odds_text) if odds_text not in ["---", ""] else None

        rank = int(rank_text) if rank_text.isdigit() else None

        results.append((
            race_id,
            int(horse_no),
            horse_name,
            rank,
            odds
        ))

    return results

# ==============================
# DB保存（UPSERT）
# ==============================
def save_to_db(rows):
    cur.executemany("""
        insert into race_results (race_id, horse_no, horse_name, rank, odds)
        values (%s,%s,%s,%s,%s)
        on conflict (race_id, horse_no)
        do update set
            horse_name = excluded.horse_name,
            rank = excluded.rank,
            odds = excluded.odds
    """, rows)

    conn.commit()

# ==============================
# CSV保存
# ==============================
def save_csv(race_id, rows):
    df = pd.DataFrame(rows, columns=[
        "race_id", "horse_no", "horse_name", "rank", "odds"
    ])
    df.to_csv(f"{SAVE_DIR}/{race_id}.csv", index=False, encoding="utf_8_sig")

# ==============================
# メイン処理（自動更新対応）
# ==============================
def main():
    years = range(2025, 2027)
    courses = ["01","02","03","04","05","06","07","08","09","10"]

    for y in years:
        for c in courses:
            for kai in range(1,7):
                for day in range(1,13):
                    for r in range(1,13):

                        race_id = f"{y}{c}{kai:02}{day:02}{r:02}"
                        csv_path = f"{SAVE_DIR}/{race_id}.csv"

                        # すでにあればスキップ（自動更新）
                        if os.path.exists(csv_path):
                            continue

                        rows = scrape_race(race_id)

                        # レース存在しなければ次の日へ
                        if rows is None:
                            break

                        save_csv(race_id, rows)
                        save_to_db(rows)

                        print("saved:", race_id)
                        time.sleep(1)

if __name__ == "__main__":
    main()
