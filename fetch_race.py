# fetch_race.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://race.netkeiba.com/"
}

def safe_int(x):
    try:
        return int(x)
    except:
        return None

def safe_float(x):
    try:
        return float(x)
    except:
        return None


def fetch_race_data(netkeiba_url):
    # =========================
    # HTML取得（文字化け対策）
    # =========================
    res = requests.get(netkeiba_url, headers=HEADERS, timeout=10)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "lxml")

    # =========================
    # レース条件取得
    # =========================
    race_info = soup.select_one(".RaceData01")
    race_text = race_info.text if race_info else ""

    surface = "芝" if "芝" in race_text else "ダ"

    m = re.search(r"(\d+)m", race_text)
    distance = int(m.group(1)) if m else 0

    if "右" in race_text:
        rotation = "右"
    elif "左" in race_text:
        rotation = "左"
    else:
        rotation = "直"

    race_id_match = re.search(r"race_id=(\d+)", netkeiba_url)
    race_id = race_id_match.group(1) if race_id_match else ""
    venue = race_id[4:6] if len(race_id) >= 6 else "00"

    # =========================
    # 出走表テーブル取得
    # =========================
    table = soup.select_one(".Shutuba_Table")
    if table is None:
        raise ValueError("出走表テーブルが取得できません（URL確認）")

    rows = table.select("tr")
    data = []

    for r in rows:
        tds = r.find_all("td")
        if len(tds) < 7:
            continue

        bracket = safe_int(tds[0].text.strip())
        horse_no = safe_int(tds[1].text.strip())

        # 取消・除外・空行を除外
        if bracket is None or horse_no is None:
            continue

        horse_name = tds[3].text.strip()

        sex_age = tds[4].text.strip()
        sex = sex_age[0] if len(sex_age) >= 1 else "不明"
        age = safe_int(sex_age[1:]) if len(sex_age) >= 2 else 0

        weight_carrier = safe_float(tds[5].text.strip()) or 0
        jockey = tds[6].text.strip()

        data.append({
            "bracket": bracket,
            "horse_no": horse_no,
            "horse_name": horse_name,
            "sex": sex,
            "age": age,
            "weight_carrier": weight_carrier,
            "jockey": jockey,
            "venue": venue,
            "surface": surface,
            "distance": distance,
            "rotation": rotation,
        })

    if len(data) == 0:
        raise ValueError(
            "有効な出走馬データが0件です。"
            "発走前か、URLがshutuba.htmlか確認してください。"
        )

    return pd.DataFrame(data)
