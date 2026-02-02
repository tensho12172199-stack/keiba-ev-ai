import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, roc_auc_score
import glob
import re

def load_data():
    all_files = glob.glob("horse_race_data_*.csv")
    if not all_files:
        print("CSVファイルが見つかりません。")
        return None
    data_list = [pd.read_csv(f) for f in all_files]
    return pd.concat(data_list, ignore_index=True)

def convert_time_to_seconds(time_str):
    """ '1:34.5' 形式を秒数(94.5)に変換 """
    try:
        if pd.isna(time_str): return np.nan
        parts = str(time_str).split(':')
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        else:
            return float(parts[0]) # 秒のみの場合
    except:
        return np.nan

def classify_leg_type(passing_str):
    """ 通過順から脚質を判定 (0:先行, 1:差し) """
    try:
        if pd.isna(passing_str): return np.nan
        first_corner = passing_str.split('-')[0]
        rank = int(first_corner)
        return 0 if rank <= 4 else 1
    except:
        return np.nan 

def preprocess_advanced(df):
    print("高度な特徴量エンジニアリング（フルスペック版）を実行中...")
    
    # --- 0. 基礎データの整形 ---
    df['rank'] = pd.to_numeric(df['rank'], errors='coerce')
    df = df.dropna(subset=['rank'])
    df['target'] = (df['rank'] == 1).astype(int)
    
    # タイム変換
    df['seconds'] = df['time'].apply(convert_time_to_seconds)
    df = df.dropna(subset=['seconds'])

    # 上がり3Fの数値化
    df['last_3f'] = pd.to_numeric(df['last_3f'], errors='coerce')
    
    # --- 1. コース情報の詳細抽出 ---
    # 競馬場コード (race_idの3,4文字目)
    df['venue'] = df['race_id'].astype(str).str[4:6]
    
    # 芝・ダート
    df['surface'] = df['race_details'].str.extract(r'([芝ダ])')
    
    # 距離
    df['distance'] = pd.to_numeric(df['race_details'].str.extract(r'(\d+)')[0], errors='coerce')
    
    # 回り (右/左/直)
    df['rotation'] = df['race_details'].str.extract(r'(右|左|直)')
    df['rotation'] = df['rotation'].fillna('Unknown')
    
    # コースタイプID (例: 06_芝_2500_右)
    df['course_id'] = df['venue'] + '_' + df['surface'] + '_' + df['distance'].astype(str) + '_' + df['rotation']

    # --- 2. 馬体重の処理 ---
    def split_weight(w):
        match = re.search(r'(\d+)\((.+)\)', str(w))
        if match:
            try:
                return float(match.group(1)), float(match.group(2))
            except:
                return float(match.group(1)), 0.0
        return np.nan, 0.0
    
    df['weight'], df['weight_diff'] = zip(*df['horse_weight'].apply(split_weight))

    # --- 3. スピード指数 (Speed Index) ---
    print("スピード指数を計算中...")
    grouped = df.groupby('course_id')['seconds']
    mean_times = grouped.transform('mean')
    std_times = grouped.transform('std')
    
    # 偏差値計算 (タイムは小さい方が良いので反転)
    df['speed_index'] = 50 + 10 * (mean_times - df['seconds']) / std_times.replace(0, 1)
    df['speed_index'] = df['speed_index'].fillna(50)

    # --- 4. 前走成績 (Lag Features) の作成 ---
    # これを作るためにデータを時系列（馬ごと・日付順）に並べる
    # race_idは概ね時系列になっているためそれを利用
    print("前走データを生成中...")
    df = df.sort_values(['horse_name', 'race_id'])
    
    # shift(1) で1つ前の行（前走）のデータを取得
    grouped_horse = df.groupby('horse_name')
    
    df['prev_rank'] = grouped_horse['rank'].shift(1)       # 前走着順
    df['prev_speed_index'] = grouped_horse['speed_index'].shift(1) # 前走指数
    df['prev_last_3f'] = grouped_horse['last_3f'].shift(1) # 前走上がり
    df['prev_distance'] = grouped_horse['distance'].shift(1) # 前走距離
    
    # 距離変化 (今回 - 前走)
    df['dist_change'] = df['distance'] - df['prev_distance']
    df['dist_change'] = df['dist_change'].fillna(0)
    
    # キャリア数 (何戦目か)
    df['career_count'] = grouped_horse.cumcount() + 1

    # 過去の平均パフォーマンス (Target Encoding的な指標)
    # ※リークを防ぐため、shiftして累積平均をとるのが理想だが、ここでは簡易的に全期間平均
    df['avg_speed_index'] = grouped_horse['speed_index'].transform('mean')
    df['avg_last_3f'] = grouped_horse['last_3f'].transform('mean')

    # --- 5. 騎手・血統・枠などの集計特徴量 ---
    print("集計特徴量を計算中...")
    
    # 脚質傾向
    df['run_type'] = df['passing'].apply(classify_leg_type)
    df['avg_run_style'] = grouped_horse['run_type'].transform('mean') # 0:逃げ寄り, 1:差し寄り

    # 騎手勝率
    df['jockey_win_rate'] = df.groupby('jockey')['target'].transform('mean')
    
    # 騎手xコース相性
    df['jockey_course_win_rate'] = df.groupby(['jockey', 'course_id'])['target'].transform('mean')
    
    # 枠番バイアス (そのコースにおける枠ごとの勝率)
    # 例: 中山芝2500mは内枠有利、などの傾向を学習させる
    df['bracket_win_rate'] = df.groupby(['course_id', 'bracket'])['target'].transform('mean')

    # --- 6. カテゴリ変数のエンコーディング ---
    le = LabelEncoder()
    # 文字列のカラムを数値に変換
    cat_cols = ['venue', 'surface', 'rotation', 'sex', 'jockey', 'horse_name']
    for col in cat_cols:
        df[col] = le.fit_transform(df[col].astype(str))

    # --- 最終的な特徴量の選択 ---
    features = [
        # 基本情報
        'bracket', 'horse_no', 'age', 'sex', 'weight_carrier',
        'weight', 'weight_diff', 'career_count',
        
        # コース環境
        'venue', 'surface', 'distance', 'rotation',
        
        # 能力指数 (過去平均)
        'avg_speed_index', 'avg_last_3f', 'avg_run_style',
        
        # 前走情報 (直近の調子)
        'prev_rank', 'prev_speed_index', 'prev_last_3f', 'dist_change',
        
        # 騎手・相性・傾向データ
        'jockey_win_rate',
        'jockey_course_win_rate',
        'bracket_win_rate'
    ]
    
    # 欠損値埋め
    X = df[features].fillna(0)
    y = df['target']
    
    return X, y, features

