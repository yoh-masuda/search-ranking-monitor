"""
Streamlit版 検索順位モニタリングアプリ（データ共有版）
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os
from deta import Deta

# ページ設定
st.set_page_config(
    page_title="Amazon・楽天 検索順位モニタリング",
    page_icon="🔍",
    layout="wide"
)

# Deta初期化（環境変数から）
# Streamlit Secretsから取得
if 'DETA_PROJECT_KEY' in st.secrets:
    deta = Deta(st.secrets['DETA_PROJECT_KEY'])
    db_products = deta.Base("products")
    db_rankings = deta.Base("rankings")
else:
    # ローカル開発用
    st.warning("⚠️ データベース未接続。ローカルモードで動作中。")
    db_products = None
    db_rankings = None

# CSSスタイル
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    .ranking-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .product-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# データ取得関数
@st.cache_data(ttl=10)  # 10秒キャッシュ
def get_products():
    """商品リストを取得"""
    if db_products:
        try:
            result = db_products.fetch()
            return result.items
        except:
            return []
    else:
        # ローカルモード
        if 'products' not in st.session_state:
            st.session_state.products = []
        return st.session_state.products

@st.cache_data(ttl=10)  # 10秒キャッシュ
def get_rankings():
    """ランキングデータを取得"""
    if db_rankings:
        try:
            result = db_rankings.fetch()
            return result.items
        except:
            return []
    else:
        # ローカルモード
        if 'rankings' not in st.session_state:
            st.session_state.rankings = []
        return st.session_state.rankings

def add_product(product_data):
    """商品を追加"""
    if db_products:
        try:
            # 一意のキーを生成
            key = f"{product_data['name']}_{datetime.now().timestamp()}"
            db_products.put(product_data, key)
            st.cache_data.clear()  # キャッシュをクリア
            return True
        except:
            return False
    else:
        # ローカルモード
        if 'products' not in st.session_state:
            st.session_state.products = []
        st.session_state.products.append(product_data)
        return True

def add_ranking(ranking_data):
    """ランキングデータを追加"""
    if db_rankings:
        try:
            # 一意のキーを生成
            key = f"{ranking_data['product']}_{ranking_data['keyword']}_{ranking_data['date']}"
            db_rankings.put(ranking_data, key)
            st.cache_data.clear()  # キャッシュをクリア
            return True
        except:
            return False
    else:
        # ローカルモード
        if 'rankings' not in st.session_state:
            st.session_state.rankings = []
        st.session_state.rankings.append(ranking_data)
        return True

def delete_product(key):
    """商品を削除"""
    if db_products:
        try:
            db_products.delete(key)
            st.cache_data.clear()  # キャッシュをクリア
            return True
        except:
            return False
    else:
        # ローカルモード（インデックスで削除）
        if 'products' in st.session_state:
            st.session_state.products.pop(key)
        return True

# タイトル
st.title("🔍 Amazon・楽天 検索順位モニタリング")

# 共有状態の表示
if db_products:
    st.success("🌐 データ共有モード：すべてのユーザーと情報を共有中")
else:
    st.info("💻 ローカルモード：データはこのセッションのみ有効")

# タブ
tab1, tab2, tab3 = st.tabs(["📊 ダッシュボード", "📦 商品管理", "🔄 検索実行"])

# ダッシュボードタブ
with tab1:
    # データを取得
    products = get_products()
    rankings = get_rankings()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        product_names = [p.get('name', p.get('key', '')) for p in products]
        selected_product = st.selectbox(
            "商品選択",
            ["すべて"] + product_names
        )
    
    with col2:
        if selected_product != "すべて":
            product = next((p for p in products if p.get('name', p.get('key', '')) == selected_product), None)
            if product and 'keywords' in product:
                selected_keyword = st.selectbox(
                    "キーワード",
                    ["すべて"] + product['keywords']
                )
            else:
                selected_keyword = "すべて"
        else:
            selected_keyword = "すべて"
    
    with col3:
        period = st.selectbox(
            "期間",
            ["過去7日間", "過去30日間", "過去90日間", "過去1年間"]
        )
    
    with col4:
        if st.button("🔄 更新", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
    # グラフ表示
    if rankings:
        df = pd.DataFrame(rankings)
        
        # フィルタリング
        if selected_product != "すべて":
            df = df[df['product'] == selected_product]
        if selected_keyword != "すべて":
            df = df[df['keyword'] == selected_keyword]
        
        if not df.empty and len(df) > 0:
            try:
                # 日付でソート
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')
                
                # グラフ作成
                fig = make_subplots(
                    rows=1, cols=1,
                    subplot_titles=("検索順位推移",)
                )
                
                # 商品・キーワードごとにプロット
                for product in df['product'].unique():
                    for keyword in df[df['product'] == product]['keyword'].unique():
                        data = df[(df['product'] == product) & (df['keyword'] == keyword)]
                        
                        # Amazon
                        if 'amazon_rank' in data.columns:
                            fig.add_trace(go.Scatter(
                                x=data['date'],
                                y=data['amazon_rank'],
                                mode='lines+markers',
                                name=f"{product} - {keyword} (Amazon)",
                                line=dict(width=2),
                                marker=dict(size=8)
                            ))
                        
                        # 楽天
                        if 'rakuten_rank' in data.columns:
                            fig.add_trace(go.Scatter(
                                x=data['date'],
                                y=data['rakuten_rank'],
                                mode='lines+markers',
                                name=f"{product} - {keyword} (楽天)",
                                line=dict(width=2, dash='dash'),
                                marker=dict(size=8)
                            ))
                
                fig.update_yaxis(autorange="reversed", title="順位")
                fig.update_xaxis(title="日付")
                fig.update_layout(height=500)
                
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"グラフの表示中にエラーが発生しました: {str(e)}")
            
            # 統計情報
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if 'amazon_rank' in df.columns:
                    amazon_best = df[df['amazon_rank'].notna()]['amazon_rank'].min()
                    st.metric("Amazon最高順位", f"{int(amazon_best)}位" if pd.notna(amazon_best) else "データなし")
                else:
                    st.metric("Amazon最高順位", "データなし")
            
            with col2:
                if 'rakuten_rank' in df.columns:
                    rakuten_best = df[df['rakuten_rank'].notna()]['rakuten_rank'].min()
                    st.metric("楽天最高順位", f"{int(rakuten_best)}位" if pd.notna(rakuten_best) else "データなし")
                else:
                    st.metric("楽天最高順位", "データなし")
            
            with col3:
                last_date = df['date'].max().strftime('%Y-%m-%d')
                st.metric("最終更新", last_date)
        else:
            st.info("データがありません。商品を登録して検索を実行してください。")
    else:
        st.info("データがありません。商品を登録して検索を実行してください。")

# 商品管理タブ
with tab2:
    st.subheader("新規商品登録")
    
    with st.form("product_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            product_name = st.text_input("商品名", placeholder="例: リノンロックオイル")
            amazon_url = st.text_input("Amazon URL", placeholder="https://www.amazon.co.jp/dp/...")
        
        with col2:
            rakuten_url = st.text_input("楽天URL", placeholder="https://item.rakuten.co.jp/...")
            keywords = st.text_area("キーワード（改行区切り）", placeholder="ヘアオイル\nロックオイル\nヘアケア")
        
        submitted = st.form_submit_button("商品を登録", type="primary")
        
        if submitted:
            if product_name and (amazon_url or rakuten_url) and keywords:
                # キーワードを配列に変換
                keyword_list = [k.strip() for k in keywords.split('\n') if k.strip()]
                
                # ASINを抽出
                asin = ""
                if amazon_url:
                    import re
                    match = re.search(r'/dp/([A-Z0-9]{10})', amazon_url)
                    if match:
                        asin = match.group(1)
                
                # 商品を追加
                product_data = {
                    'name': product_name,
                    'amazon_url': amazon_url,
                    'rakuten_url': rakuten_url,
                    'asin': asin,
                    'keywords': keyword_list,
                    'created_at': datetime.now().isoformat()
                }
                
                if add_product(product_data):
                    st.success("商品を登録しました！")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("登録に失敗しました")
            else:
                st.error("必須項目を入力してください")
    
    st.divider()
    
    st.subheader("登録済み商品")
    
    # 最新データを取得
    products = get_products()
    rankings = get_rankings()
    
    if products:
        for i, product in enumerate(products):
            with st.container():
                st.markdown(f"""
                <div class="product-card">
                    <h4>📦 {product.get('name', 'Unknown')}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Amazon:** {product.get('asin', 'なし')}")
                    if product.get('amazon_url'):
                        st.link_button("Amazonで見る", product['amazon_url'])
                
                with col2:
                    st.write(f"**楽天:** {'あり' if product.get('rakuten_url') else 'なし'}")
                    if product.get('rakuten_url'):
                        st.link_button("楽天で見る", product['rakuten_url'])
                
                with col3:
                    if db_products:
                        # Deta使用時はキーで削除
                        if st.button(f"削除", key=f"delete_{product.get('key', i)}"):
                            if delete_product(product['key']):
                                st.rerun()
                    else:
                        # ローカルモード
                        if st.button(f"削除", key=f"delete_{i}"):
                            if delete_product(i):
                                st.rerun()
                
                if 'keywords' in product:
                    st.write(f"**キーワード:** {', '.join(product['keywords'])}")
                
                # 最新順位を表示
                product_name = product.get('name', product.get('key', ''))
                latest_rankings = [r for r in rankings if r.get('product') == product_name]
                
                if latest_rankings:
                    st.write("**最新順位:**")
                    for keyword in product.get('keywords', []):
                        kr = [r for r in latest_rankings if r.get('keyword') == keyword]
                        if kr:
                            latest = sorted(kr, key=lambda x: x.get('date', ''))[-1]
                            amazon = f"A:{latest.get('amazon_rank')}位" if latest.get('amazon_rank') else "A:圏外"
                            rakuten = f"R:{latest.get('rakuten_rank')}位" if latest.get('rakuten_rank') else "R:圏外"
                            st.write(f"- {keyword}: {amazon} / {rakuten} ({latest.get('date', 'N/A')})")
    else:
        st.info("商品が登録されていません")

