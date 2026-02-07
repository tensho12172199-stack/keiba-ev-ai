"""
競馬レース結果スクレイピングスクリプト（改善版）

機能:
- 最新の結果が出ているレースまで自動取得
- スクレイピング済みのレースは自動スキップ
- エラーハンドリング強化
- 進捗状況の詳細表示
- 修正: 全レースを確実に取得できるようループ構造を改善
"""

import requests
from bs4 import BeautifulSoup
import time
import os
import psycopg2
from datetime import datetime, timedelta
import re
from typing import List, Tuple, Optional, Set

# =========================
# DB設定
# =========================
DB_URL = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")

if not DB_URL:
    raise ValueError("環境変数 DB_URL または DATABASE_URL を設定してください")

def get_conn():
    """DB接続を取得"""
    return psycopg2.connect(
        DB_URL,
        sslmode="require",
        connect_timeout=10
    )

# =========================
# 取得済みrace_idを管理
# =========================
def load_done_ids() -> Set[str]:
    """取得済みのレースIDをDBから読み込み"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT race_id FROM race_results")
        ids = set(r[0] for r in cur.fetchall())
        cur.close()
        conn.close()
        print(f"✓ 取得済みレース数: {len(ids)}")
        return ids
    except Exception as e:
        print(f"⚠️  取得済みID読み込みエラー: {e}")
        return set()

# =========================
# 取得期間の設定
# =========================
def get_date_range() -> Tuple[int, int]:
    """
    取得する年の範囲を決定
    
    Returns:
        (開始年, 終了年)
    """
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # 今年のレースが始まっているかチェック
    # 1月なら前年末まで、それ以降なら今年も含む
    if current_month == 1:
        end_year = current_year - 1
    else:
        end_year = current_year
    
    # 過去5年分を取得
    start_year = end_year - 4
    
    return start_year, end_year

# =========================
# ヘルパー関数
# =========================
def safe(tag) -> Optional[str]:
    """タグからテキストを安全に取得"""
    return tag.text.strip() if tag else None

def time_to_sec(t: str) -> Optional[float]:
    """タイム文字列を秒数に変換"""
    if not t or ":" not in t:
        return None
    try:
        parts = t.split(":")
        if len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
    except:
        pass
    return None

def parse_weight(w: str) -> Optional[int]:
    """馬体重文字列をパース"""
    if not w or "(" not in w:
        return None
    try:
        return int(w.split("(")[0])
    except:
        return None

def parse_date(text: str) -> Optional[str]:
    """日付文字列をYYYY-MM-DD形式に変換"""
    if not text:
        return None
    # 2024年12月25日 形式
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return None

# =========================
# レース結果を取得
# =========================
def scrape_race(race_id: str) -> Optional[List[Tuple]]:
    """
    指定されたレースIDの結果を取得
    
    Args:
        race_id: レースID (例: "202406030811")
    
    Returns:
        レース結果のリスト、または None（レースが存在しない場合）
    """
    url = f"https://db.netkeiba.com/race/{race_id}"
    
    try:
        r = requests.get(
            url, 
            headers={"User-Agent": "Mozilla/5.0"}, 
            timeout=15
        )
        r.encoding = "EUC-JP"
        
        if r.status_code != 200:
            return None
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # 結果テーブルを探す
        table = soup.find("table", class_="race_table_01")
        if not table:
            # 出走表のテーブルも確認（レースが未実施の可能性）
            shutuba_table = soup.find("table", class_="Shutuba_Table")
            if shutuba_table:
                # 出走表がある = レース未実施
                return None
            # テーブルが全くない = レースが存在しない
            return None
        
        # レース情報を取得
        race_name = safe(soup.find("h1"))
        info = safe(soup.find("div", class_="data_intro")) or ""
        
        # 距離
        dist_match = re.search(r'(\d+)m', info)
        distance = int(dist_match.group(1)) if dist_match else None
        
        # コース種別
        course_type = "芝" if "芝" in info else "ダート"
        
        # トラック方向
        track_direction = "右" if "右" in info else "左"
        
        # 天候
        weather = safe(soup.find("span", class_="weather"))
        
        # 馬場状態
        track_condition = safe(soup.find("span", class_="condition"))
        
        # レース日付
        raw_date = safe(soup.find("p", class_="smalltxt"))
        race_date = parse_date(raw_date)
        
        results = []
        
        # 各馬の結果を取得
        for row in table.find_all("tr")[1:]:  # ヘッダー行をスキップ
            c = row.find_all("td")
            if len(c) < 18:
                continue
            
            # 着順
            rank_text = c[0].text.strip()
            rank = int(rank_text) if rank_text.isdigit() else None
            
            # オッズ
            odds_text = c[12].text.strip()
            odds = float(odds_text) if odds_text not in ["", "---", "----"] else None
            
            # 人気
            pop_text = c[13].text.strip()
            popularity = int(pop_text) if pop_text.isdigit() else None
            
            # タイム
            time_sec = time_to_sec(c[7].text.strip())
            
            # 馬体重
            weight = parse_weight(c[14].text.strip())
            
            # 上がり3F
            last_3f_text = c[11].text.strip()
            last_3f = float(last_3f_text) if last_3f_text not in ["", "---"] else None
            
            results.append((
                race_id,           # race_id
                race_name,         # race_name
                rank,              # rank
                int(c[1].text.strip()),  # horse_no (枠番)
                int(c[2].text.strip()),  # horse_no (馬番)
                c[3].text.strip(),       # horse_name
                c[4].text.strip(),       # sex_age
                float(c[5].text.strip()), # weight_carrier
                c[6].text.strip(),       # jockey
                time_sec,                # time_sec
                c[8].text.strip(),       # margin
                c[10].text.strip(),      # passing
                last_3f,                 # last_3f
                odds,                    # odds
                popularity,              # popularity
                weight,                  # horse_weight
                info,                    # race_info
                race_date,               # race_date
                distance,                # distance
                course_type,             # course_type
                track_direction,         # track_direction
                weather,                 # weather
                track_condition          # track_condition
            ))
        
        return results if results else None
    
    except requests.RequestException as e:
        print(f"⚠️  {race_id}: 通信エラー - {e}")
        return None
    except Exception as e:
        print(f"⚠️  {race_id}: パースエラー - {e}")
        return None

# =========================
# DB保存
# =========================
def save_to_db(rows: List[Tuple]) -> bool:
    """
    レース結果をDBに保存
    
    Args:
        rows: レース結果のリスト
    
    Returns:
        成功したらTrue
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        cur.executemany("""
            INSERT INTO race_results (
                race_id, race_name, rank, waku_no, horse_no,
                horse_name, sex_age, weight_carrier, jockey, time_sec,
                margin, passing, last_3f, odds, popularity,
                horse_weight, race_info, race_date, distance,
                course_type, track_direction, weather, track_condition
            ) VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                %s,%s,%s
            )
            ON CONFLICT (race_id, horse_no)
            DO UPDATE SET
                rank=EXCLUDED.rank,
                odds=EXCLUDED.odds,
                time_sec=EXCLUDED.time_sec,
                popularity=EXCLUDED.popularity
        """, rows)
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    
    except Exception as e:
        print(f"❌ DB保存エラー: {e}")
        return False

