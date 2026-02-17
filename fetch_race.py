"""
レースデータ取得スクリプト（柔軟版）

- テーブルクラス名が変わっても動く
- 列の位置がズレても動く
- エンコーディングを自動判定
- リトライあり
- 失敗しても部分的に取得できたデータを返す
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import time


# ========== URL変換 ==========

def extract_race_id(raw):
    """
    あらゆる入力形式からrace_idを抽出する

    対応形式:
      - 202506050509                           (数字のみ)
      - race_id=202506050509                   (パラメータ形式)
      - https://race.netkeiba.com/...?race_id=202506050509
      - https://db.netkeiba.com/race/202506050509/
      - 2025/06/05/05/09 や 2025-06-05-05-09  (区切り文字あり)
    """
    raw = str(raw).strip()

    # 1. URLパラメータ形式 race_id=XXXX
    m = re.search(r'race_id=(\d{10,12})', raw)
    if m:
        return m.group(1)

    # 2. パスの末尾 /race/XXXXXXXXXX/
    m = re.search(r'/race/(\d{10,12})/?', raw)
    if m:
        return m.group(1)

    # 3. 連続する10〜12桁の数字
    m = re.search(r'\b(\d{10,12})\b', raw)
    if m:
        return m.group(1)

    # 4. 区切り文字を除去して10〜12桁になるか試みる
    digits_only = re.sub(r'[\s\-/.]', '', raw)
    m = re.search(r'(\d{10,12})', digits_only)
    if m:
        return m.group(1)

    return None


def build_urls(race_url):
    """
    入力からアクセス候補URLのリストを返す（優先順）
    """
    race_id = extract_race_id(race_url)

    if not race_id:
        return [race_url]

    return [
        f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}",
        f"https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}",
        f"https://db.netkeiba.com/race/{race_id}/",
    ]


# ========== HTTPアクセス ==========

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
    'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://race.netkeiba.com/',
}


def fetch_html(url, retries=3, wait=2):
    """
    HTMLを取得（リトライあり・エンコーディング自動判定）
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)

            if resp.status_code == 200:
                # エンコーディング自動判定
                for enc in ['EUC-JP', 'UTF-8', 'cp932']:
                    try:
                        resp.encoding = enc
                        text = resp.text
                        # 文字化けチェック（日本語が含まれているか）
                        if '馬' in text or 'レース' in text or 'race' in text.lower():
                            return text
                    except Exception:
                        continue
                # どれでもダメなら detected encoding を使う
                resp.encoding = resp.apparent_encoding
                return resp.text

            print(f"   ⚠️  HTTP {resp.status_code} (試行 {attempt}/{retries}): {url}")

        except requests.Timeout:
            print(f"   ⚠️  タイムアウト (試行 {attempt}/{retries}): {url}")
        except requests.RequestException as e:
            print(f"   ⚠️  通信エラー (試行 {attempt}/{retries}): {e}")

        if attempt < retries:
            time.sleep(wait)

    return None


# ========== テーブル検出 ==========

def find_race_table(soup):
    """
    出走表テーブルを柔軟に探す
    クラス名が変わっても動くように複数パターン試みる
    """
    # パターン1: 既知のクラス名
    for cls in ['Shutuba_Table', 'ShutubaTable', 'race_table_01', 'RaceTable']:
        t = soup.find('table', class_=cls)
        if t:
            return t

    # パターン2: 馬番・馬名っぽいthが含まれるtable
    for table in soup.find_all('table'):
        text = table.get_text()
        if ('馬名' in text or '馬番' in text) and len(table.find_all('tr')) > 5:
            return table

    # パターン3: 最もtrが多いtable
    tables = soup.find_all('table')
    if tables:
        return max(tables, key=lambda t: len(t.find_all('tr')))

    return None


# ========== レース情報取得 ==========