# 検索実行タブ
with tab3:
    st.subheader("検索実行")
    
    # 最新データを取得
    products = get_products()
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        product_names = [p.get('name', p.get('key', '')) for p in products]
        target_product = st.selectbox(
            "対象商品",
            ["すべての商品"] + product_names
        )
    
    with col2:
        if st.button("🔍 検索を実行", type="primary"):
            if products:
                with st.spinner("検索を実行中..."):
                    # ダミーデータを追加（実際の実装では検索処理を行う）
                    import random
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    products_to_search = products
                    if target_product != "すべての商品":
                        products_to_search = [p for p in products if p.get('name', p.get('key', '')) == target_product]
                    
                    count = 0
                    for product in products_to_search:
                        for keyword in product.get('keywords', []):
                            # ランダムな順位を生成（デモ用）
                            amazon_rank = random.choice([None, 1, 2, 3, 5, 8, 12, 20, 35])
                            rakuten_rank = random.choice([None, 1, 3, 5, 7, 10, 15, 25, 40])
                            
                            ranking_data = {
                                'date': today,
                                'product': product.get('name', product.get('key', '')),
                                'keyword': keyword,
                                'amazon_rank': amazon_rank,
                                'rakuten_rank': rakuten_rank
                            }
                            
                            add_ranking(ranking_data)
                            count += 1
                    
                    st.success(f"✅ {count}件の検索結果を取得しました！")
                    st.balloons()
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.error("商品が登録されていません")
    
    st.divider()
    
    # 実行履歴
    st.subheader("実行履歴")
    
    rankings = get_rankings()
    
    if rankings:
        df = pd.DataFrame(rankings)
        if 'date' in df.columns:
            dates = df['date'].unique()
            
            for date in sorted(dates, reverse=True)[:5]:  # 最新5件
                date_data = df[df['date'] == date]
                st.write(f"**{date}** - {len(date_data)}件の結果")
    else:
        st.info("実行履歴がありません")

