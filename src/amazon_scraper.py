import time
from typing import Optional, List, Dict
from urllib.parse import quote_plus
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from loguru import logger
import random


class AmazonScraper:
    """Amazon.co.jpの検索結果をスクレイピングするクラス"""
    
    def __init__(self, headless: bool = True):
        """
        Args:
            headless: ヘッドレスモードで実行するか
        """
        self.base_url = "https://www.amazon.co.jp"
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
    
    def _is_sponsored_product(self, product_element) -> bool:
        """
        商品が広告（スポンサー）商品かどうかを判定
        
        Args:
            product_element: 商品要素のHTML
            
        Returns:
            広告商品の場合True
        """
        try:
            # BeautifulSoupで解析
            soup = BeautifulSoup(str(product_element), 'html.parser')
            
            # スポンサー商品の判定条件
            # 1. data-component-type属性がsp-sponsored-resultの要素
            if soup.find(attrs={'data-component-type': 'sp-sponsored-result'}):
                return True
            
            # 2. AdHolderクラスを含む要素
            if soup.find(class_='AdHolder'):
                return True
            
            # 3. 「スポンサー」または「Sponsored」のテキストを含む
            text_content = soup.get_text()
            if 'スポンサー' in text_content or 'Sponsored' in text_content:
                # ただし、商品名に含まれる場合は除外
                sponsored_elements = soup.find_all(text=['スポンサー', 'Sponsored'])
                for elem in sponsored_elements:
                    parent = elem.parent
                    if parent and ('s-sponsored-label' in parent.get('class', []) or 
                                 's-label-popover' in parent.get('class', [])):
                        return True
            
            # 4. s-sponsored-labelクラスを含む
            if soup.find(class_='s-sponsored-label'):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"広告判定中のエラー: {e}")
            return False
    
    def search_product_rank(self, keyword: str, target_asin: str, max_pages: int = 5) -> Optional[int]:
        """
        指定したキーワードで検索し、ターゲットASINのオーガニック順位を取得
        
        Args:
            keyword: 検索キーワード
            target_asin: 検索対象のASIN
            max_pages: 最大検索ページ数
            
        Returns:
            オーガニック順位（1から始まる）、見つからない場合はNone
        """
        try:
            if not self.driver:
                self._init_driver()
            
            organic_rank = 0  # オーガニック商品のカウンター
            
            for page in range(1, max_pages + 1):
                logger.info(f"Amazon検索: キーワード='{keyword}', ページ={page}/{max_pages}")
                
                # 検索URLを構築
                if page == 1:
                    search_url = f"{self.base_url}/s?k={quote_plus(keyword)}"
                else:
                    search_url = f"{self.base_url}/s?k={quote_plus(keyword)}&page={page}"
                
                # ページを取得
                self.driver.get(search_url)
                
                # ランダムな待機時間（1-3秒）
                time.sleep(random.uniform(1, 3))
                
                # 検索結果の読み込みを待つ
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '[data-component-type="s-search-result"]'))
                    )
                except TimeoutException:
                    logger.warning(f"検索結果の読み込みタイムアウト: ページ {page}")
                    continue
                
                # ページソースを取得
                page_source = self.driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                
                # 検索結果の商品を取得
                products = soup.find_all('div', {'data-component-type': 's-search-result'})
                
                for product in products:
                    # ASINを取得
                    asin = product.get('data-asin', '')
                    
                    if not asin:
                        continue
                    
                    # スポンサー商品かどうかチェック
                    if self._is_sponsored_product(product.prettify()):
                        logger.debug(f"広告商品をスキップ: ASIN={asin}")
                        continue
                    
                    # オーガニック商品のカウントを増やす
                    organic_rank += 1
                    
                    # ターゲットASINと一致するかチェック
                    if asin == target_asin:
                        logger.info(f"商品発見: ASIN={target_asin}, オーガニック順位={organic_rank}")
                        return organic_rank
                
                # 次のページボタンがあるか確認
                next_button = soup.find('a', {'aria-label': '次のページに移動してください'})
                if not next_button:
                    logger.info("最終ページに到達しました")
                    break
            
            logger.info(f"商品が見つかりませんでした: ASIN={target_asin}")
            return None
            
        except Exception as e:
            logger.error(f"Amazon検索中のエラー: {e}")
            return None
    
    def search_multiple_keywords(self, keywords: List[str], target_asin: str, max_pages: int = 5) -> Dict[str, Optional[int]]:
        """
        複数のキーワードで検索し、それぞれの順位を取得
        
        Args:
            keywords: 検索キーワードのリスト
            target_asin: 検索対象のASIN
            max_pages: 最大検索ページ数
            
        Returns:
            キーワードと順位の辞書
        """
        results = {}
        
        try:
            if not self.driver:
                self._init_driver()
            
            for keyword in keywords:
                rank = self.search_product_rank(keyword, target_asin, max_pages)
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