def parse_race_info(soup, html_text):
    """
    レース情報（距離・コース・馬場など）を取得
    見つからなければNoneを返す（エラーにしない）
    """
    info = {
        'race_name': None,
        'distance': None,
        'course_type': '芝',
        'track_direction': '右',
        'weather': None,
        'track_condition': None,
    }

    # レース名
    for tag, cls in [('h1', 'RaceName'), ('h2', 'RaceName'), ('div', 'RaceName')]:
        t = soup.find(tag, class_=cls)
        if t:
            info['race_name'] = t.get_text(strip=True)
            break

    # レース条件テキスト
    race_text = ''
    for cls in ['RaceData01', 'RaceData', 'racedata']:
        t = soup.find(class_=cls)
        if t:
            race_text = t.get_text()
            break

    if not race_text:
        race_text = html_text  # フォールバック: ページ全体から探す

    # 距離
    m = re.search(r'(\d{3,4})\s*m', race_text)
    if m:
        info['distance'] = int(m.group(1))

    # コース種別
    if 'ダート' in race_text:
        info['course_type'] = 'ダート'
    elif '障' in race_text:
        info['course_type'] = '障害'
    else:
        info['course_type'] = '芝'

    # トラック方向
    if '左' in race_text:
        info['track_direction'] = '左'
    elif '右' in race_text:
        info['track_direction'] = '右'

    # 天候
    for cls in ['Weather', 'weather']:
        t = soup.find(class_=cls)
        if t:
            info['weather'] = t.get_text(strip=True)
            break

    # 馬場状態
    for cls in ['BabaInfo', 'Baba', 'TrackCondition']:
        t = soup.find(class_=cls)
        if t:
            info['track_condition'] = t.get_text(strip=True)
            break

    return info


# ========== 列マッピング ==========

def detect_column_map(header_row):
    """
    ヘッダー行のテキストから各列が何番目かを動的に判定
    """
    col_map = {}
    cells = header_row.find_all(['th', 'td'])

    for i, cell in enumerate(cells):
        text = cell.get_text(strip=True)

        if re.search(r'枠', text):
            col_map['waku_no'] = i
        elif re.search(r'馬番|番号', text):
            col_map['horse_no'] = i
        elif re.search(r'馬名', text):
            col_map['horse_name'] = i
        elif re.search(r'性齢|性別', text):
            col_map['sex_age'] = i
        elif re.search(r'斤量|重量', text):
            col_map['weight_carrier'] = i
        elif re.search(r'騎手', text):
            col_map['jockey'] = i
        elif re.search(r'調教師|厩舎', text):
            col_map['trainer'] = i
        elif re.search(r'馬体重', text):
            col_map['horse_weight'] = i

    return col_map


def default_column_map():
    """
    ヘッダーが検出できなかった場合のデフォルト列マッピング
    netkeibaの標準的なカラム順
    """
    return {
        'waku_no': 0,
        'horse_no': 1,
        'horse_name': 3,
        'sex_age': 4,
        'weight_carrier': 5,
        'jockey': 6,
        'trainer': 7,
    }


def safe_get_col(cols, idx, default=''):
    """列が存在しない場合はデフォルト値を返す"""
    if idx is None or idx >= len(cols):
        return default
    return cols[idx].get_text(strip=True)


def safe_get_link_text(cols, idx, default=''):
    """列のリンクテキストを取得（なければセルのテキスト）"""
    if idx is None or idx >= len(cols):
        return default
    a = cols[idx].find('a')
    if a:
        return a.get_text(strip=True)
    return cols[idx].get_text(strip=True)


# ========== 馬データ取得 ==========

