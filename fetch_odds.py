# fetch_odds.py
import requests
import re

HEADERS = {"User-Agent": "Mozilla/5.0"}

def fetch_win_odds(shutuba_url):
    m = re.search(r"race_id=(\d+)", shutuba_url)
    if not m:
        return {}

    race_id = m.group(1)

    # netkeiba 内部API（単勝）
    api_url = (
        "https://race.netkeiba.com/api/api_get_jra_odds.html"
        f"?race_id={race_id}&type=win"
    )

    res = requests.get(api_url, headers=HEADERS, timeout=10)
    if res.status_code != 200:
        return {}

    data = res.json()

    odds = {}
    for row in data.get("odds", []):
        try:
            horse_no = int(row["horse_number"])
            odd = float(row["odds"])
            odds[horse_no] = odd
        except:
            continue

    return odds
