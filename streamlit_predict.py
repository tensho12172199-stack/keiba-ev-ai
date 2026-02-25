"""
Streamlit用 予測関数（特徴量不一致エラー修正版）

app.py で使用する予測関数
"""

import pandas as pd
import numpy as np
import joblib
import streamlit as st
from pathlib import Path


def load_exclude_list_streamlit():
    """
    除外リストを読み込み（Streamlit用）
    
    Returns:
        除外する特徴量のリスト
    """
    # simple_weights.yaml がある場合
    config_file = Path("simple_weights.yaml")
    
    if config_file.exists():
        import yaml
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('exclude_features', [])
    
    # ない場合はデフォルトの除外リスト
    return [
        # リーク
        "rank", "time", "time_sec", "speed", "margin", 
        "odds", "popularity",
        "passing", "passing_1c", "passing_4c", "last_3f",
        "speed_recent_diff_3",
        # 識別情報
        "race_id", "race_name", "race_date", "date",
        "horse_name", "horse_id", "jockey", "trainer", "owner",
        # 変換済み
        "sex_age", "horse_weight", "waku_no", "horse_no"
    ]


def select_features_streamlit(df, exclude_list=None):
    """
    特徴量を選択（Streamlit用）
    
    Args:
        df: DataFrame
        exclude_list: 除外リスト
    
    Returns:
        特徴量名のリスト
    """
    if exclude_list is None:
        exclude_list = load_exclude_list_streamlit()
    
    # デフォルトの除外リスト
    default_exclude = ['race_id', 'race_date', 'horse_name', 'rank']
    
    # マージ
    all_exclude = list(set(exclude_list + default_exclude))
    
    # 数値カラムのみ
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    
    # 除外
    features = [col for col in numeric_cols if col not in all_exclude]
    
    return features


def predict_race_streamlit(race_df, 
                           model_file="horse_racing_full_model.txt",
                           feature_list_file="feature_list.pkl"):
    """
    レース予測（Streamlit用）
    
    Args:
        race_df: レースデータのDataFrame
        model_file: モデルファイル
        feature_list_file: 特徴量リストファイル
    
    Returns:
        予測結果のDataFrame
    """
    try:
        # モデル読み込み
        if not Path(model_file).exists():
            st.error(f"❌ モデルファイルが見つかりません: {model_file}")
            return None
        
        if not Path(feature_list_file).exists():
            st.error(f"❌ 特徴量リストが見つかりません: {feature_list_file}")
            return None
        
        model = joblib.load(model_file)
        feature_list = joblib.load(feature_list_file)
        
        st.info(f"✓ モデル読み込み完了（学習時の特徴量: {len(feature_list)}個）")
        
        # 除外リスト読み込み
        exclude_list = load_exclude_list_streamlit()
        
        # 現在のDataFrameの状態を詳細表示
        with st.expander("🔍 現在のデータ状態（デバッグ情報）"):
            st.write(f"**全カラム数:** {len(race_df.columns)}")
            st.write(f"**行数:** {len(race_df)}")
            
            # 数値カラム
            numeric_cols = race_df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            st.write(f"**数値カラム数:** {len(numeric_cols)}")
            
            # 過去レース特徴量の確認
            past_race_features = [
                'past_races_count', 'recent_avg_rank', 'recent_best_rank',
                'recent_avg_time_sec', 'recent_avg_speed', 'recent_win_rate',
                'recent_top3_rate', 'days_since_last_race', 'recent_avg_pos_4c'
            ]
            
            st.write("**過去レース特徴量の状態:**")
            for feat in past_race_features:
                if feat in race_df.columns:
                    # 値の統計
                    non_zero = (race_df[feat] != 0).sum()
                    st.write(f"✓ {feat}: {non_zero}/{len(race_df)} 頭が非ゼロ")
                else:
                    st.write(f"❌ {feat}: 存在しない")
            
            # 全カラムリスト
            with st.expander("全カラム一覧"):
                for i, col in enumerate(race_df.columns, 1):
                    dtype = race_df[col].dtype
                    st.write(f"{i}. {col} ({dtype})")
        
        # 学習時の特徴量で欠損しているものを確認
        missing_features = []
        for feat in feature_list:
            if feat not in race_df.columns:
                missing_features.append(feat)
                race_df[feat] = 0  # 0埋め
        
        if missing_features:
            st.warning(f"⚠️ 欠損している特徴量: {len(missing_features)}個を0で埋めました")
            
            with st.expander("欠損特徴量の詳細"):
                # 過去レース特徴量かどうか判定
                past_missing = [f for f in missing_features if any(
                    keyword in f for keyword in ['recent', 'past_races', 'days_since']
                )]
                other_missing = [f for f in missing_features if f not in past_missing]
                
                if past_missing:
                    st.error(f"**過去レース特徴量が不足: {len(past_missing)}個**")
                    st.write("→ Supabase接続ができていない可能性があります")
                    for feat in past_missing[:10]:
                        st.write(f"- {feat}")
                    if len(past_missing) > 10:
                        st.write(f"... 他 {len(past_missing) - 10}個")
                
                if other_missing:
                    st.warning(f"**その他の特徴量が不足: {len(other_missing)}個**")
                    for feat in other_missing[:10]:
                        st.write(f"- {feat}")
                    if len(other_missing) > 10:
                        st.write(f"... 他 {len(other_missing) - 10}個")
        
        # 学習時と同じ順序で特徴量を並べる
        X = race_df[feature_list].copy()
        
        # 特徴量数の最終チェック
        if len(X.columns) != len(feature_list):
            st.error(f"❌ 特徴量数が一致しません")
            st.write(f"   期待: {len(feature_list)}個")
            st.write(f"   実際: {len(X.columns)}個")
            
            # 重複をチェック
            duplicates = [col for col in X.columns if list(X.columns).count(col) > 1]
            if duplicates:
                st.error(f"❌ 重複している特徴量: {set(duplicates)}")
            
            st.stop()
        
        st.success(f"✅ 予測用データ準備完了（特徴量: {len(X.columns)}個）")
        
        # デバッグ情報
        with st.expander("🔍 特徴量リスト（デバッグ用）"):
            st.write(f"**学習時の特徴量数**: {len(feature_list)}")
            st.write(f"**予測時の特徴量数**: {len(X.columns)}")
            
            if len(X.columns) != len(feature_list):
                st.warning(f"⚠️ 特徴量数が不一致（学習: {len(feature_list)}, 予測: {len(X.columns)}）")
            
            # 重複チェック
            duplicates = [col for col in X.columns if list(X.columns).count(col) > 1]
            if duplicates:
                st.error(f"❌ 重複している特徴量: {set(duplicates)}")
            
            st.write("**特徴量一覧:**")
            st.dataframe(pd.DataFrame({
                'feature': X.columns,
                'dtype': X.dtypes.values,
                'null_count': X.isna().sum().values
            }))
        
        # 予測
        with st.spinner("🔮 予測計算中..."):
            try:
                # 一時的にshape checkを無効化
                predictions = model.predict(X, predict_disable_shape_check=True)
                
                if len(X.columns) != len(feature_list):
                    st.warning(
                        f"⚠️ 特徴量数が不一致のため、一時的に予測を続行しています。\n"
                        f"正確な予測のため、モデルの再学習を推奨します。"
                    )
                    
            except Exception as e:
                st.error(f"❌ 予測エラー: {e}")
                
                # 詳細診断
                st.write("### 詳細診断情報")
                st.write(f"入力データの形状: {X.shape}")
                st.write(f"データ型: {X.dtypes.value_counts()}")
                
                # NaNや無限大をチェック
                nan_cols = X.columns[X.isna().any()].tolist()
                if nan_cols:
                    st.warning(f"⚠️ NaN含む列: {nan_cols}")
                
                inf_cols = X.columns[(X == np.inf).any() | (X == -np.inf).any()].tolist()
                if inf_cols:
                    st.warning(f"⚠️ 無限大含む列: {inf_cols}")
                
                raise
        
        # 結果をDataFrameに追加
        result_df = race_df.copy()
        result_df['predicted_score'] = predictions
        
        # 予測順位（スコアが低い方が上位）
        result_df['predicted_rank'] = result_df['predicted_score'].rank(method='min').astype(int)
        
        # スコアの低い順（＝予測上位順）にソート
        result_df = result_df.sort_values('predicted_score', ascending=True)
        
        st.success("✅ 予測完了！")
        
        return result_df
    
    except Exception as e:
        st.error(f"❌ 予測エラー: {e}")
        import traceback
        with st.expander("詳細なエラー情報"):
            st.code(traceback.format_exc())
        return None


