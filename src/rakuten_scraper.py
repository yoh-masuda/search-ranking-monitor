import time
import re
from typing import Optional, List, Dict
from urllib.parse import quote_plus, urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from loguru import logger
import random


class RakutenScraper:
    """楽天市場の検索結果をスクレイピングするクラス"""
    
    def __init__(self, headless: bool = True):
        """
        Args:
            headless: ヘッドレスモードで実行するか
        """
        self.base_url = "https://search.rakuten.co.jp/search/mall"
        self.headless = headless
        self.driver = None
    
    def _init_driver(self):
        """Seleniumドライバーを初期化"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
    
    def _close_driver(self):
        """ドライバーを閉じる"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _extract_product_id_from_url(self, url: str) -> Optional[str]:
        """
        楽天商品URLから商品IDを抽出
        
        Args:
            url: 楽天商品URL
            
        Returns:
            商品ID
        """
        try:
            # URLから商品IDを抽出するパターン
            # 例: https://item.rakuten.co.jp/shop-name/product-id/
            patterns = [
                r'/item\.rakuten\.co\.jp/[^/]+/([^/?]+)',  # 通常の商品URL
                r'/product\.rakuten\.co\.jp/product/-/([^/?]+)',  # 別形式のURL
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # 商品IDが直接渡された場合
            if '/' not in url and '?' not in url:
                return url
            
            return None
            
        except Exception as e:
            logger.debug(f"商品ID抽出エラー: {e}")
            return None
    
    def search_product_rank(self, keyword: str, target_url: str, max_pages: int = 5) -> Optional[int]:
        """
        指定したキーワードで検索し、ターゲット商品の順位を取得
        
        Args:
            keyword: 検索キーワード
            target_url: 検索対象の商品URLまたは商品ID
            max_pages: 最大検索ページ数
            
        Returns:
            商品順位（1から始まる）、見つからない場合はNone
        """
        try:
            if not self.driver:
                self._init_driver()
            
            # ターゲット商品IDを抽出
            target_product_id = self._extract_product_id_from_url(target_url)
            if not target_product_id:
                logger.error(f"商品IDを抽出できませんでした: {target_url}")
                return None
            
            rank = 0  # 商品のカウンター（広告含む全ての商品）
            
            for page in range(1, max_pages + 1):
                logger.info(f"楽天検索: キーワード='{keyword}', ページ={page}/{max_pages}")
                
                # 検索URLを構築
                if page == 1:
                    search_url = f"{self.base_url}/{quote_plus(keyword)}/"
                else:
                    search_url = f"{self.base_url}/{quote_plus(keyword)}/p{page}"
                
                # ページを取得
                self.driver.get(search_url)
                
                # ランダムな待機時間（1-3秒）
                time.sleep(random.uniform(1, 3))
                
                # 検索結果の読み込みを待つ
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.searchresultitem'))
                    )
                except TimeoutException:
                    logger.warning(f"検索結果の読み込みタイムアウト: ページ {page}")
                    continue
                
                # ページソースを取得
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # 検索結果の商品を取得
                products = soup.find_all('div', class_='searchresultitem')
                
                for product in products:
                    rank += 1
                    
                    # 商品URLを取得
                    link_elem = product.find('a')
                    if not link_elem or not link_elem.get('href'):
                        continue
                    
                    product_url = link_elem['href']
                    
                    # 商品IDを抽出
                    product_id = self._extract_product_id_from_url(product_url)
                    
                    if product_id and product_id == target_product_id:
                        logger.info(f"商品発見: ID={target_product_id}, 順位={rank}")
                        return rank
                
                # 次のページボタンがあるか確認
                pagination = soup.find('div', class_='pagination')
                if pagination:
                    next_links = pagination.find_all('a')
                    has_next = any('次へ' in link.get_text() for link in next_links)
                    if not has_next:
                        logger.info("最終ページに到達しました")
                        break
                else:
                    # ページネーションが見つからない場合は最終ページと判断
                    logger.info("ページネーションが見つかりません。最終ページと判断します。")
                    break
            
            logger.info(f"商品が見つかりませんでした: ID={target_product_id}")
            return None
            
        except Exception as e:
            logger.error(f"楽天検索中のエラー: {e}")
            return None
    
    def search_multiple_keywords(self, keywords: List[str], target_url: str, max_pages: int = 5) -> Dict[str, Optional[int]]:
        """
        複数のキーワードで検索し、それぞれの順位を取得
        
        Args:
            keywords: 検索キーワードのリスト
            target_url: 検索対象の商品URLまたは商品ID
            max_pages: 最大検索ページ数
            
        Returns:
            キーワードと順位の辞書
        """
        results = {}
        
        try:
            if not self.driver:
                self._init_driver()
            
            for keyword in keywords:
                rank = self.search_product_rank(keyword, target_url, max_pages)
                results[keyword] = rank
                
                # リクエスト間隔を空ける（2-5秒）
                if keyword != keywords[-1]:  # 最後のキーワード以外
                    time.sleep(random.uniform(2, 5))
            
        finally:
            self._close_driver()
        
        return results
    
    def __enter__(self):
        """with文のenter処理"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """with文のexit処理"""
        self._close_driver()