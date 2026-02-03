import pandas as pd

def add_recent_diff_features(df, n_recent=3):
    """
    horse_name 単位で近走平均との差特徴量を作る
    
    必須カラム:
    - horse_name: 馬名
    
    前提：
      - 同一DataFrame内に複数レースが含まれている
      - 過去→未来の順で race_date が並んでいる or ソート可能
    """
    # 必須カラムの存在チェック
    if "horse_name" not in df.columns:
        print(f"      ⚠️  近走差分特徴量: horse_nameカラムが不足")
        return df

    df = df.copy()

    # 日付があればソート（なければ race_id などで代用）
    if "race_date" in df.columns:
        df = df.sort_values("race_date")
    elif "race_id" in df.columns:
        df = df.sort_values("race_id")

    # 数値特徴量だけ対象
    exclude_cols = ["race_id", "race_date", "horse_name", "horse_id", "rank"]
    numeric_cols = [
        c for c in df.columns
        if c not in exclude_cols
        and pd.api.types.is_numeric_dtype(df[c])
    ]

    # 近走差分特徴量の作成
    processed_count = 0
    for col in numeric_cols:
        try:
            # 近走平均の計算
            df[f"{col}_recent_avg_{n_recent}"] = (
                df
                .groupby("horse_name")[col]
                .transform(lambda x: x.shift(1).rolling(n_recent).mean())
            )

            # 差分の計算
            df[f"{col}_recent_diff_{n_recent}"] = (
                df[col] - df[f"{col}_recent_avg_{n_recent}"]
            )
            processed_count += 1
        except Exception as e:
            # 個別のカラムでエラーが出ても続行
            continue
    
    if processed_count > 0:
        print(f"      ✓ {processed_count}個の数値カラムに近走差分を追加")

    return df
