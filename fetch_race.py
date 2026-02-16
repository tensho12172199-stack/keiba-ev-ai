"""
レースデータ取得スクリプト（修正版）

result.html のURLでも自動的に shutuba.html に変換して取得
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re


def convert_to_shutuba_url(url):
    """
    result.html のURLを shutuba.html に変換
    
    Args:
        url: レースURL
    
    Returns:
        出走表のURL
    """
    # result.html を shutuba.html に置き換え
    if 'result.html' in url:
        shutuba_url = url.replace('result.html', 'shutuba.html')
        print(f"📝 result.html → shutuba.html に変換")
        print(f"   変換前: {url}")
        print(f"   変換後: {shutuba_url}")
        return shutuba_url
    
    # shutuba.html が含まれていればそのまま
    if 'shutuba.html' in url:
        return url
    
    # race_id パラメータがある場合
    if 'race_id=' in url:
        # race_id を抽出
        race_id_match = re.search(r'race_id=(\d+)', url)
        if race_id_match:
            race_id = race_id_match.group(1)
            shutuba_url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
            print(f"📝 出走表URLを生成: {shutuba_url}")
            return shutuba_url
    
    # それ以外はそのまま返す
    return url


def fetch_race_data(race_url):
    """
    レースデータを取得
    
    Args:
        race_url: レースURL（result.html でも shutuba.html でもOK）
    
    Returns:
        レースデータのDataFrame
    """
    print("\n" + "="*80)
    print("📥 レースデータ取得")
    print("="*80)
    
    # URLを変換
    shutuba_url = convert_to_shutuba_url(race_url)
    
    # データ取得
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print(f"\n🌐 アクセス中: {shutuba_url}")
        
        response = requests.get(shutuba_url, headers=headers, timeout=30)
        response.encoding = 'EUC-JP'
        
        if response.status_code != 200:
            print(f"❌ HTTPエラー: {response.status_code}")
            return None
        
        print(f"✅ ページ取得成功")
        
    except requests.RequestException as e:
        print(f"❌ 通信エラー: {e}")
        return None
    
    # HTML解析
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 出走表テーブルを探す
    table = soup.find('table', class_='Shutuba_Table')
    
    if not table:
        print("❌ 出走表テーブルが見つかりません")
        print("   URLを確認してください:")
        print(f"   {shutuba_url}")
        return None
    
    print(f"✅ 出走表テーブル発見")
    
    # レース情報を取得
    race_name_tag = soup.find('h1', class_='RaceName')
    race_name = race_name_tag.text.strip() if race_name_tag else "不明"
    
    # レース条件を取得
    race_data_tag = soup.find('div', class_='RaceData01')
    race_info = race_data_tag.text.strip() if race_data_tag else ""
    
    # 距離を抽出
    distance_match = re.search(r'(\d+)m', race_info)
    distance = int(distance_match.group(1)) if distance_match else None
    
    # コース種別
    course_type = "芝" if "芝" in race_info else "ダート"
    
    # トラック方向
    track_direction = "右" if "右" in race_info else "左"
    
    # 天候
    weather_tag = soup.find('span', class_='Weather')
    weather = weather_tag.text.strip() if weather_tag else None
    
    # 馬場状態
    condition_tag = soup.find('span', class_='BabaInfo')
    track_condition = condition_tag.text.strip() if condition_tag else None
    
    print(f"\n📋 レース情報:")
    print(f"   レース名: {race_name}")
    print(f"   距離: {distance}m")
    print(f"   コース: {course_type} {track_direction}")
    print(f"   天候: {weather}")
    print(f"   馬場: {track_condition}")
    
    # 馬データを取得
    horses = []
    
    rows = table.find_all('tr')
    
    for row in rows[1:]:  # ヘッダー行をスキップ
        cols = row.find_all('td')
        
        if len(cols) < 10:
            continue
        
        try:
            # 枠番
            waku_no = int(cols[0].text.strip()) if cols[0].text.strip() else None
            
            # 馬番
            horse_no = int(cols[1].text.strip()) if cols[1].text.strip() else None
            
            # 馬名
            horse_name_tag = cols[3].find('a')
            horse_name = horse_name_tag.text.strip() if horse_name_tag else cols[3].text.strip()
            
            # 性齢
            sex_age = cols[4].text.strip()
            
            # 斤量
            weight_carrier_text = cols[5].text.strip()
            weight_carrier = float(weight_carrier_text) if weight_carrier_text else None
            
            # 騎手
            jockey_tag = cols[6].find('a')
            jockey = jockey_tag.text.strip() if jockey_tag else cols[6].text.strip()
            
            # 調教師
            trainer_tag = cols[7].find('a')
            trainer = trainer_tag.text.strip() if trainer_tag else cols[7].text.strip()
            
            # 馬体重（出走表では表示されない場合がある）
            horse_weight = None
            if len(cols) > 10:
                weight_text = cols[10].text.strip()
                if weight_text and '(' in weight_text:
                    try:
                        horse_weight = int(weight_text.split('(')[0])
                    except:
                        pass
            
            horses.append({
                'race_id': race_url.split('race_id=')[-1] if 'race_id=' in race_url else None,
                'race_name': race_name,
                'waku_no': waku_no,
                'horse_no': horse_no,
                'horse_name': horse_name,
                'sex_age': sex_age,
                'weight_carrier': weight_carrier,
                'jockey': jockey,
                'trainer': trainer,
                'horse_weight': horse_weight,
                'distance': distance,
                'course_type': course_type,
                'track_direction': track_direction,
                'weather': weather,
                'track_condition': track_condition
            })
        
        except Exception as e:
            print(f"⚠️  行の解析でエラー: {e}")
            continue
    
    if not horses:
        print("❌ 馬データを取得できませんでした")
        return None
    
    df = pd.DataFrame(horses)
    
    print(f"\n✅ データ取得完了: {len(df)}頭")
    print("="*80)
    
    return df


if __name__ == "__main__":
    # テスト
    print("レースデータ取得スクリプト（テスト）")
    
    # result.html のURL（自動変換される）
    test_url = "https://race.netkeiba.com/race/result.html?race_id=202506050509"
    
    df = fetch_race_data(test_url)
    
    if df is not None:
        print("\n取得したデータ:")
        print(df[['horse_no', 'horse_name', 'sex_age', 'weight_carrier']].head())
