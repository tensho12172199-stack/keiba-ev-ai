import pandas as pd
import numpy as np

# =====================
# age_sex
# =====================
def process_age_sex(df):
    """年齢と性別の処理"""
    if "age_sex" not in df.columns:
        print("      ⚠️  age_sexカラムが存在しません - スキップ")
        return df
    
    try:
        df["age"] = df["age_sex"].str.extract(r"(\d+)").astype(float)
        
        # 性別のマッピング（牡=0, 牝=1, セ=2, 騸=3）
        sex_map = {"牡": 0, "牝": 1, "セ": 2, "騸": 3}
        df["sex"] = df["age_sex"].str[0].map(sex_map)
        
        # マッピングできなかった値を0（牡馬）で埋める
        df["sex"] = df["sex"].fillna(0).astype(int)
        
    except Exception as e:
        print(f"      ⚠️  age_sex処理でエラー: {e}")
        # エラー時はデフォルト値を設定
        if "age" not in df.columns:
            df["age"] = 4.0  # デフォルト年齢
        if "sex" not in df.columns:
            df["sex"] = 0  # デフォルト性別（牡馬）
    
    return df


# =====================
# horse_weight
# =====================
def process_horse_weight(df):
    """馬体重の処理"""
    if "horse_weight" not in df.columns:
        print("      ⚠️  horse_weightカラムが存在しません - スキップ")
        return df
    
    try:
        df["horse_weight_base"] = df["horse_weight"].str.extract(r"(\d+)").astype(float)
        df["horse_weight_diff"] = df["horse_weight"].str.extract(r"\(([+-]?\d+)\)").astype(float)
    except Exception as e:
        print(f"      ⚠️  horse_weight処理でエラー: {e}")
    
    return df


# =====================
# odds
# =====================
def process_odds(df):
    """オッズの処理"""
    if "odds" not in df.columns:
        # オッズは必須ではないのでスキップ（メッセージも出さない）
        return df
    
    df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
    return df


# =====================
# passing → pos_4c
# =====================
def process_passing(df):
    """通過順の処理（4角位置の抽出）"""
    if "passing" not in df.columns:
        print("      ⚠️  passingカラムが存在しません - スキップ")
        return df
    
    try:
        df["pos_4c"] = (
            df["passing"]
            .astype(str)
            .str.split("-")
            .str[-1]
            .replace("", np.nan)
            .astype(float)
        )
    except Exception as e:
        print(f"      ⚠️  passing処理でエラー: {e}")
    
    return df


# =====================
# running style
# =====================
def process_running_style(df):
    """脚質の判定"""
    if "pos_4c" not in df.columns:
        # pos_4cが無ければスキップ（process_passingで作られる）
        return df
    
    try:
        df["running_style"] = df["pos_4c"].apply(
            lambda x: 0 if x <= 5 else 1 if x <= 9 else 2
            if pd.notna(x) else np.nan
        )
    except Exception as e:
        print(f"      ⚠️  running_style処理でエラー: {e}")
    
    return df


# =====================
# time normalize
# =====================
def process_time(df):
    """タイムの正規化"""
    if "time" not in df.columns:
        print("      ⚠️  timeカラムが存在しません - スキップ")
        return df
    
    def to_sec(t):
        """タイムを秒に変換"""
        try:
            if pd.isna(t):
                return np.nan
            t = str(t).strip()
            if ":" in t:
                m, s = t.split(":")
                return int(m) * 60 + float(s)
            else:
                # コロンがない場合は秒として扱う
                return float(t)
        except:
            return np.nan

    df["time_sec"] = df["time"].apply(to_sec)

    # 距離があればメートルあたりのタイムを計算
    if "distance" in df.columns and "time_sec" in df.columns:
        try:
            df["time_per_meter"] = df["time_sec"] / df["distance"]
            
            # レース内での相対的な速さ
            if "race_id" in df.columns:
                df["time_diff_race"] = (
                    df["time_per_meter"]
                    - df.groupby("race_id")["time_per_meter"].transform("mean")
                )
        except Exception as e:
            print(f"      ⚠️  time_per_meter処理でエラー: {e}")

    return df


# =====================
# jockey profile merge
# =====================
def merge_jockey_profile(df, jockey_csv="jockey_profile.csv"):
    """騎手プロファイルのマージ"""
    if "jockey" not in df.columns:
        print("      ⚠️  jockeyカラムが存在しません - jockey_profile マージをスキップ")
        return df
    
    try:
        jockey_df = pd.read_csv(jockey_csv)
        df = df.merge(jockey_df, on="jockey", how="left")
    except FileNotFoundError:
        # ファイルがない場合は静かにスキップ（騎手特徴量追加時に再度チェック）
        pass
    except Exception as e:
        print(f"      ⚠️  jockey_profile読み込みでエラー: {e}")
    
    return df


# =====================
# master
# =====================
def apply_all_features(df):
    """すべての基本特徴量処理を適用"""
    df = process_age_sex(df)
    df = process_horse_weight(df)
    df = process_odds(df)
    df = process_passing(df)
    df = process_running_style(df)
    df = process_time(df)
    df = merge_jockey_profile(df)
    return df
