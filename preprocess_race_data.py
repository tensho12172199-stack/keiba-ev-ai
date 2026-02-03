"""
競馬データの前処理スクリプト

race_detailsカラムから以下の情報を抽出：
- distance: 距離（メートル）
- course_type: コース種別（芝/ダート）
- track_direction: コース回り（左/右/直線）
- weather: 天候
- track_condition: 馬場状態
"""

import pandas as pd
import re
from pathlib import Path


def extract_distance(race_details):
    """
    距離を抽出
    例: "芝右1800m" → 1800
    """
    if pd.isna(race_details):
        return None
    
    match = re.search(r'(\d{3,4})m', str(race_details))
    if match:
        return int(match.group(1))
    return None


def extract_course_type(race_details):
    """
    コース種別を抽出
    例: "芝右1800m" → "turf"
        "ダ右1000m" → "dirt"
    """
    if pd.isna(race_details):
        return None
    
    detail_str = str(race_details)
    if '芝' in detail_str:
        return 'turf'
    elif 'ダ' in detail_str or 'ダート' in detail_str:
        return 'dirt'
    return None


def extract_track_direction(race_details):
    """
    コース回りを抽出
    例: "芝右1800m" → "right"
        "芝左2000m" → "left"
    """
    if pd.isna(race_details):
        return None
    
    detail_str = str(race_details)
    if '右' in detail_str:
        return 'right'
    elif '左' in detail_str:
        return 'left'
    elif '直' in detail_str:
        return 'straight'
    return None


def extract_weather(race_details):
    """
    天候を抽出
    例: "天候 : 曇" → "cloudy"
    """
    if pd.isna(race_details):
        return None
    
    detail_str = str(race_details)
    
    # 天候のマッピング
    weather_map = {
        '晴': 'sunny',
        '曇': 'cloudy',
        '雨': 'rainy',
        '小雨': 'light_rain',
        '雪': 'snowy',
    }
    
    for jp, en in weather_map.items():
        if jp in detail_str:
            return en
    
    return None


def extract_track_condition(race_details):
    """
    馬場状態を抽出
    例: "芝 : 良" → "firm"
        "ダート : 重" → "heavy"
    """
    if pd.isna(race_details):
        return None
    
    detail_str = str(race_details)
    
    # 馬場状態のマッピング
    condition_map = {
        '良': 'firm',
        '稍': 'good',
        '稍重': 'good',
        '重': 'yielding',
        '不良': 'soft',
    }
    
    for jp, en in condition_map.items():
        if jp in detail_str:
            return en
    
    return None


def extract_race_date(race_id):
    """
    race_idから日付を抽出
    例: "201901010101" → "2019-01-01"
    """
    if pd.isna(race_id):
        return None
    
    race_id_str = str(race_id)
    if len(race_id_str) >= 8:
        year = race_id_str[0:4]
        month = race_id_str[4:6]
        day = race_id_str[6:8]
        return f"{year}-{month}-{day}"
    
    return None


