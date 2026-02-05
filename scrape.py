import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import psycopg2
from datetime import datetime
import re

# ==============================
# DB接続
# ==============================
DB_URL = os.environ["DB_URL"]
conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# ==============================
# 取得済みrace_id
# ==============================
cur.execute("select distinct race_id from race_results")
done_ids = set(r[0] for r in cur.fetchall())

# ==============================
# 取得期間（任意）
# ==============================
YEARS_BACK = 5

current_year = datetime.now().year
years = range(current_year - YEARS_BACK + 1, current_year + 1)

courses = ["01","02","03","04","05","06","07","08","09","10"]

# ==============================
# ユーティリティ
# ==============================
def time_to_sec(t):
    if ":" not in t:
        return None
    m, s = t.split(":")
    return int(m) * 60 + float(s)

def parse_weight(w):
    if "(" not in w:
        return None
    return int(w.split("(")[0])

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

    race_name = soup.find("h1").text.strip()
    info = soup.find("div", class_="data_intro").text

    dist_match = re.search(r'(\d+)m', info)
    distance = int(dist_match.group(1)) if dist_match else None

    course_type = "芝" if "芝" in info else "ダート"
    track_direction = "右" if "右" in info else "左"

    weather = soup.find("span", class_="weather").text
    track_condition = soup.find("span", class_="condition").text

    race_date = soup.find("p", class_="smalltxt").text.split()[0]

    rows = table.find_all("tr")[1:]
    results = []

    for row in rows:
        c = row.find_all("td")
        if len(c) < 18:
            continue

        rank = int(c[0].text.strip()) if c[0].text.strip().isdigit() else None

        odds_text = c[12].text.strip()
        odds = float(odds_text) if odds_text not in ["---", ""] else None

        pop_text = c[13].text.strip()
        popularity = int(pop_text) if pop_text.isdigit() else None

        time_sec = time_to_sec(c[7].text.strip())
        weight = parse_weight(c[14].text.strip())

        last3f_text = c[11].text.strip()
        last_3f = float(last3f_text) if last3f_text not in ["", "---"] else None

        results.append((
            race_id,
            race_name,
            rank,
            int(c[1].text.strip()),
            int(c[2].text.strip()),
            c[3].text.strip(),
            c[4].text.strip(),
            float(c[5].text.strip()),
            c[6].text.strip(),
            time_sec,
            c[8].text.strip(),
            c[10].text.strip(),
            last_3f,
            odds,
            popularity,
            weight,
            info,
            race_date,
            distance,
            course_type,
            track_direction,
            weather,
            track_condition
        ))

    return results

# ==============================
# 保存（UPSERT）
# ==============================
def save(rows):
    cur.executemany("""
    insert into race_results values (
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s
    )
    on conflict (race_id, horse_no)
    do update set
        rank = excluded.rank,
        odds = excluded.odds,
        time = excluded.time
    """, rows)

    conn.commit()

# ==============================
# メイン
# ==============================
def main():
    for y in years:
        for c in courses:
            for kai in range(1, 7):
                for day in range(1, 13):
                    for r in range(1, 13):

                        race_id = f"{y}{c}{kai:02}{day:02}{r:02}"

                        if race_id in done_ids:
                            continue

                        rows = scrape_race(race_id)

                        if rows is None:
                            break

                        save(rows)
                        done_ids.add(race_id)

                        print("saved:", race_id)
                        time.sleep(1)

if __name__ == "__main__":
    main()
