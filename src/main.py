#!/usr/bin/env python3
"""
Amazon・楽天検索順位モニタリングツール
メインスクリプト
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import *
from src.google_sheets import GoogleSheetsClient
from src.amazon_scraper import AmazonScraper
from src.rakuten_scraper import RakutenScraper


def setup_logging():
    """ログ設定を初期化"""
    logger.remove()  # デフォルトハンドラを削除
    
    # コンソール出力
    logger.add(
        sys.stdout,
        level=LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{message}</cyan>"
    )
    
    # ファイル出力
    logger.add(
        LOG_FILE,
        level=LOG_LEVEL,
        rotation="1 week",
        retention="1 month",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )


def check_already_run_today(sheets_client: GoogleSheetsClient) -> bool:
    """
    本日既に実行済みかチェック
    
    Args:
        sheets_client: Google Sheetsクライアント
        
    Returns:
        実行済みの場合True
    """
    if not SKIP_IF_ALREADY_RUN_TODAY:
        return False
    
    today = datetime.now().strftime('%Y-%m-%d')
    last_execution_date = sheets_client.get_last_execution_date(OUTPUT_SHEET_NAME)
    
    if last_execution_date == today:
        logger.info(f"本日（{today}）は既に実行済みです")
        return True
    
    return False


def search_rankings(sku_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    SKUに対して全キーワードの検索を実行
    
    Args:
        sku_data: SKU情報（sku_name, asin, rakuten_url, keywords）
        
    Returns:
        ランキング結果のリスト
    """
    results = []
    today = datetime.now().strftime('%Y-%m-%d')
    
    logger.info(f"=== {sku_data['sku_name']} の検索開始 ===")
    
    # Amazon検索
    if sku_data['asin']:
        logger.info(f"Amazon検索開始: ASIN={sku_data['asin']}")
        try:
            with AmazonScraper(headless=HEADLESS_MODE) as amazon:
                amazon_results = amazon.search_multiple_keywords(
                    sku_data['keywords'],
                    sku_data['asin'],
                    MAX_SEARCH_PAGES
                )
        except Exception as e:
            logger.error(f"Amazon検索エラー: {e}")
            amazon_results = {kw: None for kw in sku_data['keywords']}
    else:
        logger.warning(f"ASINが設定されていません: {sku_data['sku_name']}")
        amazon_results = {kw: None for kw in sku_data['keywords']}
    
    # 楽天検索
    if sku_data['rakuten_url']:
        logger.info(f"楽天検索開始: URL={sku_data['rakuten_url']}")
        try:
            with RakutenScraper(headless=HEADLESS_MODE) as rakuten:
                rakuten_results = rakuten.search_multiple_keywords(
                    sku_data['keywords'],
                    sku_data['rakuten_url'],
                    MAX_SEARCH_PAGES
                )
        except Exception as e:
            logger.error(f"楽天検索エラー: {e}")
            rakuten_results = {kw: None for kw in sku_data['keywords']}
    else:
        logger.warning(f"楽天URLが設定されていません: {sku_data['sku_name']}")
        rakuten_results = {kw: None for kw in sku_data['keywords']}
    
    # 結果を整形
    for keyword in sku_data['keywords']:
        result = {
            'date': today,
            'sku_name': sku_data['sku_name'],
            'keyword': keyword,
            'amazon_rank': amazon_results.get(keyword),
            'rakuten_rank': rakuten_results.get(keyword)
        }
        results.append(result)
        
        logger.info(
            f"  {keyword}: "
            f"Amazon={result['amazon_rank'] or '圏外'}, "
            f"楽天={result['rakuten_rank'] or '圏外'}"
        )
    
    return results


def main():
    """メイン処理"""
    setup_logging()
    logger.info("検索順位モニタリングツールを開始します")
    
    # 設定チェック
    if not SPREADSHEET_ID:
        logger.error("SPREADSHEET_IDが設定されていません。.envファイルを確認してください。")
        sys.exit(1)
    
    if not Path(GOOGLE_SHEETS_CREDENTIALS_PATH).exists():
        logger.error(f"認証情報ファイルが見つかりません: {GOOGLE_SHEETS_CREDENTIALS_PATH}")
        sys.exit(1)
    
    try:
        # Google Sheetsクライアントを初期化
        sheets_client = GoogleSheetsClient(
            GOOGLE_SHEETS_CREDENTIALS_PATH,
            SPREADSHEET_ID
        )
        
        # 本日既に実行済みかチェック
        if check_already_run_today(sheets_client):
            return
        
        # 入力データを読み取る
        logger.info("入力データを読み取っています...")
        sku_list = sheets_client.read_input_data(INPUT_SHEET_NAME)
        
        if not sku_list:
            logger.warning("処理対象のSKUがありません")
            return
        
        logger.info(f"{len(sku_list)} 個のSKUを処理します")
        
        # 全SKUに対して検索を実行
        all_results = []
        for sku_data in sku_list:
            results = search_rankings(sku_data)
            all_results.extend(results)
        
        # 結果をスプレッドシートに書き込む
        if all_results:
            logger.info("結果をスプレッドシートに書き込んでいます...")
            sheets_client.write_ranking_data(all_results, OUTPUT_SHEET_NAME)
            logger.info(f"合計 {len(all_results)} 件の結果を書き込みました")
        
        logger.info("検索順位モニタリングツールが正常に完了しました")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()