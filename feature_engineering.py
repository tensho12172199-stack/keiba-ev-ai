"""
基本特徴量エンジニアリング（Supabase対応版）

Supabaseのrace_resultsテーブルのカラム名に対応した特徴量生成
"""

import pandas as pd
import numpy as np
import re


def apply_all_features(df):
    """
    基本的な特徴量エンジニアリング
    
    Supabaseカラム対応:
    - sex_age → age, sex
    - horse_weight → horse_weight_base, horse_weight_diff
    - time → time_sec (既に秒で保存済み)
    """
    df = df.copy()
    
    # ===== 1. 性齢の分解 =====
    if 'sex_age' in df.columns:
        print("      ✓ sex_ageを分解")
        
        def parse_sex_age(text):
            """性齢を分解（例: '4牡' → age=4, sex=0）"""
            if pd.isna(text) or text == '':
                return pd.Series({'age': None, 'sex': None})
            
            text = str(text).strip()
            
            # 年齢を抽出
            age_match = re.search(r'(\d+)', text)
            age = int(age_match.group(1)) if age_match else None
            
            # 性別を抽出（数値に変換）
            if '牡' in text:
                sex = 0
            elif '牝' in text:
                sex = 1
            elif 'セ' in text:
                sex = 2
            elif '騸' in text:
                sex = 3
            else:
                sex = None
            
            return pd.Series({'age': age, 'sex': sex})
        
        # age, sexカラムがなければ作成
        if 'age' not in df.columns or 'sex' not in df.columns:
            parsed = df['sex_age'].apply(parse_sex_age)
            if 'age' not in df.columns:
                df['age'] = parsed['age']
            if 'sex' not in df.columns:
                df['sex'] = parsed['sex']
    
    # sexが文字列の場合は数値に変換（重要！）
    if 'sex' in df.columns:
        if df['sex'].dtype == 'object':
            print("      ✓ sexを数値型に変換")
            df['sex'] = pd.to_numeric(df['sex'], errors='coerce')
        
        # 欠損値を0で埋める
        df['sex'] = df['sex'].fillna(0).astype(int)
    
    # ageも同様に処理
    if 'age' in df.columns:
        if df['age'].dtype == 'object':
            df['age'] = pd.to_numeric(df['age'], errors='coerce')
        df['age'] = df['age'].fillna(0).astype(int)
    
    # ===== 2. 馬体重の処理 =====
    if 'horse_weight' in df.columns:
        print("      ✓ horse_weightを処理")
        
        # Supabaseではhorse_weightはINTEGER型なので文字列変換不要
        if df['horse_weight'].dtype in ['int64', 'float64']:
            # 既に数値型の場合
            if 'horse_weight_base' not in df.columns:
                df['horse_weight_base'] = df['horse_weight']
        else:
            # 文字列型の場合（念のため）
            def parse_horse_weight(text):
                """馬体重を分解（例: '480(+4)' → base=480, diff=4）"""
                if pd.isna(text) or text == '':
                    return pd.Series({'horse_weight_base': None, 'horse_weight_diff': None})
                
                text = str(text).strip()
                
                # ベース体重
                base_match = re.search(r'(\d+)', text)
                base = int(base_match.group(1)) if base_match else None
                
                # 増減
                diff_match = re.search(r'([+-]\d+)', text)
                diff = int(diff_match.group(1)) if diff_match else 0
                
                return pd.Series({'horse_weight_base': base, 'horse_weight_diff': diff})
            
            if 'horse_weight_base' not in df.columns:
                parsed = df['horse_weight'].apply(parse_horse_weight)
                df['horse_weight_base'] = parsed['horse_weight_base']
                if 'horse_weight_diff' not in df.columns:
                    df['horse_weight_diff'] = parsed['horse_weight_diff']
    
    # ===== 3. タイムの処理 =====
    # Supabaseでは既にtime_secとして秒数で保存されている
    if 'time' in df.columns and 'time_sec' not in df.columns:
        print("      ✓ timeを秒数に変換")
        
        def time_to_seconds(time_str):
            """タイム文字列を秒数に変換（例: '1:23.4' → 83.4）"""
            if pd.isna(time_str) or time_str == '':
                return None
            
            time_str = str(time_str).strip()
            
            if ':' not in time_str:
                return None
            
            try:
                parts = time_str.split(':')
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            except:
                return None
        
        df['time_sec'] = df['time'].apply(time_to_seconds)
    
    # ===== 4. 距離帯の作成 =====
    if 'distance' in df.columns:
        print("      ✓ distance_bandを作成")
        
        def categorize_distance(dist):
            """距離を帯に分類"""
            if pd.isna(dist):
                return None
            
            dist = int(dist)
            
            if dist < 1400:
                return 0  # 短距離
            elif dist < 1800:
                return 1  # マイル
            elif dist < 2200:
                return 2  # 中距離
            elif dist < 2800:
                return 3  # 中長距離
            else:
                return 4  # 長距離
        
        df['distance_band'] = df['distance'].apply(categorize_distance)
    
    # ===== 5. コース種別のエンコーディング =====
    if 'course_type' in df.columns:
        print("      ✓ course_typeをエンコーディング")
        
        # 芝=0, ダート=1
        df['course_type_encoded'] = df['course_type'].map({
            '芝': 0,
            'ダート': 1
        }).fillna(0)
    
    # ===== 6. トラック方向のエンコーディング =====
    if 'track_direction' in df.columns:
        print("      ✓ track_directionをエンコーディング")
        
        # 右=0, 左=1
        df['track_direction_encoded'] = df['track_direction'].map({
            '右': 0,
            '左': 1
        }).fillna(0)
    
    # ===== 7. 馬場状態のエンコーディング =====
    if 'track_condition' in df.columns:
        print("      ✓ track_conditionをエンコーディング")
        
        # 良=0, 稍重=1, 重=2, 不良=3
        df['track_condition_encoded'] = df['track_condition'].map({
            '良': 0,
            '稍重': 1,
            '重': 2,
            '不良': 3
        }).fillna(0)
    
    # ===== 8. 欠損値の処理 =====
    # 数値カラムの欠損を0で埋める
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        if df[col].isna().any():
            df[col] = df[col].fillna(0)
    
    # ===== 9. すべてのobject型を数値型に変換（重要！）=====
    print("      ✓ object型カラムをチェック")
    object_cols = df.select_dtypes(include=['object']).columns
    
    for col in object_cols:
        # 識別情報以外は数値に変換を試みる
        if col not in ['race_id', 'race_name', 'horse_name', 'jockey', 'trainer', 
                       'sex_age', 'horse_weight', 'time', 'passing', 'weather', 
                       'track_condition', 'course_type', 'track_direction']:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                print(f"         - {col} を数値型に変換")
            except:
                pass
    
    return df


if __name__ == "__main__":
    # テスト
    print("基本特徴量エンジニアリング（Supabase対応版）")
    
    # サンプルデータ
    sample_data = {
        'race_id': ['202406030811'],
        'horse_name': ['テストホース'],
        'sex_age': ['4牡'],
        'horse_weight': [480],
        'distance': [2000],
        'course_type': ['芝'],
        'track_direction': ['右'],
        'track_condition': ['良'],
    }
    
    df = pd.DataFrame(sample_data)
    print("\n元データ:")
    print(df)
    
    df = apply_all_features(df)
    print("\n処理後:")
    print(df)
    
    print("\n生成されたカラム:")
    print(df.columns.tolist())
