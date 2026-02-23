"""
予測時用 脚質特徴量生成

Supabaseから各馬の過去レース通過順を取得して脚質を判定
"""

import pandas as pd
import numpy as np


def get_horse_typical_passing_from_supabase(df, supabase_db, n_races=3):
    """
    Supabaseから各馬の過去レース通過順を取得して典型的な脚質を判定
    
    Args:
        df: 予測対象のDataFrame（horse_nameカラムが必要）
        supabase_db: Supabaseデータベース接続
        n_races: 参照する過去レース数
    
    Returns:
        脚質特徴量が追加されたDataFrame
    """
    if 'horse_name' not in df.columns:
        print("⚠️ horse_nameカラムがありません")
        return df
    
    print(f"🔍 過去{n_races}走の通過順から脚質を判定中...")
    
    # 各馬の典型的な4コーナー位置を計算
    df['passing_4c_typical'] = 0
    
    for idx, row in df.iterrows():
        horse_name = row['horse_name']
        
        try:
            # Supabaseから過去レースを取得
            past_races = supabase_db.get_horse_history(horse_name, limit=n_races)
            
            if past_races and len(past_races) > 0:
                # 過去レースの通過順を解析
                passing_4c_values = []
                
                for race in past_races:
                    passing = race.get('passing', '')
                    if passing:
                        # 通過順を分解 "1-2-3-4" → [1,2,3,4]
                        positions = []
                        for p in str(passing).split('-'):
                            try:
                                positions.append(int(p))
                            except:
                                continue
                        
                        # 4コーナー位置（最後の位置）
                        if len(positions) >= 4:
                            passing_4c_values.append(positions[3])
                        elif len(positions) > 0:
                            passing_4c_values.append(positions[-1])
                
                # 平均4コーナー位置を計算
                if passing_4c_values:
                    avg_4c = np.mean(passing_4c_values)
                    df.at[idx, 'passing_4c_typical'] = avg_4c
        
        except Exception as e:
            print(f"   ⚠️ {horse_name}: エラー ({e})")
            continue
    
    # 典型的な4コーナー位置から脚質を判定
    df['style_front'] = (df['passing_4c_typical'] <= 4).astype(int)
    df['style_stalker'] = ((df['passing_4c_typical'] > 4) & (df['passing_4c_typical'] <= 9)).astype(int)
    df['style_closer'] = (df['passing_4c_typical'] > 9).astype(int)
    
    # passing_gain は過去の平均上がりを計算（簡易版：0に設定）
    df['passing_gain'] = 0
    
    # 統計
    front_count = df['style_front'].sum()
    stalker_count = df['style_stalker'].sum()
    closer_count = df['style_closer'].sum()
    
    print(f"   逃げ: {front_count}頭, 先行: {stalker_count}頭, 差し: {closer_count}頭")
    
    return df


def add_passing_features_for_prediction(df, supabase_db=None):
    """
    予測時用の通過順・脚質特徴量を追加
    
    Args:
        df: 予測対象のDataFrame
        supabase_db: Supabaseデータベース接続（任意）
    
    Returns:
        特徴量が追加されたDataFrame
    """
    print("\n🏇 脚質特徴量を生成中...")
    
    # passingカラムがあれば通常の処理
    if 'passing' in df.columns:
        from add_passing_features import add_passing_features
        df = add_passing_features(df)
        print("   ✓ passingカラムから脚質を判定")
        return df
    
    # passingがない場合はSupabaseから取得
    if supabase_db is not None:
        df = get_horse_typical_passing_from_supabase(df, supabase_db, n_races=5)  # 3 → 5に変更
        print("   ✓ Supabaseから過去レースの脚質を取得")
        return df
    
    # どちらもない場合はデフォルト値
    print("   ⚠️ passingデータなし、Supabase未接続 → デフォルト値を設定")
    
    df['passing_1c'] = 0
    df['passing_4c'] = 0
    df['passing_gain'] = 0
    df['style_front'] = 0
    df['style_stalker'] = 0
    df['style_closer'] = 0
    
    return df


if __name__ == "__main__":
    # テスト
    print("予測時用 脚質特徴量生成テスト")
    
    # サンプルデータ
    sample_df = pd.DataFrame({
        'horse_name': ['ドウデュース', 'イクイノックス', 'ジャスティンパレス']
    })
    
    print("\n元データ:")
    print(sample_df)
    
    # Supabaseなしでテスト
    result = add_passing_features_for_prediction(sample_df, supabase_db=None)
    
    print("\n結果:")
    print(result[['horse_name', 'style_front', 'style_stalker', 'style_closer']])
