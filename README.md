# Amazon・楽天検索順位モニタリングツール

このツールは、Amazon.co.jpと楽天市場での商品の検索順位を自動的に取得し、Googleスプレッドシートに記録するPythonスクリプトです。

## 主な機能

- Googleスプレッドシートから商品情報とキーワードを読み込み
- Amazon.co.jpでのオーガニック検索順位を取得（広告除外）
- 楽天市場での検索順位を取得
- 結果をGoogleスプレッドシートに自動保存
- 1日1回の自動実行に対応

## 必要な環境

- Python 3.8以上
- Google Chrome（最新版推奨）
- Google Cloud Platform（GCP）のサービスアカウント

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone [repository-url]
cd search-ranking-monitor
```

### 2. Python環境のセットアップ

```bash
# 仮想環境の作成（推奨）
python -m venv venv

# 仮想環境の有効化
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 必要なパッケージのインストール
pip install -r requirements.txt
```

### 3. Google Sheets APIの設定

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成または既存のプロジェクトを選択
3. 「APIとサービス」→「ライブラリ」から「Google Sheets API」を有効化
4. 「APIとサービス」→「認証情報」→「サービスアカウントを作成」
5. サービスアカウントのJSON鍵ファイルをダウンロード
6. ダウンロードしたJSONファイルを `data/credentials.json` として保存

### 4. Googleスプレッドシートの準備

1. Googleスプレッドシートを新規作成
2. サービスアカウントのメールアドレス（JSONファイル内の`client_email`）に編集権限を付与
3. 入力シート（デフォルト: Sheet1）に以下の形式でデータを入力：

| SKU名 | ASIN | 楽天URL | KW1 | KW2 | KW3 | ... |
|-------|------|---------|-----|-----|-----|-----|
| 商品A | B01XXXXX | https://item.rakuten.co.jp/... | 化粧水 | スキンケア | 保湿 | ... |

### 5. 環境変数の設定

```bash
# .env.exampleをコピーして.envを作成
cp .env.example .env
```

`.env`ファイルを編集：

```
# Google Sheets設定
GOOGLE_SHEETS_CREDENTIALS_PATH=data/credentials.json
SPREADSHEET_ID=your-spreadsheet-id-here  # スプレッドシートのIDを入力
INPUT_SHEET_NAME=Sheet1
OUTPUT_SHEET_NAME=Rankings

# スクレイピング設定
MAX_SEARCH_PAGES=5  # 最大検索ページ数
HEADLESS_MODE=True  # ブラウザを表示しない
REQUEST_DELAY_MIN=2  # 最小待機時間（秒）
REQUEST_DELAY_MAX=5  # 最大待機時間（秒）
```

スプレッドシートIDは、スプレッドシートのURLから取得できます：
`https://docs.google.com/spreadsheets/d/[SPREADSHEET_ID]/edit`

## 実行方法

### 手動実行

```bash
python src/main.py
```

### 定期実行の設定

#### Linux/Mac (cron)

```bash
# crontabを編集
crontab -e

# 毎日午前9時に実行する例
0 9 * * * cd /path/to/search-ranking-monitor && /path/to/venv/bin/python src/main.py
```

#### Windows (タスクスケジューラ)

1. タスクスケジューラを開く
2. 「基本タスクの作成」を選択
3. トリガー: 毎日
4. 操作: プログラムの開始
   - プログラム: `C:\path\to\venv\Scripts\python.exe`
   - 引数: `src/main.py`
   - 開始: `C:\path\to\search-ranking-monitor`

## 出力形式

結果は指定したスプレッドシートの「Rankings」シートに以下の形式で保存されます：

| 日付 | SKU名 | キーワード | Amazon順位 | 楽天順位 |
|------|-------|-----------|------------|----------|
| 2024-01-15 | 商品A | 化粧水 | 3 | 5 |
| 2024-01-15 | 商品A | スキンケア | 15 | 圏外 |

- 順位は広告を除外したオーガニック順位（Amazonのみ）
- 検索結果に表示されない場合は「圏外」と記録

## トラブルシューティング

### ChromeDriverのエラー

自動的にChromeDriverがダウンロードされますが、問題が発生する場合：

1. Chrome のバージョンを確認
2. 対応する ChromeDriver を[公式サイト](https://chromedriver.chromium.org/)からダウンロード
3. `.env`ファイルに`CHROME_DRIVER_PATH`を設定

### 認証エラー

- サービスアカウントのメールアドレスがスプレッドシートに編集権限を持っているか確認
- `credentials.json`のパスが正しいか確認
- Google Sheets APIが有効になっているか確認

### 検索結果が取得できない

- `HEADLESS_MODE=False`に設定してブラウザの動作を確認
- リクエスト間隔を長めに設定（`REQUEST_DELAY_MIN/MAX`）
- ログファイル（`logs/search_ranking_monitor.log`）を確認

## ログ

実行ログは`logs/search_ranking_monitor.log`に保存されます。エラーの詳細はこのファイルで確認できます。

## 注意事項

- このツールはWebスクレイピングを行うため、サイトの利用規約を確認してください
- 過度なアクセスを避けるため、適切な待機時間を設定してください
- 検索結果のHTML構造が変更された場合、スクレイピング部分の修正が必要になる可能性があります