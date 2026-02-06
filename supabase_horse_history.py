"""
Supabase過去レースデータ管理システム

PostgreSQLデータベースを使用して馬の過去レースデータを管理
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import os
from supabase import create_client, Client


class SupabaseHorseHistoryDB:
    """
    Supabase（PostgreSQL）を使用した過去レース管理
    
    テーブル構造:
        race_results:
            - race_id (text)
            - race_date (date)
            - race_name (text)
            - horse_name (text)
            - rank (integer)
            - time (text)
            - time_sec (float)
            - distance (integer)
            - passing (text)
            - speed (float)
            - jockey (text)
            - weight_carrier (float)
            - horse_weight (text)
            - odds (float)
            - popularity (integer)
            - その他...
    """
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Supabaseクライアントを初期化
        
        Args:
            url: Supabase URL（環境変数 SUPABASE_URL から取得も可）
            key: Supabase API Key（環境変数 SUPABASE_KEY から取得も可）
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError(
                "Supabase URLとKeyが必要です。\n"
                "環境変数 SUPABASE_URL と SUPABASE_KEY を設定するか、\n"
                "引数で直接指定してください。"
            )
        
        try:
            self.client: Client = create_client(self.url, self.key)
            print("✅ Supabaseに接続しました")
        except Exception as e:
            raise ConnectionError(f"Supabaseへの接続に失敗: {e}")
    
    def create_table(self):
        """
        race_resultsテーブルを作成（初回のみ）
        
        Note: Supabase Web UIまたはSQLエディタで以下を実行:
        
        詳細は supabase_schema.sql を参照してください。
        
        主要カラム:
        - race_id (TEXT): レースID
        - race_date (DATE): レース日付
        - horse_name (TEXT): 馬名
        - horse_no (INTEGER): 馬番
        - rank (INTEGER): 着順
        - distance (INTEGER): 距離
        - course_type (TEXT): 芝/ダート
        - track_direction (TEXT): 右/左
        - weather (TEXT): 天候
        - track_condition (TEXT): 馬場状態
        - speed (FLOAT): スピード
        - jockey (TEXT): 騎手
        - passing_4c (FLOAT): 4コーナー通過順
        - その他多数...
        """
        print("⚠️  テーブル作成はSupabase Web UIで実行してください")
        print("    詳細: supabase_schema.sql を参照")
    
    def upload_csv_to_supabase(self, csv_path: str, batch_size: int = 1000):
        """
        CSVファイルからSupabaseにデータをアップロード
        
        Args:
            csv_path: CSVファイルのパス
            batch_size: 一度にアップロードする行数
        """
        print(f"\n📤 Supabaseにデータをアップロード中: {csv_path}")
        
        # CSVを読み込み
        df = pd.read_csv(csv_path)
        print(f"   ✓ {len(df):,}行を読み込み")
        
        # 日付型に変換
        if 'race_date' in df.columns:
            df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
            df['race_date'] = df['race_date'].dt.strftime('%Y-%m-%d')
        
        # NaNをNoneに変換（JSON互換）
        df = df.where(pd.notna(df), None)
        
        # バッチでアップロード
        total_uploaded = 0
        total_batches = (len(df) + batch_size - 1) // batch_size
        
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            records = batch.to_dict('records')
            
            try:
                self.client.table('race_results').insert(records).execute()
                total_uploaded += len(records)
                print(f"   ✓ バッチ {i // batch_size + 1}/{total_batches}: {total_uploaded:,}行アップロード")
            except Exception as e:
                print(f"   ❌ バッチ {i // batch_size + 1} エラー: {e}")
                continue
        
        print(f"✅ アップロード完了: {total_uploaded:,}行")
    
    def upload_directory_to_supabase(self, data_dir: str = "data", batch_size: int = 1000):
        """
        ディレクトリ内の全CSVファイルをSupabaseにアップロード
        
        Args:
            data_dir: CSVファイルが格納されているディレクトリ
            batch_size: バッチサイズ
        """
        from pathlib import Path
        
        print(f"\n📂 ディレクトリから一括アップロード: {data_dir}")
        
        csv_files = list(Path(data_dir).glob("*.csv"))
        
        if not csv_files:
            print(f"❌ CSVファイルが見つかりません: {data_dir}")
            return
        
        print(f"   見つかったファイル: {len(csv_files)}個")
        
        for csv_file in csv_files:
            self.upload_csv_to_supabase(str(csv_file), batch_size)
    
    def get_horse_recent_races(
        self,
        horse_name: str,
        before_date: Optional[str] = None,
        n_races: int = 3
    ) -> pd.DataFrame:
        """
        馬の直近N走を取得（Supabaseから）
        
        Args:
            horse_name: 馬名
            before_date: この日付より前のレース（YYYY-MM-DD形式）
            n_races: 取得する過去レース数
        
        Returns:
            過去レースのDataFrame
        """
        try:
            # クエリを構築
            query = self.client.table('race_results') \
                .select('*') \
                .eq('horse_name', horse_name) \
                .order('race_date', desc=True)
            
            # 日付フィルタ
            if before_date:
                query = query.lt('race_date', before_date)
            
            # 実行
            response = query.limit(n_races).execute()
            
            # DataFrameに変換
            if response.data:
                return pd.DataFrame(response.data)
            else:
                return pd.DataFrame()
        
        except Exception as e:
            print(f"   ⚠️  {horse_name}の過去レース取得エラー: {e}")
            return pd.DataFrame()
    
    def get_batch_recent_races(
        self,
        horse_names: List[str],
        before_date: Optional[str] = None,
        n_races: int = 3
    ) -> Dict[str, pd.DataFrame]:
        """
        複数の馬の直近N走を一括取得
        
        Args:
            horse_names: 馬名のリスト
            before_date: この日付より前のレース
            n_races: 取得する過去レース数
        
        Returns:
            {horse_name: DataFrame} の辞書
        """
        results = {}
        
        print(f"   📊 {len(horse_names)}頭の過去レースを取得中...")
        
        for horse_name in horse_names:
            results[horse_name] = self.get_horse_recent_races(
                horse_name, before_date, n_races
            )
        
        # 統計
        found_count = sum(1 for df in results.values() if not df.empty)
        print(f"   ✓ 過去レースが見つかった馬: {found_count}頭")
        
        return results
    
    def search_races(
        self,
        race_date_from: Optional[str] = None,
        race_date_to: Optional[str] = None,
        jockey: Optional[str] = None,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        レースを検索
        
        Args:
            race_date_from: 開始日（YYYY-MM-DD）
            race_date_to: 終了日（YYYY-MM-DD）
            jockey: 騎手名
            limit: 最大取得件数
        
        Returns:
            検索結果のDataFrame
        """
        query = self.client.table('race_results').select('*')
        
        if race_date_from:
            query = query.gte('race_date', race_date_from)
        if race_date_to:
            query = query.lte('race_date', race_date_to)
        if jockey:
            query = query.eq('jockey', jockey)
        
        response = query.limit(limit).execute()
        
        if response.data:
            return pd.DataFrame(response.data)
        else:
            return pd.DataFrame()
    
    def get_stats(self) -> Dict:
        """
        データベースの統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        try:
            # 総レコード数
            count_response = self.client.table('race_results') \
                .select('*', count='exact') \
                .execute()
            total_records = count_response.count
            
            # ユニークな馬の数（RPC関数を使用）
            # Note: 以下のSQL関数を事前にSupabaseで作成する必要があります
            # CREATE OR REPLACE FUNCTION get_unique_horses_count()
            # RETURNS bigint AS $$
            #   SELECT COUNT(DISTINCT horse_name) FROM race_results;
            # $$ LANGUAGE sql;
            
            stats = {
                'total_records': total_records,
                'status': 'connected'
            }
            
            return stats
            
        except Exception as e:
            print(f"統計情報の取得エラー: {e}")
            return {'total_records': 0, 'status': 'error'}
    
    def delete_all_data(self):
        """
        全データを削除（注意！）
        
        Warning: この操作は取り消せません
        """
        print("⚠️  全データを削除します。本当によろしいですか？")
        confirm = input("削除する場合は 'DELETE' と入力: ")
        
        if confirm == "DELETE":
            try:
                # 全削除（大量データの場合は時間がかかる）
                self.client.table('race_results').delete().neq('id', 0).execute()
                print("✅ 全データを削除しました")
            except Exception as e:
                print(f"❌ 削除エラー: {e}")
        else:
            print("キャンセルしました")


def calculate_recent_features_supabase(
    current_race_df: pd.DataFrame,
    supabase_db: SupabaseHorseHistoryDB,
    n_races: int = 3
) -> pd.DataFrame:
    """
    Supabaseから直近N走のデータを取得して特徴量を計算
    
    Args:
        current_race_df: 現在のレースデータ
        supabase_db: SupabaseHorseHistoryDB インスタンス
        n_races: 参照する過去レース数
    
    Returns:
        特徴量を追加したDataFrame
    """
    df = current_race_df.copy()
    
    # レースの日付を取得
    race_date = None
    if 'race_date' in df.columns and not df['race_date'].isna().all():
        race_date = pd.to_datetime(df['race_date'].iloc[0]).strftime('%Y-%m-%d')
    
    print(f"\n🔍 Supabaseから直近{n_races}走を取得中...")
    
    # 各馬の過去レースを取得
    horse_names = df['horse_name'].unique().tolist()
    past_races_dict = supabase_db.get_batch_recent_races(
        horse_names, before_date=race_date, n_races=n_races
    )
    
    # 特徴量を計算
    features_list = []
    
    for idx, row in df.iterrows():
        horse_name = row['horse_name']
        past_races = past_races_dict.get(horse_name, pd.DataFrame())
        
        features = {
            'horse_name': horse_name,
            'past_races_count': len(past_races),
        }
        
        if not past_races.empty:
            # 平均着順
            if 'rank' in past_races.columns:
                features['recent_avg_rank'] = past_races['rank'].mean()
                features['recent_best_rank'] = past_races['rank'].min()
            
            # 平均タイム
            if 'time_sec' in past_races.columns:
                features['recent_avg_time_sec'] = past_races['time_sec'].mean()
            
            # 平均スピード
            if 'speed' in past_races.columns:
                features['recent_avg_speed'] = past_races['speed'].mean()
            
            # 勝率
            if 'rank' in past_races.columns:
                features['recent_win_rate'] = (past_races['rank'] == 1).mean()
                features['recent_top3_rate'] = (past_races['rank'] <= 3).mean()
            
            # 連続出走日数
            if 'race_date' in past_races.columns and race_date:
                last_race_date = pd.to_datetime(past_races['race_date'].iloc[0])
                current_date = pd.to_datetime(race_date)
                days_since_last = (current_date - last_race_date).days
                features['days_since_last_race'] = days_since_last
            
            # 脚質
            if 'passing_4c' in past_races.columns:
                features['recent_avg_pos_4c'] = past_races['passing_4c'].mean()
        
        features_list.append(features)
    
    # DataFrameに変換
    features_df = pd.DataFrame(features_list)
    
    # マージ
    df = df.merge(features_df, on='horse_name', how='left')
    
    # 欠損値を埋める
    for col in features_df.columns:
        if col != 'horse_name' and col in df.columns:
            df[col] = df[col].fillna(0)
    
    print(f"   ✓ 追加された特徴量: {len(features_df.columns) - 1}個")
    
    return df


if __name__ == "__main__":
    # テスト・セットアップ
    print("="*80)
    print("🏇 Supabase過去レースデータ管理システム")
    print("="*80)
    
    # 環境変数の確認
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("\n⚠️  環境変数を設定してください:")
        print("   export SUPABASE_URL='your-project-url'")
        print("   export SUPABASE_KEY='your-anon-key'")
        print("\n   または .env ファイルに記載:")
        print("   SUPABASE_URL=your-project-url")
        print("   SUPABASE_KEY=your-anon-key")
    else:
        try:
            # Supabaseに接続
            db = SupabaseHorseHistoryDB()
            
            # 統計情報を表示
            stats = db.get_stats()
            print(f"\n📊 データベース統計:")
            print(f"   総レコード数: {stats.get('total_records', 0):,}")
            print(f"   ステータス: {stats.get('status', 'unknown')}")
            
            print("\n💡 使用方法:")
            print("   # CSVをアップロード")
            print("   db.upload_csv_to_supabase('data/race_2019.csv')")
            print("")
            print("   # ディレクトリから一括アップロード")
            print("   db.upload_directory_to_supabase('data')")
            print("")
            print("   # 馬の過去レースを取得")
            print("   past = db.get_horse_recent_races('ドウデュース', n_races=3)")
            
        except Exception as e:
            print(f"\n❌ エラー: {e}")