# サイドバー
with st.sidebar:
    st.header("ℹ️ 使い方")
    st.write("""
    1. **商品管理**タブで商品を登録
    2. **検索実行**タブで順位を取得
    3. **ダッシュボード**で結果を確認
    """)
    
    st.divider()
    
    st.header("📊 統計")
    products = get_products()
    rankings = get_rankings()
    
    st.metric("登録商品数", len(products))
    st.metric("データ件数", len(rankings))
    
    st.divider()
    
    # 管理者機能
    with st.expander("🔧 管理者機能"):
        st.warning("⚠️ 注意：これらの操作は取り消せません")
        
        if st.button("🗑️ すべてのデータをクリア", type="secondary"):
            if db_products and db_rankings:
                # Detaのデータをクリア
                try:
                    # すべてのアイテムを取得して削除
                    products = db_products.fetch()
                    for item in products.items:
                        db_products.delete(item['key'])
                    
                    rankings = db_rankings.fetch()
                    for item in rankings.items:
                        db_rankings.delete(item['key'])
                    
                    st.cache_data.clear()
                    st.success("データをクリアしました")
                    st.rerun()
                except:
                    st.error("データのクリアに失敗しました")
            else:
                # ローカルモード
                if 'products' in st.session_state:
                    st.session_state.products = []
                if 'rankings' in st.session_state:
                    st.session_state.rankings = []
                st.rerun()
        
        if db_products:
            st.info("🌐 Deta Cloud接続中")
        else:
            st.info("💻 ローカルモード")