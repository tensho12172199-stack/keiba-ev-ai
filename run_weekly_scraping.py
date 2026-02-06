"""
競馬レーススクレイピング 定期実行スクリプト

GitHub Actionsで毎週日曜日に実行する想定
"""

import sys
import os
from datetime import datetime
from scrape_improved import main as scrape_main

def run_weekly_scraping():
    """週次スクレイピングを実行"""
    print("="*80)
    print(f"🗓️  定期スクレイピング実行: {datetime.now()}")
    print("="*80)
    
    try:
        # スクレイピング実行
        scrape_main()
        
        print("\n✅ 定期スクレイピング成功")
        return 0
    
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = run_weekly_scraping()
    sys.exit(exit_code)
