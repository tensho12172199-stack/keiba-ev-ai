# 🤖 競馬レース自動スクレイピングガイド

## 🎯 目的

毎週自動で最新のレース結果をSupabaseに保存し、予測システムを常に最新の状態に保ちます。

---

## ✨ 主な機能

### 1. スクレイピング済みレースの自動スキップ

```python
# 取得済みレースIDをDBから読み込み
done_ids = load_done_ids()

# スキップ判定
if race_id in done_ids:
    continue  # すでに取得済み
```

### 2. 最新レースまで自動取得

```python
# 現在の年月から自動判定
start_year, end_year = get_date_range()

# 過去5年分を取得
# 例: 2024年2月 → 2020年〜2024年
```

### 3. 連続で見つからないレースをスキップ

```python
# 連続で5レース見つからなければ次の開催へ
if consecutive_not_found >= 5:
    break
```

---

## 📁 必要なファイル

### スクレイピング用

```
scraping/
├── scrape_improved.py           # メインスクレイピングスクリプト
├── run_weekly_scraping.py       # 定期実行用ラッパー
└── .github/
    └── workflows/
        └── scraping.yml         # GitHub Actions設定
```

---

## 🚀 セットアップ（GitHub Actions）

### ステップ1: ファイルを配置

```bash
# リポジトリルート
your-repo/
├── scrape_improved.py
├── run_weekly_scraping.py
└── .github/
    └── workflows/
        └── scraping.yml
```

### ステップ2: GitHubにプッシュ

```bash
git add scrape_improved.py
git add run_weekly_scraping.py
git add .github/workflows/scraping.yml
git commit -m "Add weekly scraping automation"
git push
```

### ステップ3: Secretsを設定

GitHub → リポジトリ → Settings → Secrets and variables → Actions

**New repository secret**をクリック:

```
Name: DB_URL
Value: postgresql://user:password@host:5432/database?sslmode=require
```

**DB_URLの取得方法:**

Supabase Dashboard → Settings → Database → Connection string → URI

例:
```
postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:5432/postgres
```

### ステップ4: 実行スケジュールの確認

`.github/workflows/scraping.yml`:

```yaml
on:
  schedule:
    - cron: '0 23 * * 0'  # 毎週日曜日23:00 UTC (月曜日8:00 JST)
```

**カスタマイズ例:**

```yaml
# 毎週土曜日22:00 UTC (日曜日7:00 JST)
- cron: '0 22 * * 6'

# 毎日深夜0:00 UTC (9:00 JST)
- cron: '0 0 * * *'

# 毎週月曜日と木曜日の9:00 UTC (18:00 JST)
- cron: '0 9 * * 1,4'
```

---

## 💻 ローカルで実行

### 初回セットアップ

```bash
# 依存関係をインストール
pip install requests beautifulsoup4 psycopg2-binary lxml

# 環境変数を設定
export DB_URL="postgresql://postgres.xxxxx:..."
```

### 実行

```bash
# 通常実行
python scrape_improved.py

# 定期実行スクリプト経由
python run_weekly_scraping.py
```

**出力例:**
```
================================================================================
🏇 競馬レース結果スクレイピング開始
================================================================================
✓ 取得済みレース数: 15234
📅 取得期間: 2020年 〜 2024年

📆 2024年のレースを取得中...
✓ 202405030801: 16頭の結果を保存
✓ 202405030802: 15頭の結果を保存
...

================================================================================
✅ スクレイピング完了
================================================================================
📊 統計:
   新規取得: 127レース
   スキップ: 15234レース
   合計取得済み: 15361レース
================================================================================
```

---

## 🔍 動作確認

### GitHub Actionsのログを確認

1. GitHub → リポジトリ → Actions
2. 「Weekly Race Scraping」をクリック
3. 最新の実行をクリック
4. ログを確認

### 手動実行

1. GitHub → Actions → 「Weekly Race Scraping」
2. 「Run workflow」をクリック
3. 「Run workflow」ボタン

---

## 📊 取得されるデータ

### race_resultsテーブル

