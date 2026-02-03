#!/bin/bash

# 競馬予測モデル 簡単実行スクリプト
# 
# 使用方法:
#   bash quick_start.sh horse_race_data_2019.csv
#   bash quick_start.sh data/*.csv

set -e  # エラーで停止

echo "================================================================================================"
echo "🏇 競馬予測モデル クイックスタート"
echo "================================================================================================"
echo ""

# 引数チェック
if [ $# -eq 0 ]; then
    echo "使用方法: bash quick_start.sh <CSVファイル>"
    echo ""
    echo "例:"
    echo "  bash quick_start.sh horse_race_data_2019.csv"
    echo "  bash quick_start.sh data/race_*.csv"
    echo ""
    exit 1
fi

# Pythonのチェック
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3が見つかりません"
    exit 1
fi

echo "✓ Python3: $(python3 --version)"
echo ""

# 必要なライブラリのチェック
echo "📦 必要なライブラリをチェック中..."
python3 -c "import pandas" 2>/dev/null || { echo "❌ pandasがインストールされていません。pip install pandas を実行してください"; exit 1; }
python3 -c "import numpy" 2>/dev/null || { echo "❌ numpyがインストールされていません。pip install numpy を実行してください"; exit 1; }
python3 -c "import lightgbm" 2>/dev/null || { echo "❌ lightgbmがインストールされていません。pip install lightgbm を実行してください"; exit 1; }
echo "✓ すべてのライブラリがインストール済み"
echo ""

# オールインワンスクリプトの実行
echo "🚀 処理を開始します..."
echo ""
python3 run_all.py "$@"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo ""
    echo "================================================================================================"
    echo "✅ 完了！ outputs/ フォルダを確認してください"
    echo "================================================================================================"
else
    echo ""
    echo "================================================================================================"
    echo "❌ エラーが発生しました"
    echo "================================================================================================"
fi

exit $exit_code
