@echo off
REM 競馬予測モデル 簡単実行スクリプト (Windows)
REM 
REM 使用方法:
REM   quick_start.bat horse_race_data_2019.csv
REM   quick_start.bat data\*.csv

echo ================================================================================================
echo 🏇 競馬予測モデル クイックスタート
echo ================================================================================================
echo.

REM 引数チェック
if "%~1"=="" (
    echo 使用方法: quick_start.bat ^<CSVファイル^>
    echo.
    echo 例:
    echo   quick_start.bat horse_race_data_2019.csv
    echo   quick_start.bat data\race_*.csv
    echo.
    exit /b 1
)

REM Pythonのチェック
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Pythonが見つかりません
    exit /b 1
)

echo ✓ Python: 
python --version
echo.

REM 必要なライブラリのチェック
echo 📦 必要なライブラリをチェック中...
python -c "import pandas" 2>nul
if errorlevel 1 (
    echo ❌ pandasがインストールされていません。pip install pandas を実行してください
    exit /b 1
)
python -c "import numpy" 2>nul
if errorlevel 1 (
    echo ❌ numpyがインストールされていません。pip install numpy を実行してください
    exit /b 1
)
python -c "import lightgbm" 2>nul
if errorlevel 1 (
    echo ❌ lightgbmがインストールされていません。pip install lightgbm を実行してください
    exit /b 1
)
echo ✓ すべてのライブラリがインストール済み
echo.

REM オールインワンスクリプトの実行
echo 🚀 処理を開始します...
echo.
python run_all.py %*

if errorlevel 1 (
    echo.
    echo ================================================================================================
    echo ❌ エラーが発生しました
    echo ================================================================================================
    exit /b 1
) else (
    echo.
    echo ================================================================================================
    echo ✅ 完了！ outputs\ フォルダを確認してください
    echo ================================================================================================
    exit /b 0
)
