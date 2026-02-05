import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import psycopg2
from datetime import datetime

DB_URL = os.environ["DB_URL"]

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# 取得済み
cur.execute("select distinct race_id from race_results")
done_ids = set(r[0] for r in cur.fetchall())

YEARS_BACK = 5
current_year = datetime.now().year
years = range(current_year - YEARS_BACK + 1, current_year + 1)

courses = ["01","02","03","04","05","06","07","08","09","10"]

def time_to_sec(t):
    if ":" not in t:
        return None
    m, s = t.split(":")
    return int(m)*60 + float(s)

def parse_weight(w):
    if "(" not in w:
        return None, None
    base = int(w.split("(")[0])
    diff = int(w.split("(")[1].replace(")",""))
    return base, diff

def scrape_race(race_id):
    url = f"https://db.netkeiba.com/race/{race_id}"
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"})
    r.encoding = "EUC-JP"

    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text,"html.parser")

    race_name = soup.find("h1").text.strip()
    info = soup.find("div", class_="data_intro").text

    distance = int(info.split("m")[0].split()[-1])
    course_type = "芝" if "芝" in info else "ダート"
    track_direction = "右" if "右" in info else "左"

    weather = soup.find("span", class_="weather").text
    track_condition = soup.find("span", class_="condition").text

    race_date = soup.find("p", class_="smalltxt").text.split()[0]

    table = soup.find("table", class_="race_table_01")
    rows = table.find_all("tr")[1:]

    results = []

    for row in rows:
        c = row.find_all("td")
        if len(c) < 18:
            continue

        time_sec = time_to_sec(c[7].text.strip())

        weight, diff = parse_weight(c[14].text.strip())

        odds_text = c[12].text.strip()
        odds = float(odds_text) if odds_text not in ["---",""] else None

        pop = int(c[13].text.strip()) if c[13].text.strip().isdigit() else None

        rank = int(c[0].text.strip()) if c[0].text.strip().isdigit() else None

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
            float(c[11].text.strip()),
            odds,
            pop,
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

def save(rows):
    cur.executemany("""
    insert into race_results values (
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s
    )
    on conflict (race_id, horse_no)
    do update set
        rank=excluded.rank,
        odds=excluded.odds,
        time=excluded.time
    """, rows)
    conn.commit()

def main():
    for y in years:
        for c in courses:
            for kai in range(1,7):
                for day in range(1,13):
                    for r in range(1,13):

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