def preprocess_race_data(input_csv, output_csv=None):
    """
    競馬データの前処理を実行
    
    Args:
        input_csv: 入力CSVファイルパス
        output_csv: 出力CSVファイルパス（Noneの場合、_processed.csvを追加）
    
    Returns:
        処理後のDataFrame
    """
    print("="*80)
    print("🏇 競馬データ前処理スクリプト")
    print("="*80)
    
    # ファイル読み込み
    print(f"\n📂 データ読み込み中: {input_csv}")
    df = pd.read_csv(input_csv)
    print(f"   行数: {len(df):,}")
    print(f"   カラム数: {len(df.columns)}")
    
    initial_columns = len(df.columns)
    
    # race_dateの抽出
    if 'race_id' in df.columns:
        print("\n🔧 race_idから日付を抽出中...")
        df['race_date'] = df['race_id'].apply(extract_race_date)
        extracted = df['race_date'].notna().sum()
        print(f"   ✓ {extracted:,} 行の日付を抽出")
    
    # race_detailsから情報抽出
    if 'race_details' in df.columns:
        print("\n🔧 race_detailsから情報を抽出中...")
        
        # 距離
        print("   ・距離（distance）...")
        df['distance'] = df['race_details'].apply(extract_distance)
        extracted = df['distance'].notna().sum()
        print(f"     ✓ {extracted:,} 行で抽出成功")
        
        # コース種別
        print("   ・コース種別（course_type）...")
        df['course_type'] = df['race_details'].apply(extract_course_type)
        extracted = df['course_type'].notna().sum()
        print(f"     ✓ {extracted:,} 行で抽出成功")
        
        # コース回り
        print("   ・コース回り（track_direction）...")
        df['track_direction'] = df['race_details'].apply(extract_track_direction)
        extracted = df['track_direction'].notna().sum()
        print(f"     ✓ {extracted:,} 行で抽出成功")
        
        # 天候
        print("   ・天候（weather）...")
        df['weather'] = df['race_details'].apply(extract_weather)
        extracted = df['weather'].notna().sum()
        print(f"     ✓ {extracted:,} 行で抽出成功")
        
        # 馬場状態
        print("   ・馬場状態（track_condition）...")
        df['track_condition'] = df['race_details'].apply(extract_track_condition)
        extracted = df['track_condition'].notna().sum()
        print(f"     ✓ {extracted:,} 行で抽出成功")
    else:
        print("\n⚠️  race_detailsカラムが見つかりません")
    
    # 統計情報の表示
    print("\n📊 抽出結果サマリー")
    print("-"*80)
    
    new_columns = ['race_date', 'distance', 'course_type', 'track_direction', 
                   'weather', 'track_condition']
    
    for col in new_columns:
        if col in df.columns:
            total = len(df)
            valid = df[col].notna().sum()
            coverage = (valid / total * 100) if total > 0 else 0
            print(f"   {col:20s}: {valid:>8,} / {total:,} ({coverage:.1f}%)")
    
    # 距離の統計
    if 'distance' in df.columns:
        print("\n📏 距離の分布")
        print("-"*80)
        distance_stats = df['distance'].describe()
        print(f"   最小: {distance_stats['min']:.0f}m")
        print(f"   最大: {distance_stats['max']:.0f}m")
        print(f"   平均: {distance_stats['mean']:.0f}m")
        print(f"   中央値: {distance_stats['50%']:.0f}m")
    
    # ファイル保存
    if output_csv is None:
        input_path = Path(input_csv)
        output_csv = input_path.parent / f"{input_path.stem}_processed.csv"
    
    print(f"\n💾 処理済みデータを保存中: {output_csv}")
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    
    added_columns = len(df.columns) - initial_columns
    print(f"   ✓ 保存完了")
    print(f"   追加カラム数: {added_columns}")
    
    print("\n" + "="*80)
    print("✅ 前処理完了！")
    print("="*80)
    
    return df


if __name__ == "__main__":
    import sys
    
    # コマンドライン引数の処理
    if len(sys.argv) < 2:
        print("使用方法: python preprocess_race_data.py <入力CSVファイル> [出力CSVファイル]")
        print("例: python preprocess_race_data.py horse_race_data_2019.csv")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 入力ファイルの存在チェック
    if not Path(input_csv).exists():
        print(f"❌ ファイルが見つかりません: {input_csv}")
        sys.exit(1)
    
    # 前処理実行
    try:
        df = preprocess_race_data(input_csv, output_csv)
        
        # サンプルデータの表示
        print("\n👀 処理後データのサンプル（最初の3行）")
        print("-"*80)
        sample_cols = ['race_id', 'horse_name', 'distance', 'course_type', 
                      'track_direction', 'weather', 'track_condition']
        display_cols = [col for col in sample_cols if col in df.columns]
        print(df[display_cols].head(3).to_string(index=False))
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
