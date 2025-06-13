"""
Web管理画面アプリケーション
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import json
import base64
from io import BytesIO

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from loguru import logger
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import *
from src.google_sheets import GoogleSheetsClient
from src.visualizer import RankingVisualizer
from src.main import search_rankings

app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app)

# グローバル変数
sheets_client = None
visualizer = None

def init_clients():
    """クライアントを初期化"""
    global sheets_client, visualizer
    if not sheets_client:
        sheets_client = GoogleSheetsClient(
            GOOGLE_SHEETS_CREDENTIALS_PATH,
            SPREADSHEET_ID
        )
    if not visualizer:
        visualizer = RankingVisualizer(sheets_client)

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/api/products', methods=['GET'])
def get_products():
    """登録済み商品リストを取得"""
    try:
        init_clients()
        data = sheets_client.read_input_data(INPUT_SHEET_NAME)
        
        # 各商品の最新順位を取得
        ranking_df = visualizer.get_ranking_history()
        
        for product in data:
            # 最新順位情報を追加
            product['latest_rankings'] = {}
            
            if not ranking_df.empty:
                # この商品の最新データを取得
                product_df = ranking_df[ranking_df['SKU名'] == product['sku_name']]
                
                if not product_df.empty:
                    # キーワードごとの最新順位を取得
                    for keyword in product['keywords']:
                        keyword_df = product_df[product_df['キーワード'] == keyword]
                        if not keyword_df.empty:
                            latest = keyword_df.iloc[-1]  # 最新のデータ
                            product['latest_rankings'][keyword] = {
                                'amazon': latest['Amazon順位'] if latest['Amazon順位'] < 999 else None,
                                'rakuten': latest['楽天順位'] if latest['楽天順位'] < 999 else None,
                                'date': latest['日付'].strftime('%Y-%m-%d')
                            }
        
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        logger.error(f"商品リスト取得エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/products', methods=['POST'])
def add_product():
    """新規商品を登録"""
    try:
        init_clients()
        data = request.json
        
        # 現在のデータを取得
        result = sheets_client.sheets.values().get(
            spreadsheetId=sheets_client.spreadsheet_id,
            range=f'{INPUT_SHEET_NAME}!A:Z'
        ).execute()
        
        values = result.get('values', [])
        if not values:
            # ヘッダーを作成
            headers = ['SKU名', 'Amazon URL', '楽天URL']
            for i in range(1, 11):  # KW1〜KW10
                headers.append(f'KW{i}')
            values = [headers]
        
        # 新しい行を追加
        new_row = [
            data.get('sku_name', ''),
            data.get('amazon_url', ''),
            data.get('rakuten_url', '')
        ]
        
        # キーワードを追加
        keywords = data.get('keywords', [])
        for i in range(10):  # 最大10個のキーワード
            if i < len(keywords):
                new_row.append(keywords[i])
            else:
                new_row.append('')
        
        # スプレッドシートに書き込み
        next_row = len(values) + 1
        sheets_client.sheets.values().update(
            spreadsheetId=sheets_client.spreadsheet_id,
            range=f'{INPUT_SHEET_NAME}!A{next_row}:M{next_row}',
            valueInputOption='RAW',
            body={'values': [new_row]}
        ).execute()
        
        return jsonify({'status': 'success', 'message': '商品を登録しました'})
        
    except Exception as e:
        logger.error(f"商品登録エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/products/<int:row_number>', methods=['PUT'])
def update_product(row_number):
    """商品情報を更新"""
    try:
        init_clients()
        data = request.json
        
        # 更新する行のデータを作成
        updated_row = [
            data.get('sku_name', ''),
            data.get('amazon_url', ''),
            data.get('rakuten_url', '')
        ]
        
        # キーワードを追加
        keywords = data.get('keywords', [])
        for i in range(10):  # 最大10個のキーワード
            if i < len(keywords):
                updated_row.append(keywords[i])
            else:
                updated_row.append('')
        
        # スプレッドシートを更新
        sheets_client.sheets.values().update(
            spreadsheetId=sheets_client.spreadsheet_id,
            range=f'{INPUT_SHEET_NAME}!A{row_number}:M{row_number}',
            valueInputOption='RAW',
            body={'values': [updated_row]}
        ).execute()
        
        return jsonify({'status': 'success', 'message': '商品情報を更新しました'})
        
    except Exception as e:
        logger.error(f"商品更新エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/rankings/history', methods=['GET'])
def get_ranking_history():
    """ランキング履歴を取得"""
    try:
        init_clients()
        sku_name = request.args.get('sku_name')
        keyword = request.args.get('keyword')
        days = int(request.args.get('days', 30))
        
        # データを取得
        df = visualizer.get_ranking_history(sku_name, keyword)
        
        if not df.empty:
            # 指定期間でフィルタ
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            df = df[df['日付'] >= start_date]
            
            # JSON形式に変換
            df['日付'] = df['日付'].dt.strftime('%Y-%m-%d')
            df['Amazon順位'] = df['Amazon順位'].apply(lambda x: None if x == 999 else x)
            df['楽天順位'] = df['楽天順位'].apply(lambda x: None if x == 999 else x)
            
            data = df.to_dict('records')
        else:
            data = []
        
        return jsonify({'status': 'success', 'data': data})
        
    except Exception as e:
        logger.error(f"履歴取得エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/rankings/graph', methods=['GET'])
def get_ranking_graph():
    """ランキンググラフを生成"""
    try:
        init_clients()
        sku_name = request.args.get('sku_name')
        keyword = request.args.get('keyword')
        
        if not sku_name or not keyword:
            return jsonify({'status': 'error', 'message': 'SKU名とキーワードを指定してください'}), 400
        
        # グラフを生成
        buffer = BytesIO()
        visualizer.plot_ranking_trend(sku_name, keyword, save_path=buffer)
        buffer.seek(0)
        
        # Base64エンコード
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        
        return jsonify({
            'status': 'success',
            'image': f'data:image/png;base64,{img_base64}'
        })
        
    except Exception as e:
        logger.error(f"グラフ生成エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/run-search', methods=['POST'])
def run_search():
    """検索を実行"""
    try:
        init_clients()
        data = request.json
        sku_name = data.get('sku_name')
        
        # 入力データを読み取る
        all_skus = sheets_client.read_input_data(INPUT_SHEET_NAME)
        
        # 特定のSKUのみ検索する場合
        if sku_name:
            sku_list = [sku for sku in all_skus if sku['sku_name'] == sku_name]
        else:
            sku_list = all_skus
        
        if not sku_list:
            return jsonify({'status': 'error', 'message': '対象商品が見つかりません'}), 404
        
        # 検索を実行
        all_results = []
        for sku_data in sku_list:
            results = search_rankings(sku_data)
            all_results.extend(results)
        
        # 結果を保存
        if all_results:
            sheets_client.write_ranking_data(all_results, OUTPUT_SHEET_NAME)
        
        return jsonify({
            'status': 'success',
            'message': f'{len(all_results)}件の結果を取得しました'
        })
        
    except Exception as e:
        logger.error(f"検索実行エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/options', methods=['GET'])
def get_options():
    """フィルタオプションを取得"""
    try:
        init_clients()
        
        # 利用可能な組み合わせを取得
        combinations = visualizer.get_available_combinations()
        
        # ユニークなSKU名とキーワードを抽出
        sku_names = sorted(list(set(c['SKU名'] for c in combinations)))
        keywords = sorted(list(set(c['キーワード'] for c in combinations)))
        
        return jsonify({
            'status': 'success',
            'sku_names': sku_names,
            'keywords': keywords
        })
        
    except Exception as e:
        logger.error(f"オプション取得エラー: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001)