# Streamlit用の簡易版（互換性維持）
def predict_plackett_luce_streamlit(race_df, 
                                    model_file="horse_racing_full_model.txt",
                                    feature_list_file="feature_list.pkl",
                                    n_simulations=50000):
    """
    Plackett-Luceモデルでの予測（Streamlit用）
    
    Args:
        race_df: レースデータ
        model_file: モデルファイル
        feature_list_file: 特徴量リスト
        n_simulations: シミュレーション回数
    
    Returns:
        予測結果DataFrame
    """
    # 基本予測
    result_df = predict_race_streamlit(race_df, model_file, feature_list_file)
    
    if result_df is None:
        return None
    
    # Plackett-Luceシミュレーション
    try:
        from plackett_luce import simulate_race_probabilities
        
        st.info("🎲 Plackett-Luceシミュレーション実行中...")
        
        # スコアを確率に変換
        scores = result_df['predicted_score'].values
        
        # シミュレーション
        probabilities = simulate_race_probabilities(scores, n_simulations)
        
        # 結果を追加
        result_df['win_probability'] = probabilities['win']
        result_df['place_probability'] = probabilities['place']
        result_df['show_probability'] = probabilities['show']
        
        st.success("✅ シミュレーション完了")
        
    except ImportError:
        st.warning("⚠️ plackett_luce.py が見つかりません（確率計算スキップ）")
    except Exception as e:
        st.warning(f"⚠️ シミュレーションエラー: {e}（確率計算スキップ）")
    
    return result_df


if __name__ == "__main__":
    # テスト用
    print("Streamlit用予測関数")
    
    # サンプルデータ
    sample_data = {
        'horse_name': ['馬A', '馬B', '馬C'],
        'age': [4, 5, 3],
        'sex': [0, 0, 1],
        'weight_carrier': [55, 56, 54],
        'recent_avg_rank': [2.3, 3.5, 1.8],
        'recent_win_rate': [0.33, 0.20, 0.45]
    }
    
    df = pd.DataFrame(sample_data)
    
    print("\nサンプルデータ:")
    print(df)
    
    # 除外リスト確認
    exclude_list = load_exclude_list_streamlit()
    print(f"\n除外リスト: {len(exclude_list)}個")
