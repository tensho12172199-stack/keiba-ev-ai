import pandas as pd
from pathlib import Path

def add_jockey_style_features(df, jockey_profile_path="jockey_profile.csv"):
    """
    騎手の脚質傾向データをマージし、スコアを計算する。
    
    必須カラム:
    - jockey: 騎手名
    
    オプショナル（add_passing_features()で作成される）:
    - style_front, style_stalker, style_closer
    """
    # 必須カラムの存在チェック
    if "jockey" not in df.columns:
        print(f"      ⚠️  騎手特徴量: jockeyカラムが不足")
        return df
    
    # 必要なカラム名
    cols_to_check = ["jockey_front_rate", "jockey_stalker_rate", "jockey_closer_rate"]
    
    # すべてのカラムが既に存在しているかチェック
    is_merged = all(c in df.columns for c in cols_to_check)

    if not is_merged:
        # ファイルが存在するか確認
        if not Path(jockey_profile_path).exists():
            print(f"      ℹ️  {jockey_profile_path} が見つからないため、騎手特徴量はスキップします")
            return df

        try:
            jockey_df = pd.read_csv(jockey_profile_path)
            df = df.merge(jockey_df, on="jockey", how="left")
        except Exception as e:
            print(f"      ⚠️  騎手プロファイルの読み込みに失敗: {e}")
            return df

    # スコア計算（これらのカラムが存在する前提）
    # スタイルカラムの存在チェック
    style_cols = ["style_front", "style_stalker", "style_closer"]
    jockey_cols = ["jockey_front_rate", "jockey_stalker_rate", "jockey_closer_rate"]
    
    if all(c in df.columns for c in style_cols + jockey_cols):
        # 欠損値は0埋め
        for col in jockey_cols:
            df[col] = df[col].fillna(0)
        
        df["jockey_style_front_score"] = df["style_front"] * df["jockey_front_rate"]
        df["jockey_style_stalker_score"] = df["style_stalker"] * df["jockey_stalker_rate"]
        df["jockey_style_closer_score"] = df["style_closer"] * df["jockey_closer_rate"]
    else:
        print(f"      ℹ️  騎手スタイルスコア: 脚質カラムが不足（add_passing_features()を先に実行してください）")
    
    return df