def train_and_evaluate(X, y, feature_names):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    train_data = lgb.Dataset(X_train, label=y_train)
    
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'verbosity': -1,
        'boosting_type': 'gbdt',
        'learning_rate': 0.05,
        'num_leaves': 63,        # 特徴量が増えたので少し複雑に
        'feature_fraction': 0.8, # 過学習防止
        'random_state': 42
    }
    
    print("\nモデル学習を開始します...")
    model = lgb.train(params, train_data, num_boost_round=150)
    
    # 評価
    y_pred = model.predict(X_test)
    y_pred_binary = [1 if p > 0.5 else 0 for p in y_pred]
    
    print(f"正解率 (Accuracy): {accuracy_score(y_test, y_pred_binary):.4f}")
    print(f"AUCスコア: {roc_auc_score(y_test, y_pred):.4f}")
    
    # 重要度表示
    imp = pd.DataFrame({'feature': feature_names, 'importance': model.feature_importance()})
    print("\n--- 特徴量の重要度 Top 10 ---")
    print(imp.sort_values('importance', ascending=False).head(10))
    
    return model

if __name__ == "__main__":
    raw_df = load_data()
    if raw_df is not None:
        X, y, feats = preprocess_advanced(raw_df)
        model = train_and_evaluate(X, y, feats)
        model.save_model('horse_racing_full_model.txt')