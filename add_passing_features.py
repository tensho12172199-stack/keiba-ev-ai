import pandas as pd
import numpy as np

def parse_passing(p):
    """通過順データをパース"""
    if pd.isna(p):
        return [np.nan] * 4
    nums = [int(x) for x in str(p).split("-") if x.isdigit()]
    if len(nums) < 4:
        nums += [np.nan] * (4 - len(nums))
    return nums[:4]

def add_passing_features(df):
    """
    通過順に関する特徴量を追加
    
    必須カラム:
    - passing: 通過順（例: "1-2-3-4"）
    """
    # 必須カラムの存在チェック
    if "passing" not in df.columns:
        print(f"      ⚠️  通過順特徴量: passingカラムが不足")
        return df
    
    # 通過順のパース
    passing_cols = df["passing"].apply(parse_passing)

    df["passing_1c"] = passing_cols.apply(lambda x: x[0])
    df["passing_4c"] = passing_cols.apply(lambda x: x[3])

    df["passing_gain"] = df["passing_1c"] - df["passing_4c"]

    # 脚質分類
    df["style_front"] = (df["passing_4c"] <= 4).astype(int)
    df["style_stalker"] = ((df["passing_4c"] >= 5) & (df["passing_4c"] <= 9)).astype(int)
    df["style_closer"] = (df["passing_4c"] >= 10).astype(int)

    return df
