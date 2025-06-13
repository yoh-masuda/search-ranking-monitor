"""
順位変動グラフを生成するモジュール
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from datetime import datetime
from loguru import logger

# 日本語フォントの設定
plt.rcParams['font.sans-serif'] = ['Hiragino Sans', 'Arial Unicode MS', 'Yu Gothic', 'Meiryo', 'Takao', 'IPAexGothic', 'IPAPGothic', 'VL PGothic', 'Noto Sans CJK JP']
plt.rcParams['axes.unicode_minus'] = False

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import *
from src.google_sheets import GoogleSheetsClient


class RankingVisualizer:
    """順位変動を可視化するクラス"""
    
    def __init__(self, sheets_client: GoogleSheetsClient):
        """
        Args:
            sheets_client: Google Sheetsクライアント
        """
        self.sheets_client = sheets_client
        
    def get_ranking_history(self, sku_name: Optional[str] = None, keyword: Optional[str] = None) -> pd.DataFrame:
        """
        ランキング履歴データを取得
        
        Args:
            sku_name: SKU名（Noneの場合は全て）
            keyword: キーワード（Noneの場合は全て）
            
        Returns:
            ランキング履歴のDataFrame
        """
        try:
            # Rankingsシートからデータを読み取る
            result = self.sheets_client.sheets.values().get(
                spreadsheetId=self.sheets_client.spreadsheet_id,
                range=f'{OUTPUT_SHEET_NAME}!A:E'
            ).execute()
            
            values = result.get('values', [])
            
            if len(values) <= 1:  # ヘッダーのみまたは空
                logger.warning("ランキングデータがありません")
                return pd.DataFrame()
            
            # DataFrameに変換
            headers = values[0]
            data = values[1:]
            df = pd.DataFrame(data, columns=headers)
            
            # 日付をdatetime型に変換
            df['日付'] = pd.to_datetime(df['日付'])
            
            # 順位を数値に変換（圏外は999）
            df['Amazon順位'] = df['Amazon順位'].apply(lambda x: 999 if x == '圏外' else int(x))
            df['楽天順位'] = df['楽天順位'].apply(lambda x: 999 if x == '圏外' else int(x))
            
            # フィルタリング
            if sku_name:
                df = df[df['SKU名'] == sku_name]
            if keyword:
                df = df[df['キーワード'] == keyword]
            
            # 日付でソート
            df = df.sort_values('日付')
            
            return df
            
        except Exception as e:
            logger.error(f"ランキング履歴の取得エラー: {e}")
            return pd.DataFrame()
    
    def plot_ranking_trend(self, sku_name: str, keyword: str, save_path: Optional[str] = None):
        """
        特定のSKUとキーワードの順位変動グラフを作成
        
        Args:
            sku_name: SKU名
            keyword: キーワード
            save_path: 保存先パス（Noneの場合は表示のみ）
        """
        # データを取得
        df = self.get_ranking_history(sku_name, keyword)
        
        if df.empty:
            logger.warning(f"データが見つかりません: SKU={sku_name}, キーワード={keyword}")
            return
        
        # グラフを作成
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Amazon順位をプロット
        amazon_data = df[df['Amazon順位'] < 999]
        if not amazon_data.empty:
            ax.plot(amazon_data['日付'], amazon_data['Amazon順位'], 
                   marker='o', linestyle='-', linewidth=2, markersize=8,
                   label='Amazon', color='#FF9900')
        
        # 楽天順位をプロット
        rakuten_data = df[df['楽天順位'] < 999]
        if not rakuten_data.empty:
            ax.plot(rakuten_data['日付'], rakuten_data['楽天順位'], 
                   marker='s', linestyle='-', linewidth=2, markersize=8,
                   label='楽天', color='#BF0000')
        
        # グラフの設定
        ax.set_xlabel('日付', fontsize=12)
        ax.set_ylabel('順位', fontsize=12)
        ax.set_title(f'{sku_name} - 「{keyword}」の順位推移', fontsize=14, fontweight='bold')
        
        # Y軸を反転（1位が上に来るように）
        ax.invert_yaxis()
        
        # グリッドを追加
        ax.grid(True, alpha=0.3)
        
        # 凡例を追加
        ax.legend(loc='best')
        
        # X軸の日付フォーマット
        fig.autofmt_xdate()
        
        # レイアウトを調整
        plt.tight_layout()
        
        # 保存または表示
        if save_path:
            if hasattr(save_path, 'write'):  # BytesIOなどのファイルライクオブジェクトの場合
                plt.savefig(save_path, format='png', dpi=300, bbox_inches='tight')
            else:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"グラフを保存しました: {save_path}")
        else:
            plt.show()
        
        # メモリを解放
        plt.close(fig)
    
    def plot_keyword_comparison(self, sku_name: str, save_path: Optional[str] = None):
        """
        特定のSKUの全キーワードの順位を比較するグラフを作成
        
        Args:
            sku_name: SKU名
            save_path: 保存先パス（Noneの場合は表示のみ）
        """
        # データを取得
        df = self.get_ranking_history(sku_name)
        
        if df.empty:
            logger.warning(f"データが見つかりません: SKU={sku_name}")
            return
        
        # キーワードごとにグループ化
        keywords = df['キーワード'].unique()
        
        # グラフを作成
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # カラーマップ
        colors = plt.cm.Set3(range(len(keywords)))
        
        # Amazon順位のグラフ
        for i, kw in enumerate(keywords):
            kw_data = df[(df['キーワード'] == kw) & (df['Amazon順位'] < 999)]
            if not kw_data.empty:
                ax1.plot(kw_data['日付'], kw_data['Amazon順位'], 
                        marker='o', linestyle='-', linewidth=2,
                        label=kw, color=colors[i])
        
        ax1.set_ylabel('Amazon順位', fontsize=12)
        ax1.set_title(f'{sku_name} - Amazon順位推移', fontsize=14)
        ax1.invert_yaxis()
        ax1.grid(True, alpha=0.3)
        ax1.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # 楽天順位のグラフ
        for i, kw in enumerate(keywords):
            kw_data = df[(df['キーワード'] == kw) & (df['楽天順位'] < 999)]
            if not kw_data.empty:
                ax2.plot(kw_data['日付'], kw_data['楽天順位'], 
                        marker='s', linestyle='-', linewidth=2,
                        label=kw, color=colors[i])
        
        ax2.set_xlabel('日付', fontsize=12)
        ax2.set_ylabel('楽天順位', fontsize=12)
        ax2.set_title(f'{sku_name} - 楽天順位推移', fontsize=14)
        ax2.invert_yaxis()
        ax2.grid(True, alpha=0.3)
        ax2.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # X軸の日付フォーマット
        fig.autofmt_xdate()
        
        # レイアウトを調整
        plt.tight_layout()
        
        # 保存または表示
        if save_path:
            if hasattr(save_path, 'write'):  # BytesIOなどのファイルライクオブジェクトの場合
                plt.savefig(save_path, format='png', dpi=300, bbox_inches='tight')
            else:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"グラフを保存しました: {save_path}")
        else:
            plt.show()
        
        # メモリを解放
        plt.close(fig)
    
    def get_available_combinations(self) -> List[Dict[str, str]]:
        """
        利用可能なSKU名とキーワードの組み合わせを取得
        
        Returns:
            SKU名とキーワードの組み合わせリスト
        """
        df = self.get_ranking_history()
        
        if df.empty:
            return []
        
        # ユニークな組み合わせを取得
        combinations = df[['SKU名', 'キーワード']].drop_duplicates().to_dict('records')
        
        return combinations


def main():
    """グラフ生成のメイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='順位変動グラフを生成')
    parser.add_argument('--sku', type=str, help='SKU名')
    parser.add_argument('--keyword', type=str, help='キーワード')
    parser.add_argument('--output', type=str, help='出力ファイルパス')
    parser.add_argument('--list', action='store_true', help='利用可能な組み合わせを表示')
    parser.add_argument('--compare', action='store_true', help='キーワード比較グラフを作成')
    
    args = parser.parse_args()
    
    # Google Sheetsクライアントを初期化
    sheets_client = GoogleSheetsClient(
        GOOGLE_SHEETS_CREDENTIALS_PATH,
        SPREADSHEET_ID
    )
    
    # Visualizerを初期化
    visualizer = RankingVisualizer(sheets_client)
    
    if args.list:
        # 利用可能な組み合わせを表示
        combinations = visualizer.get_available_combinations()
        if combinations:
            print("\n利用可能なSKU名とキーワード:")
            for combo in combinations:
                print(f"  SKU: {combo['SKU名']}, キーワード: {combo['キーワード']}")
        else:
            print("データがありません")
    
    elif args.compare and args.sku:
        # キーワード比較グラフを作成
        visualizer.plot_keyword_comparison(args.sku, args.output)
    
    elif args.sku and args.keyword:
        # 順位変動グラフを作成
        visualizer.plot_ranking_trend(args.sku, args.keyword, args.output)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()