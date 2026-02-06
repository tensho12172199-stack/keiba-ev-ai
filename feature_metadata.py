"""
特徴量メタデータ管理システム

学習時に使用した特徴量の情報を保存し、
予測時に同じ特徴量を再現できるようにします。
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any
import joblib


class FeatureMetadata:
    """
    特徴量のメタデータを管理するクラス
    
    保存される情報:
    - 使用した特徴量のリスト
    - 各特徴量の生成方法
    - 前処理パラメータ
    - 統計情報（平均、標準偏差など）
    """
    
    def __init__(self):
        self.feature_list = []
        self.feature_groups = {}
        self.preprocessing_params = {}
        self.feature_stats = {}
        self.config = {}
    
    def set_features(self, feature_list: List[str]):
        """使用する特徴量リストを設定"""
        self.feature_list = feature_list
    
    def set_feature_groups(self, groups: Dict[str, List[str]]):
        """
        特徴量グループを設定
        
        Args:
            groups: {グループ名: [特徴量リスト]}
        """
        self.feature_groups = groups
    
    def set_preprocessing_params(self, params: Dict[str, Any]):
        """
        前処理パラメータを設定
        
        Args:
            params: {
                'n_recent': 3,
                'distance_bands': {...},
                'sex_mapping': {...},
                ...
            }
        """
        self.preprocessing_params = params
    
    def calculate_feature_stats(self, df: pd.DataFrame):
        """
        特徴量の統計情報を計算
        
        Args:
            df: 学習データのDataFrame
        """
        stats = {}
        
        for feature in self.feature_list:
            if feature in df.columns:
                col_data = df[feature]
                
                stats[feature] = {
                    'mean': float(col_data.mean()) if pd.api.types.is_numeric_dtype(col_data) else None,
                    'std': float(col_data.std()) if pd.api.types.is_numeric_dtype(col_data) else None,
                    'min': float(col_data.min()) if pd.api.types.is_numeric_dtype(col_data) else None,
                    'max': float(col_data.max()) if pd.api.types.is_numeric_dtype(col_data) else None,
                    'dtype': str(col_data.dtype),
                    'null_count': int(col_data.isna().sum()),
                }
        
        self.feature_stats = stats
    
    def set_config(self, config: Dict[str, Any]):
        """
        設定情報を保存
        
        Args:
            config: training_config.yamlの内容
        """
        self.config = config
    
    def save(self, filepath: str = "feature_metadata.json"):
        """
        メタデータをJSONファイルに保存
        
        Args:
            filepath: 保存先パス
        """
        metadata = {
            'feature_list': self.feature_list,
            'feature_groups': self.feature_groups,
            'preprocessing_params': self.preprocessing_params,
            'feature_stats': self.feature_stats,
            'config': self.config,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"💾 特徴量メタデータを保存: {filepath}")
    
    @classmethod
    def load(cls, filepath: str = "feature_metadata.json"):
        """
        メタデータをJSONファイルから読み込み
        
        Args:
            filepath: 読み込み元パス
        
        Returns:
            FeatureMetadata インスタンス
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        instance = cls()
        instance.feature_list = metadata.get('feature_list', [])
        instance.feature_groups = metadata.get('feature_groups', {})
        instance.preprocessing_params = metadata.get('preprocessing_params', {})
        instance.feature_stats = metadata.get('feature_stats', {})
        instance.config = metadata.get('config', {})
        
        print(f"📂 特徴量メタデータを読み込み: {filepath}")
        print(f"   ✓ 特徴量数: {len(instance.feature_list)}")
        
        return instance
    
    def get_feature_info(self, feature_name: str) -> Dict[str, Any]:
        """
        特定の特徴量の情報を取得
        
        Args:
            feature_name: 特徴量名
        
        Returns:
            特徴量の情報辞書
        """
        info = {
            'name': feature_name,
            'stats': self.feature_stats.get(feature_name, {}),
            'group': None,
        }
        
        # どのグループに属するか
        for group_name, features in self.feature_groups.items():
            if feature_name in features:
                info['group'] = group_name
                break
        
        return info
    
    def print_summary(self):
        """メタデータのサマリーを表示"""
        print("\n" + "="*80)
        print("📊 特徴量メタデータ サマリー")
        print("="*80)
        
        print(f"\n📋 特徴量数: {len(self.feature_list)}")
        
        if self.feature_groups:
            print(f"\n🗂️  特徴量グループ:")
            for group_name, features in self.feature_groups.items():
                print(f"   {group_name:30s}: {len(features)}個")
        
        if self.preprocessing_params:
            print(f"\n⚙️  前処理パラメータ:")
            for key, value in self.preprocessing_params.items():
                print(f"   {key:30s}: {value}")
        
        if self.feature_stats:
            print(f"\n📈 統計情報（サンプル）:")
            for feature in list(self.feature_stats.keys())[:5]:
                stats = self.feature_stats[feature]
                if stats['mean'] is not None:
                    print(f"   {feature:30s}: mean={stats['mean']:.2f}, std={stats['std']:.2f}")
        
        print("="*80)


