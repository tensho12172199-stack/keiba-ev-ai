"""
複数の競馬データCSVファイルを一括前処理するスクリプト

使用方法:
    python batch_preprocess.py data/*.csv
    python batch_preprocess.py horse_race_data_*.csv
"""

import sys
from pathlib import Path
from preprocess_race_data import preprocess_race_data


def batch_preprocess(file_patterns):
    """
    複数のCSVファイルを一括前処理
    
    Args:
        file_patterns: ファイルパターンのリスト
    """
    print("\n" + "="*80)
    print("📦 バッチ前処理スクリプト")
    print("="*80)
    
    # ファイルパターンから実際のファイルリストを取得
    all_files = []
    for pattern in file_patterns:
        # パターンマッチング
        if '*' in pattern or '?' in pattern:
            from glob import glob
            matched_files = glob(pattern)
            all_files.extend(matched_files)
        else:
            # 通常のファイルパス
            if Path(pattern).exists():
                all_files.append(pattern)
            else:
                print(f"⚠️  ファイルが見つかりません: {pattern}")
    
    if not all_files:
        print("❌ 処理対象のファイルが見つかりません")
        return
    
    # 重複削除
    all_files = list(set(all_files))
    all_files.sort()
    
    print(f"\n📋 処理対象ファイル: {len(all_files)}個")
    for i, f in enumerate(all_files, 1):
        print(f"   {i}. {f}")
    
    # 各ファイルを処理
    success_count = 0
    failed_files = []
    
    for i, input_file in enumerate(all_files, 1):
        print(f"\n{'='*80}")
        print(f"処理中 ({i}/{len(all_files)}): {Path(input_file).name}")
        print('='*80)
        
        try:
            # 出力ファイル名の生成
            input_path = Path(input_file)
            output_file = input_path.parent / f"{input_path.stem}_processed.csv"
            
            # 前処理実行
            preprocess_race_data(input_file, output_file)
            success_count += 1
            
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            failed_files.append(input_file)
    
    # 結果サマリー
    print("\n" + "="*80)
    print("📊 バッチ処理結果")
    print("="*80)
    print(f"   処理対象: {len(all_files)}ファイル")
    print(f"   成功: {success_count}ファイル ✅")
    print(f"   失敗: {len(failed_files)}ファイル ❌")
    
    if failed_files:
        print("\n失敗したファイル:")
        for f in failed_files:
            print(f"   - {f}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python batch_preprocess.py <ファイルパターン>")
        print("\n例:")
        print("  python batch_preprocess.py data/*.csv")
        print("  python batch_preprocess.py horse_race_data_2019.csv horse_race_data_2020.csv")
        print("  python batch_preprocess.py horse_race_data_*.csv")
        sys.exit(1)
    
    # ファイルパターンを取得（最初の引数はスクリプト名なので除外）
    patterns = sys.argv[1:]
    
    batch_preprocess(patterns)
