"""
データ型チェックと修正ユーティリティ

LightGBMが受け付けるデータ型（int, float, bool）に変換
"""

import pandas as pd
import numpy as np


def check_and_fix_dtypes(df, exclude_cols=None):
    """
    DataFrameのデータ型をチェックし、LightGBM互換に修正
    
    Args:
        df: チェック対象のDataFrame
        exclude_cols: チェック対象外のカラムリスト
    
    Returns:
        修正後のDataFrame
    """
    if exclude_cols is None:
        exclude_cols = []
    
    print("🔍 データ型をチェック中...")
    
    issues = []
    fixed_cols = []
    
    for col in df.columns:
        if col in exclude_cols:
            continue
        
        dtype = df[col].dtype
        
        # object型（文字列）の場合
        if dtype == 'object':
            issues.append(col)
            
            # 数値に変換を試みる
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].fillna(0)
                fixed_cols.append(col)
                print(f"   ✓ {col}: object → numeric (NaNは0埋め)")
            except:
                # 変換できない場合はLabel Encoding
                df[col] = pd.factorize(df[col])[0]
                fixed_cols.append(col)
                print(f"   ✓ {col}: object → label encoded")
        
        # category型の場合
        elif dtype.name == 'category':
            df[col] = df[col].cat.codes
            fixed_cols.append(col)
            print(f"   ✓ {col}: category → int")
        
        # datetime型の場合
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            # UNIXタイムスタンプに変換
            df[col] = df[col].astype(np.int64) // 10**9
            fixed_cols.append(col)
            print(f"   ✓ {col}: datetime → unix timestamp")
    
    if issues:
        print(f"\n⚠️  修正が必要だったカラム: {len(issues)}個")
        print(f"   {issues}")
    else:
        print("✅ すべてのカラムが数値型です")
    
    return df


def validate_for_lightgbm(df, feature_list):
    """
    LightGBM用にデータを検証・修正
    
    Args:
        df: 検証対象のDataFrame
        feature_list: 使用する特徴量のリスト
    
    Returns:
        検証済みのDataFrame
    """
    print("\n🔍 LightGBM用データ検証")
    print("="*60)
    
    # 1. 特徴量の存在チェック
    missing_features = set(feature_list) - set(df.columns)
    if missing_features:
        print(f"⚠️  不足している特徴量: {len(missing_features)}個")
        for feat in missing_features:
            df[feat] = 0
            print(f"   ✓ {feat} を0で追加")
    
    # 2. 特徴量のみ抽出
    df_features = df[feature_list].copy()
    
    # 3. データ型チェック
    print("\n📊 データ型の分布:")
    dtype_counts = df_features.dtypes.value_counts()
    for dtype, count in dtype_counts.items():
        print(f"   {dtype}: {count}個")
    
    # 4. object型のカラムを検出
    object_cols = df_features.select_dtypes(include=['object']).columns.tolist()
    if object_cols:
        print(f"\n❌ object型のカラムが見つかりました: {len(object_cols)}個")
        for col in object_cols:
            print(f"   - {col}: {df_features[col].dtype}")
            # サンプル値を表示
            sample_vals = df_features[col].dropna().unique()[:5]
            print(f"     サンプル: {sample_vals}")
        
        # 自動修正
        print("\n🔧 自動修正中...")
        df_features = check_and_fix_dtypes(df_features)
    
    # 5. NaN/Infチェック
    print("\n🔍 欠損値・無限大チェック:")
    nan_counts = df_features.isna().sum()
    nan_cols = nan_counts[nan_counts > 0]
    if len(nan_cols) > 0:
        print(f"   ⚠️  NaNを含むカラム: {len(nan_cols)}個")
        for col, count in nan_cols.items():
            print(f"   - {col}: {count}個")
            df_features[col] = df_features[col].fillna(0)
        print("   ✓ すべて0で埋めました")
    else:
        print("   ✅ NaNなし")
    
    # Inf チェック
    inf_mask = np.isinf(df_features.select_dtypes(include=[np.number]))
    if inf_mask.any().any():
        print("   ⚠️  無限大を含むカラムがあります")
        df_features = df_features.replace([np.inf, -np.inf], 0)
        print("   ✓ 無限大を0で置換しました")
    else:
        print("   ✅ 無限大なし")
    
    # 6. 最終確認
    print("\n✅ 最終確認:")
    final_dtypes = df_features.dtypes.unique()
    print(f"   データ型: {final_dtypes}")
    print(f"   形状: {df_features.shape}")
    
    # LightGBM互換かチェック
    valid_dtypes = ['int8', 'int16', 'int32', 'int64', 
                   'uint8', 'uint16', 'uint32', 'uint64',
                   'float16', 'float32', 'float64', 'bool']
    
    invalid_cols = []
    for col in df_features.columns:
        if df_features[col].dtype.name not in valid_dtypes:
            invalid_cols.append((col, df_features[col].dtype))
    
    if invalid_cols:
        print(f"\n❌ まだLightGBM非互換のカラムがあります:")
        for col, dtype in invalid_cols:
            print(f"   - {col}: {dtype}")
        raise ValueError("データ型の修正に失敗しました")
    
    print("\n✅ すべてのデータがLightGBM互換です！")
    print("="*60)
    
    return df_features


if __name__ == "__main__":
    # テスト
    print("データ型チェックユーティリティのテスト")
    
    # サンプルデータ
    df = pd.DataFrame({
        'num_int': [1, 2, 3],
        'num_float': [1.0, 2.0, 3.0],
        'str_col': ['a', 'b', 'c'],
        'bool_col': [True, False, True],
        'mixed': ['1', '2', '3'],
    })
    
    print("\n元のデータ型:")
    print(df.dtypes)
    
    print("\n修正実行:")
    df_fixed = check_and_fix_dtypes(df)
    
    print("\n修正後のデータ型:")
    print(df_fixed.dtypes)
    
    print("\n修正後のデータ:")
    print(df_fixed)
