"""
競馬予測モデル オールインワンスクリプト

データの前処理から学習まで一気に実行します。

使用方法:
    python run_all.py horse_race_data_2019.csv
    python run_all.py data/race_*.csv
"""

import sys
import pandas as pd
from pathlib import Path
import shutil
import glob

# 自作モジュール
from preprocess_race_data import preprocess_race_data


def setup_environment():
    """環境のセットアップ"""
    print("\n" + "="*80)
    print("🚀 競馬予測モデル オールインワンスクリプト")
    print("="*80)
    
    # 必要なディレクトリを作成
    dirs = ["data", "outputs"]
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    
    print("\n✓ 環境セットアップ完了")


def preprocess_files(input_files):
    """
    複数のCSVファイルを前処理
    
    Args:
        input_files: 入力ファイルのリスト
    
    Returns:
        処理済みファイルのリスト
    """
    print("\n" + "="*80)
    print("📊 STEP 1: データ前処理")
    print("="*80)
    
    processed_files = []
    
    for i, input_file in enumerate(input_files, 1):
        print(f"\n[{i}/{len(input_files)}] 処理中: {Path(input_file).name}")
        print("-" * 80)
        
        try:
            # 出力先をdataフォルダに
            input_path = Path(input_file)
            output_file = Path("data") / f"{input_path.stem}_processed.csv"
            
            # 前処理実行
            df = preprocess_race_data(input_file, str(output_file))
            processed_files.append(str(output_file))
            
            print(f"✓ 保存: {output_file}")
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            continue
    
    print("\n" + "="*80)
    print(f"✅ 前処理完了: {len(processed_files)}ファイル")
    print("="*80)
    
    return processed_files


def check_processed_data():
    """処理済みデータの確認"""
    print("\n" + "="*80)
    print("🔍 処理済みデータの確認")
    print("="*80)
    
    data_files = list(Path("data").glob("*_processed.csv"))
    
    if not data_files:
        print("❌ dataフォルダに処理済みファイルがありません")
        return False
    
    print(f"\n処理済みファイル: {len(data_files)}個")
    
    total_rows = 0
    total_races = 0
    
    for f in data_files:
        df = pd.read_csv(f)
        rows = len(df)
        races = df['race_id'].nunique() if 'race_id' in df.columns else 0
        total_rows += rows
        total_races += races
        
        print(f"  ✓ {f.name:40s} {rows:>8,}行 / {races:>6,}レース")
    
    print(f"\n合計: {total_rows:,}行 / {total_races:,}レース")
    
    # 必須カラムのチェック
    print("\n必須カラムの確認:")
    df_sample = pd.read_csv(data_files[0])
    required_cols = ["race_id", "horse_name", "rank"]
    recommended_cols = ["race_date", "distance", "time", "passing", "jockey"]
    
    for col in required_cols:
        status = "✓" if col in df_sample.columns else "❌"
        print(f"  {status} {col}")
    
    print("\n推奨カラム:")
    for col in recommended_cols:
        status = "✓" if col in df_sample.columns else "⚠️"
        print(f"  {status} {col}")
    
    return True


def run_training():
    """学習スクリプトの実行"""
    print("\n" + "="*80)
    print("🎓 STEP 2: モデル学習")
    print("="*80)
    
    try:
        # train_lgbm_ranker_improved.py のmain()を直接実行
        from train_lgbm_ranker_improved import main as train_main
        
        print("\n学習を開始します...")
        train_main()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 学習中にエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return False


def display_results():
    """結果の表示"""
    print("\n" + "="*80)
    print("📊 実行結果サマリー")
    print("="*80)
    
    # モデルファイルの確認
    model_file = Path("outputs/horse_racing_lgbm_ranker.txt")
    if model_file.exists():
        print(f"✅ モデルファイル: {model_file}")
        print(f"   サイズ: {model_file.stat().st_size / 1024:.1f} KB")
    else:
        print("❌ モデルファイルが見つかりません")
    
    # 特徴量重要度の確認
    importance_file = Path("outputs/feature_importance.csv")
    if importance_file.exists():
        print(f"\n📊 特徴量重要度 (Top 10)")
        print("-" * 80)
        df_imp = pd.read_csv(importance_file)
        for idx, row in df_imp.head(10).iterrows():
            print(f"  {idx+1:2d}. {row['feature']:40s} {row['importance']:>10.1f}")
    
    # 評価指標の確認
    metrics_file = Path("outputs/training_metrics.csv")
    if metrics_file.exists():
        df_metrics = pd.read_csv(metrics_file)
        hit_rate = (df_metrics['hit_top3'] > 0).mean()
        print(f"\n🎯 予測精度")
        print("-" * 80)
        print(f"  Top3的中率: {hit_rate:.2%}")
        print(f"  平均的中頭数: {df_metrics['hit_top3'].mean():.2f}")
    
    print("\n" + "="*80)
    print("✅ すべての処理が完了しました！")
    print("="*80)
    
    print("\n次のステップ:")
    print("  1. 特徴量重要度を確認: outputs/feature_importance.csv")
    print("  2. 予測を実行: python predict.py <新しいレースデータ.csv>")


def main(input_patterns):
    """
    メイン実行関数
    
    Args:
        input_patterns: 入力ファイルのパターンリスト
    """
    try:
        # 環境セットアップ
        setup_environment()
        
        # ファイルリストの取得
        input_files = []
        for pattern in input_patterns:
            if '*' in pattern or '?' in pattern:
                matched = glob.glob(pattern)
                input_files.extend(matched)
            else:
                if Path(pattern).exists():
                    input_files.append(pattern)
                else:
                    print(f"⚠️  ファイルが見つかりません: {pattern}")
        
        if not input_files:
            print("❌ 処理対象のファイルがありません")
            print("\n使用方法:")
            print("  python run_all.py horse_race_data_2019.csv")
            print("  python run_all.py data/race_*.csv")
            return False
        
        # 重複削除
        input_files = list(set(input_files))
        input_files.sort()
        
        print(f"\n📋 処理対象: {len(input_files)}ファイル")
        for f in input_files:
            print(f"  - {f}")
        
        # STEP 1: 前処理
        processed_files = preprocess_files(input_files)
        
        if not processed_files:
            print("❌ 前処理に失敗しました")
            return False
        
        # データ確認
        if not check_processed_data():
            return False
        
        # STEP 2: 学習
        success = run_training()
        
        if not success:
            print("❌ 学習に失敗しました")
            return False
        
        # 結果表示
        display_results()
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠️  処理が中断されました")
        return False
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=" * 80)
        print("🏇 競馬予測モデル オールインワンスクリプト")
        print("=" * 80)
        print("\n使用方法:")
        print("  python run_all.py <CSVファイル> [<CSVファイル2> ...]")
        print("\n例:")
        print("  python run_all.py horse_race_data_2019.csv")
        print("  python run_all.py data/race_2019.csv data/race_2020.csv")
        print("  python run_all.py data/race_*.csv")
        print("\n処理内容:")
        print("  1. データ前処理（race_detailsから距離等を抽出）")
        print("  2. 特徴量生成")
        print("  3. モデル学習")
        print("  4. 結果の保存と表示")
        print("\n出力:")
        print("  - data/*_processed.csv (前処理済みデータ)")
        print("  - outputs/horse_racing_lgbm_ranker.txt (モデル)")
        print("  - outputs/feature_importance.csv (特徴量重要度)")
        print("=" * 80)
        sys.exit(1)
    
    patterns = sys.argv[1:]
    success = main(patterns)
    
    sys.exit(0 if success else 1)