def parse_horses(table, race_info, race_id):
    """
    テーブルから全馬データを取得
    """
    rows = table.find_all('tr')
    if not rows:
        return []

    # ヘッダー行で列マッピングを判定
    col_map = None
    data_start = 1

    for i, row in enumerate(rows[:3]):
        ths = row.find_all('th')
        if len(ths) >= 4:
            col_map = detect_column_map(row)
            data_start = i + 1
            break

    if not col_map or len(col_map) < 3:
        col_map = default_column_map()

    horses = []

    for row in rows[data_start:]:
        cols = row.find_all('td')

        # 最低限の列数チェック（緩く：3列以上あれば試みる）
        if len(cols) < 3:
            continue

        try:
            # 枠番
            waku_text = safe_get_col(cols, col_map.get('waku_no'), '')
            waku_no = int(waku_text) if waku_text.isdigit() else None

            # 馬番
            horse_no_text = safe_get_col(cols, col_map.get('horse_no'), '')
            horse_no = int(horse_no_text) if horse_no_text.isdigit() else None

            # 馬番がなければスキップ
            if horse_no is None:
                continue

            # 馬名
            horse_name = safe_get_link_text(cols, col_map.get('horse_name'), '')
            if not horse_name:
                continue

            # 性齢
            sex_age = safe_get_col(cols, col_map.get('sex_age'), '')

            # 斤量
            wc_text = safe_get_col(cols, col_map.get('weight_carrier'), '')
            try:
                weight_carrier = float(wc_text)
            except ValueError:
                weight_carrier = None

            # 騎手
            jockey = safe_get_link_text(cols, col_map.get('jockey'), '')

            # 調教師
            trainer = safe_get_link_text(cols, col_map.get('trainer'), '')

            # 馬体重（任意）
            horse_weight = None
            hw_idx = col_map.get('horse_weight')
            if hw_idx is not None and hw_idx < len(cols):
                hw_text = cols[hw_idx].get_text(strip=True)
                m = re.search(r'(\d{3,4})', hw_text)
                if m:
                    horse_weight = int(m.group(1))

            horses.append({
                'race_id': race_id,
                'race_name': race_info['race_name'],
                'waku_no': waku_no,
                'horse_no': horse_no,
                'horse_name': horse_name,
                'sex_age': sex_age,
                'weight_carrier': weight_carrier,
                'jockey': jockey,
                'trainer': trainer,
                'horse_weight': horse_weight,
                'distance': race_info['distance'],
                'course_type': race_info['course_type'],
                'track_direction': race_info['track_direction'],
                'weather': race_info['weather'],
                'track_condition': race_info['track_condition'],
            })

        except Exception as e:
            # 1行の失敗は無視して続行
            continue

    return horses


# ========== メイン関数 ==========

def fetch_race_data(race_url):
    """
    レースデータを取得

    - result.html / shutuba.html どちらでも動く
    - 複数URLを試みる
    - テーブル構造が変わっても動く
    - エンコーディング自動判定
    - リトライあり
    """
    print(f"\n📥 レースデータ取得: {race_url}")

    race_id = extract_race_id(race_url)
    urls = build_urls(race_url)

    print(f"   試行するURL: {len(urls)}件")

    html_text = None
    used_url = None

    for url in urls:
        print(f"   🌐 アクセス中: {url}")
        html_text = fetch_html(url)
        if html_text:
            used_url = url
            print(f"   ✅ 取得成功")
            break
        print(f"   ❌ 取得失敗、次を試みます")

    if not html_text:
        print("❌ すべてのURLで取得失敗")
        return None

    soup = BeautifulSoup(html_text, 'html.parser')

    # テーブル検出
    table = find_race_table(soup)
    if not table:
        print("❌ 出走表テーブルが見つかりません")
        return None

    # レース情報取得
    race_info = parse_race_info(soup, html_text)
    print(f"   レース名: {race_info['race_name'] or '不明'}")
    print(f"   距離: {race_info['distance']}m / {race_info['course_type']} {race_info['track_direction']}")

    # 馬データ取得
    horses = parse_horses(table, race_info, race_id)

    if not horses:
        print("❌ 馬データを取得できませんでした")
        return None

    df = pd.DataFrame(horses)
    print(f"✅ {len(df)}頭のデータを取得")

    return df


if __name__ == "__main__":
    # テスト
    test_urls = [
        "https://race.netkeiba.com/race/shutuba.html?race_id=202506050509",
        "https://race.netkeiba.com/race/result.html?race_id=202506050509",
    ]

    for url in test_urls:
        print(f"\n{'='*60}")
        df = fetch_race_data(url)
        if df is not None:
            print(df[['horse_no', 'horse_name', 'sex_age', 'weight_carrier']].head())
