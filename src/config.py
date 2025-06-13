import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# プロジェクトのルートディレクトリ
PROJECT_ROOT = Path(__file__).parent.parent

# ディレクトリ設定
DATA_DIR = PROJECT_ROOT / 'data'
LOGS_DIR = PROJECT_ROOT / 'logs'

# ディレクトリが存在しない場合は作成
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Google Sheets設定
GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv('GOOGLE_SHEETS_CREDENTIALS_PATH', str(DATA_DIR / 'credentials.json'))
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '')
INPUT_SHEET_NAME = os.getenv('INPUT_SHEET_NAME', 'Sheet1')
OUTPUT_SHEET_NAME = os.getenv('OUTPUT_SHEET_NAME', 'Rankings')

# スクレイピング設定
MAX_SEARCH_PAGES = int(os.getenv('MAX_SEARCH_PAGES', '5'))  # 最大検索ページ数
HEADLESS_MODE = os.getenv('HEADLESS_MODE', 'True').lower() == 'true'  # ヘッドレスモード
REQUEST_DELAY_MIN = float(os.getenv('REQUEST_DELAY_MIN', '2'))  # 最小リクエスト間隔（秒）
REQUEST_DELAY_MAX = float(os.getenv('REQUEST_DELAY_MAX', '5'))  # 最大リクエスト間隔（秒）

# ログ設定
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = LOGS_DIR / 'search_ranking_monitor.log'

# 実行設定
SKIP_IF_ALREADY_RUN_TODAY = os.getenv('SKIP_IF_ALREADY_RUN_TODAY', 'True').lower() == 'true'  # 当日既に実行済みの場合スキップ

# ChromeDriver設定
CHROME_DRIVER_PATH = os.getenv('CHROME_DRIVER_PATH', None)  # Noneの場合は自動ダウンロード