def extract_feature_metadata_from_training(
    df: pd.DataFrame,
    feature_list: List[str],
    config: Any
) -> FeatureMetadata:
    """
    学習時のデータから特徴量メタデータを抽出
    
    Args:
        df: 学習データ
        feature_list: 使用する特徴量のリスト
        config: TrainingConfig インスタンス
    
    Returns:
        FeatureMetadata インスタンス
    """
    metadata = FeatureMetadata()
    
    # 特徴量リストを設定
    metadata.set_features(feature_list)
    
    # 特徴量グループを設定
    feature_groups = {}
    if hasattr(config, 'config') and 'feature_groups' in config.config:
        for group_name, patterns in config.config['feature_groups'].items():
            group_features = []
            for feature in feature_list:
                # パターンマッチング
                import re
                for pattern in patterns:
                    if re.search(pattern, feature):
                        group_features.append(feature)
                        break
            if group_features:
                feature_groups[group_name] = group_features
    
    metadata.set_feature_groups(feature_groups)
    
    # 前処理パラメータを設定
    preprocessing_params = {}
    if hasattr(config, 'config'):
        if 'features' in config.config:
            preprocessing_params['n_recent'] = config.config['features'].get('n_recent', 3)
        if 'data' in config.config:
            preprocessing_params['train_end_date'] = config.config['data'].get('train_end_date')
    
    metadata.set_preprocessing_params(preprocessing_params)
    
    # 統計情報を計算
    metadata.calculate_feature_stats(df[feature_list])
    
    # 設定情報を保存
    if hasattr(config, 'config'):
        # 保存可能な形式に変換
        config_dict = {
            'features': config.config.get('features', {}),
            'lgbm': config.config.get('lgbm', {}),
            'active_experiment': config.config.get('active_experiment'),
        }
        metadata.set_config(config_dict)
    
    return metadata


if __name__ == "__main__":
    # テスト
    print("特徴量メタデータ管理システム テスト")
    
    # サンプルメタデータ作成
    metadata = FeatureMetadata()
    
    # 特徴量リスト
    features = [
        "age", "sex", "weight_carrier",
        "speed", "speed_recent_avg_3", "speed_recent_diff_3",
        "passing_gain", "style_front",
        "jockey_front_rate",
    ]
    metadata.set_features(features)
    
    # グループ
    groups = {
        'basic_features': ['age', 'sex', 'weight_carrier'],
        'speed_features': ['speed', 'speed_recent_avg_3', 'speed_recent_diff_3'],
        'passing_features': ['passing_gain', 'style_front'],
        'jockey_features': ['jockey_front_rate'],
    }
    metadata.set_feature_groups(groups)
    
    # パラメータ
    params = {
        'n_recent': 3,
        'train_end_date': '2024-06-30',
    }
    metadata.set_preprocessing_params(params)
    
    # サマリー表示
    metadata.print_summary()
    
    # 保存
    metadata.save("test_feature_metadata.json")
    
    # 読み込み
    loaded = FeatureMetadata.load("test_feature_metadata.json")
    loaded.print_summary()