# =========================
# メイン処理
# =========================
def main():
    """スクレイピングのメイン処理"""
    print("="*80)
    print("🏇 競馬レース結果スクレイピング開始")
    print("="*80)
    
    # 取得済みIDをロード
    done_ids = load_done_ids()
    
    # 取得期間を決定
    start_year, end_year = get_date_range()
    print(f"📅 取得期間: {start_year}年 〜 {end_year}年")
    
    # 競馬場コード
    course_codes = [
        "01",  # 札幌
        "02",  # 函館
        "03",  # 福島
        "04",  # 新潟
        "05",  # 東京
        "06",  # 中山
        "07",  # 中京
        "08",  # 京都
        "09",  # 阪神
        "10",  # 小倉
    ]
    
    total_scraped = 0
    total_skipped = 0
    total_new = 0
    
    # 年ごとに処理
    for year in range(start_year, end_year + 1):
        print(f"\n📆 {year}年のレースを取得中...")
        
        # 競馬場ごとに処理
        for course_code in course_codes:
            # 開催回 (1-6)
            for kai in range(1, 7):
                # 日数 (1-12)
                for day in range(1, 13):
                    
                    # この日のレースを処理
                    day_has_race = False # この日にレースがあったかどうかのフラグ
                    
                    # レース番号 (1-12)
                    for r in range(1, 13):
                        race_id = f"{year}{course_code}{kai:02}{day:02}{r:02}"
                        
                        # スキップ判定
                        if race_id in done_ids:
                            total_skipped += 1
                            day_has_race = True # すでにDBにある＝レースは存在する
                            continue
                        
                        # レース結果を取得
                        rows = scrape_race(race_id)
                        
                        # レースが存在しない場合
                        if rows is None:
                            # もし第1レースが存在しなければ、その日は開催がないと判断してループを抜ける
                            # (これにより無駄なアクセスを減らしつつ、次の日/次の開催はチェックを続ける)
                            if r == 1:
                                break
                            
                            # 1Rはあるのに途中のレースがない場合は、単にそのレースがないだけとして次へ
                            # (通常JRAでは稀だが、念のため続行)
                            continue
                        
                        # レースが見つかった
                        day_has_race = True
                        
                        # DB保存
                        if save_to_db(rows):
                            done_ids.add(race_id)
                            total_new += 1
                            print(f"✓ {race_id}: {len(rows)}頭の結果を保存")
                        else:
                            print(f"❌ {race_id}: 保存失敗")
                        
                        total_scraped += 1
                        
                        # レート制限対策
                        time.sleep(1)
                        
                        # 進捗表示（100レースごと）
                        if total_scraped % 100 == 0:
                            print(f"   進捗: {total_scraped}レース取得済み")
                    
                    # 第1レースが存在しなかった場合、またはDBにもなかった場合は
                    # この日は開催がないので、ウェイトを短くして次の日へ
                    if not day_has_race:
                        # 存在しない日の確認アクセス負荷軽減のための短いスリープ
                        time.sleep(0.1)

    # 最終結果
    print("\n" + "="*80)
    print("✅ スクレイピング完了")
    print("="*80)
    print(f"📊 統計:")
    print(f"   新規取得: {total_new}レース")
    print(f"   スキップ: {total_skipped}レース")
    print(f"   合計取得済み: {len(done_ids)}レース")
    print("="*80)

# =========================
# 実行
# =========================
if __name__ == "__main__":
    main()
