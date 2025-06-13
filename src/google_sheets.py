import os
import re
from datetime import datetime
from typing import List, Dict, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from loguru import logger


class GoogleSheetsClient:
    """Google Sheets APIクライアント"""
    
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        """
        Args:
            credentials_path: サービスアカウントの認証情報JSONファイルのパス
            spreadsheet_id: 操作対象のスプレッドシートID
        """
        self.spreadsheet_id = spreadsheet_id
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            self.sheets = self.service.spreadsheets()
            logger.info(f"Google Sheets APIクライアントを初期化しました: {spreadsheet_id}")
        except Exception as e:
            logger.error(f"Google Sheets APIクライアントの初期化に失敗しました: {e}")
            raise
    
    def extract_asin_from_url(self, url: str) -> str:
        """
        Amazon URLからASINを抽出
        
        Args:
            url: Amazon商品URL
            
        Returns:
            ASIN（見つからない場合は空文字）
        """
        if not url:
            return ""
        
        # Amazon URLのパターン
        # https://www.amazon.co.jp/dp/B01XXXXX
        # https://www.amazon.co.jp/gp/product/B01XXXXX
        # https://www.amazon.co.jp/商品名/dp/B01XXXXX
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return ""
    
    def read_input_data(self, sheet_name: str = 'Sheet1') -> List[Dict[str, Any]]:
        """
        入力データを読み取る
        
        Args:
            sheet_name: 読み取るシート名
            
        Returns:
            SKU情報とキーワードのリスト
        """
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A:Z'  # 十分な範囲を指定
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("スプレッドシートにデータがありません")
                return []
            
            headers = values[0]
            data = []
            
            for row_idx, row in enumerate(values[1:], start=2):
                if len(row) < 3:  # 最低限SKU名、Amazon URL、楽天URLが必要
                    continue
                
                sku_data = {
                    'row_number': row_idx,
                    'sku_name': row[0] if len(row) > 0 else '',
                    'amazon_url': row[1] if len(row) > 1 else '',
                    'rakuten_url': row[2] if len(row) > 2 else '',
                    'asin': '',
                    'keywords': []
                }
                
                # Amazon URLからASINを抽出
                if sku_data['amazon_url']:
                    extracted_asin = self.extract_asin_from_url(sku_data['amazon_url'])
                    if extracted_asin:
                        sku_data['asin'] = extracted_asin
                        logger.debug(f"Amazon URLからASINを抽出: {extracted_asin} ({sku_data['sku_name']})")
                
                # キーワード列を読み取る（KW1, KW2, KW3...）
                for col_idx in range(3, len(row)):
                    if col_idx < len(headers) and headers[col_idx].startswith('KW') and row[col_idx]:
                        sku_data['keywords'].append(row[col_idx])
                
                if sku_data['sku_name'] and (sku_data['asin'] or sku_data['rakuten_url']):
                    data.append(sku_data)
                    logger.debug(f"読み取り: {sku_data['sku_name']} - キーワード数: {len(sku_data['keywords'])}")
            
            logger.info(f"合計 {len(data)} 個のSKUデータを読み取りました")
            return data
            
        except HttpError as e:
            logger.error(f"スプレッドシートの読み取りエラー: {e}")
            raise
    
    def write_ranking_data(self, ranking_data: List[Dict[str, Any]], sheet_name: str = 'Rankings'):
        """
        ランキングデータを書き込む
        
        Args:
            ranking_data: ランキングデータのリスト
            sheet_name: 書き込むシート名
        """
        try:
            # シートが存在するか確認
            sheet_metadata = self.sheets.get(spreadsheetId=self.spreadsheet_id).execute()
            sheets = sheet_metadata.get('sheets', [])
            
            sheet_exists = any(sheet['properties']['title'] == sheet_name for sheet in sheets)
            
            if not sheet_exists:
                # シートを作成
                request_body = {
                    'requests': [{
                        'addSheet': {
                            'properties': {
                                'title': sheet_name
                            }
                        }
                    }]
                }
                self.sheets.batchUpdate(
                    spreadsheetId=self.spreadsheet_id,
                    body=request_body
                ).execute()
                
                # ヘッダーを追加
                headers = [['日付', 'SKU名', 'キーワード', 'Amazon順位', '楽天順位']]
                self.sheets.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!A1:E1',
                    valueInputOption='RAW',
                    body={'values': headers}
                ).execute()
                logger.info(f"新しいシート '{sheet_name}' を作成しました")
            
            # 既存データの行数を取得
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A:A'
            ).execute()
            
            existing_rows = len(result.get('values', []))
            next_row = existing_rows + 1
            
            # データを準備
            values = []
            for data in ranking_data:
                values.append([
                    data['date'],
                    data['sku_name'],
                    data['keyword'],
                    data['amazon_rank'] if data['amazon_rank'] else '圏外',
                    data['rakuten_rank'] if data['rakuten_rank'] else '圏外'
                ])
            
            if values:
                # データを追記
                self.sheets.values().update(
                    spreadsheetId=self.spreadsheet_id,
                    range=f'{sheet_name}!A{next_row}:E{next_row + len(values) - 1}',
                    valueInputOption='RAW',
                    body={'values': values}
                ).execute()
                
                logger.info(f"{len(values)} 件のランキングデータを書き込みました")
            
        except HttpError as e:
            logger.error(f"スプレッドシートへの書き込みエラー: {e}")
            raise
    
    def get_last_execution_date(self, sheet_name: str = 'Rankings') -> str:
        """
        最後の実行日を取得
        
        Args:
            sheet_name: ランキングデータのシート名
            
        Returns:
            最後の実行日（YYYY-MM-DD形式）またはNone
        """
        try:
            result = self.sheets.values().get(
                spreadsheetId=self.spreadsheet_id,
                range=f'{sheet_name}!A:A'
            ).execute()
            
            values = result.get('values', [])
            if len(values) > 1:  # ヘッダーを除く
                last_date = values[-1][0]
                return last_date
            
            return None
            
        except HttpError:
            return None