| カラム | 型 | 説明 |
|--------|-----|------|
| race_id | TEXT | レースID |
| race_name | TEXT | レース名 |
| rank | INTEGER | 着順 |
| waku_no | INTEGER | 枠番 |
| horse_no | INTEGER | 馬番 |
| horse_name | TEXT | 馬名 |
| sex_age | TEXT | 性齢 |
| weight_carrier | FLOAT | 斤量 |
| jockey | TEXT | 騎手 |
| time_sec | FLOAT | タイム（秒） |
| margin | TEXT | 着差 |
| passing | TEXT | 通過順 |
| last_3f | FLOAT | 上がり3F |
| odds | FLOAT | 単勝オッズ |
| popularity | INTEGER | 人気 |
| horse_weight | INTEGER | 馬体重 |
| race_info | TEXT | レース条件 |
| race_date | DATE | レース日付 |
| distance | INTEGER | 距離 |
| course_type | TEXT | 芝/ダート |
| track_direction | TEXT | 右/左 |
| weather | TEXT | 天候 |
| track_condition | TEXT | 馬場状態 |

---

## 🔧 カスタマイズ

### 取得期間を変更

**scrape_improved.py:**

```python
def get_date_range() -> Tuple[int, int]:
    current_year = datetime.now().year
    
    # 過去10年分に変更
    start_year = current_year - 9  # 5 → 9
    end_year = current_year
    
    return start_year, end_year
```

### スリープ時間を調整

```python
# レート制限対策
time.sleep(1)  # 1秒 → 0.5秒に短縮
```

### 連続エラーの閾値を変更

```python
# 連続で5レース → 10レースに変更
if consecutive_not_found >= 10:
    break
```

---

## ⚠️ 注意事項

### 1. netkeiba.comの利用規約を遵守

- 過度なアクセスは避ける
- User-Agentを設定する
- スリープ時間を設ける

### 2. DB接続のタイムアウト

```python
# 接続タイムアウトを設定済み
psycopg2.connect(DB_URL, connect_timeout=10)
```

### 3. エラーハンドリング

```python
try:
    rows = scrape_race(race_id)
except Exception as e:
    print(f"⚠️  {race_id}: エラー - {e}")
    continue  # 次のレースへ
```

---

## 🐛 トラブルシューティング

### Q: GitHub Actionsでエラーが出る

**確認:**
1. Secretsが設定されているか
2. DB_URLが正しいか
3. ログで詳細を確認

**解決:**
```bash
# ログを確認
GitHub → Actions → 最新の実行 → ログ
```

### Q: スクレイピングが遅い

**原因:**
- スリープ時間が長い
- 取得期間が広すぎる

**解決:**
```python
# スリープ時間を短縮
time.sleep(0.5)  # 1 → 0.5秒

# 期間を短縮
start_year = current_year - 2  # 過去3年分のみ
```

### Q: 重複データが保存される

**確認:**
```sql
-- Supabase SQL Editor
SELECT race_id, horse_no, COUNT(*)
FROM race_results
GROUP BY race_id, horse_no
HAVING COUNT(*) > 1;
```

**解決:**

すでに`ON CONFLICT`で対応済み：
```sql
ON CONFLICT (race_id, horse_no)
DO UPDATE SET ...
```

### Q: 最新レースが取得できない

**原因:**
- レースがまだ実施されていない
- レース結果が公開されていない

**確認:**
```python
# 手動で確認
race_id = "202412070811"  # 最新のレースID
rows = scrape_race(race_id)
print(rows)
```

---

## 📈 モニタリング

### 取得状況の確認

```sql
-- Supabase SQL Editor

-- 年別レース数
SELECT 
    EXTRACT(YEAR FROM race_date) as year,
    COUNT(DISTINCT race_id) as race_count
FROM race_results
GROUP BY year
ORDER BY year DESC;

-- 最新レース
SELECT race_id, race_name, race_date
FROM race_results
ORDER BY race_date DESC
LIMIT 10;

-- 競馬場別レース数
SELECT 
    SUBSTRING(race_id, 5, 2) as course_code,
    COUNT(DISTINCT race_id) as race_count
FROM race_results
GROUP BY course_code
ORDER BY course_code;
```

---

## 🎯 まとめ

### 自動化の流れ

1. **毎週日曜日23:00 UTC** - GitHub Actions起動
2. **取得済みレースをロード** - Supabaseから
3. **最新レースまで取得** - スキップ機能あり
4. **Supabaseに保存** - 自動的に追加
5. **完了通知** - ログで確認

### 手動実行も可能

```bash
# ローカルで実行
python scrape_improved.py

# GitHub Actionsで手動実行
Actions → Run workflow
```

これで、毎週自動的に最新レースが取得され、予測システムが常に最新データで動作します！🎊
