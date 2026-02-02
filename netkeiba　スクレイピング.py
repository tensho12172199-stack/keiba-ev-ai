import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

def scrape_race_results(race_id):
    """
    Scrape netkeiba race results for a given race_id.
    """
    url = f"https://db.netkeiba.com/race/{race_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.encoding = 'EUC-JP'
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', attrs={'class': 'race_table_01'})
        if not table:
            return None
        
        race_intro = soup.find('div', attrs={'class': 'data_intro'})
        race_name = race_intro.find('h1').text.strip() if race_intro and race_intro.find('h1') else ""
        race_details = race_intro.find('p').text.strip() if race_intro and race_intro.find('p') else ""

        rows = table.find_all('tr')
        race_data = []
        for i, row in enumerate(rows):
            if i == 0: continue
            cols = row.find_all('td')
            if len(cols) < 10: continue
            
            race_data.append({
                'race_id': race_id,
                'race_name': race_name,
                'rank': cols[0].text.strip(),
                'bracket': cols[1].text.strip(),
                'horse_no': cols[2].text.strip(),
                'horse_name': cols[3].text.strip(),
                'age_sex': cols[4].text.strip(),
                'weight_carrier': cols[5].text.strip(),
                'jockey': cols[6].text.strip(),
                'time': cols[7].text.strip(),
                'margin': cols[8].text.strip(),
                'passing': cols[10].text.strip(),
                'last_3f': cols[11].text.strip(),
                'odds': cols[12].text.strip(),
                'popularity': cols[13].text.strip(),
                'horse_weight': cols[14].text.strip(),
                'race_details': race_details
            })
        return pd.DataFrame(race_data)
    except Exception as e:
        print(f"\n[Error] {race_id}: {e}")
        return None

def main():
    # 設定: 2019年から2023年まで
    years = range(2019, 2026)
    course_codes = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]
    
    print(f"中央競馬データ収集を開始します（年度別保存モード）...")
    start_all = time.time()

    for year in years:
        output_file = f"horse_race_data_{year}.csv"
        
        # すでにファイルが存在する場合はその年をスキップ
        if os.path.exists(output_file):
            print(f"\n[Skip] {year}年度のデータは既に存在するためスキップします。")
            continue

        print(f"\n--- {year}年度の取得を開始 ---")
        
        for course in course_codes:
            for kai in range(1, 7):
                for day in range(1, 13):
                    daily_data = []
                    for race_num in range(1, 13):
                        race_id = f"{year}{course}{str(kai).zfill(2)}{str(day).zfill(2)}{str(race_num).zfill(2)}"
                        
                        df = scrape_race_results(race_id)
                        if df is not None:
                            daily_data.append(df)
                            print(f"\r処理中: {year} {course}場 {kai}回 {day}日 {race_num}R", end="")
                            time.sleep(1.0) # 安定性を高めるため1秒に設定
                        else:
                            # 1R目がなければその日の開催はなし
                            break
                    
                    # 1日分取得できたら追記
                    if daily_data:
                        final_daily_df = pd.concat(daily_data, ignore_index=True)
                        final_daily_df.to_csv(output_file, mode='a', index=False, 
                                            header=not os.path.exists(output_file), 
                                            encoding='utf_8_sig')
    
    print(f"\n\n全ての処理が完了しました。")

if __name__ == "__main__":
    main()