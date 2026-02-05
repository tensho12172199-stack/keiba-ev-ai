import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import psycopg2

DB_URL = os.environ["DB_URL"]

SAVE_DIR = "race_csv"
os.makedirs(SAVE_DIR, exist_ok=True)

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

def scrape_race(race_id):
    url = f"https://db.netkeiba.com/race/{race_id}"
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
    r.encoding = "EUC-JP"

    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text,"html.parser")
    table = soup.find("table",class_="race_table_01")
    if table is None:
        return None

    rows = table.find_all("tr")[1:]
    data = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 15:
            continue

        data.append((
            race_id,
            int(cols[2].text.strip()),
            cols[3].text.strip(),
            cols[6].text.strip(),
            cols[7].text.strip(),
            float(cols[12].text.strip()),
            int(cols[13].text.strip())
        ))

    return data

def save_to_db(rows):
    cur.executemany("""
    insert into race_results values (%s,%s,%s,%s,%s,%s,%s)
    on conflict (race_id, horse_no) do nothing
    """, rows)
    conn.commit()

def save_csv(race_id, rows):
    df = pd.DataFrame(rows, columns=[
        "race_id","horse_no","horse","jockey","time","odds","popularity"
    ])
    df.to_csv(f"{SAVE_DIR}/{race_id}.csv", index=False, encoding="utf_8_sig")

def main():
    years = range(2025, 2027)
    courses = ["01","02","03","04","05","06","07","08","09","10"]

    for y in years:
        for c in courses:
            for kai in range(1,7):
                for day in range(1,13):
                    for r in range(1,13):
                        race_id = f"{y}{c}{kai:02}{day:02}{r:02}"
                        path = f"{SAVE_DIR}/{race_id}.csv"

                        if os.path.exists(path):
                            continue

                        rows = scrape_race(race_id)
                        if rows is None:
                            break

                        save_csv(race_id, rows)
                        save_to_db(rows)

                        print("saved:", race_id)
                        time.sleep(1)

if __name__ == "__main__":
    main()
