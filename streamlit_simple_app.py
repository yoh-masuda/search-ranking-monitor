"""
Streamlit版 検索順位モニタリングアプリ（シンプル版）
データはJSONファイルで保存
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

# ページ設定
st.set_page_config(
    page_title="Amazon・楽天 検索順位モニタリング",
    page_icon="🔍",
    layout="wide"
)

# データファイル
DATA_FILE = "data.json"

# データの読み込み
def load_data():
    """データをJSONファイルから読み込む"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"products": [], "rankings": []}

# データの保存
def save_data(data):
    """データをJSONファイルに保存"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 初期データ読み込み
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# データ取得関数
def get_products():
    """商品リストを取得"""
    return st.session_state.data.get('products', [])

def get_rankings():
    """ランキングデータを取得"""
    return st.session_state.data.get('rankings', [])

def add_product(product_data):
    """商品を追加"""
    products = st.session_state.data.get('products', [])
    products.append(product_data)
    st.session_state.data['products'] = products
    save_data(st.session_state.data)
    return True

def add_ranking(ranking_data):
    """ランキングデータを追加"""
    rankings = st.session_state.data.get('rankings', [])
    rankings.append(ranking_data)
    st.session_state.data['rankings'] = rankings
    save_data(st.session_state.data)
    return True

def delete_product(index):
    """商品を削除"""
    products = st.session_state.data.get('products', [])
    if 0 <= index < len(products):
        products.pop(index)
        st.session_state.data['products'] = products
        save_data(st.session_state.data)
        return True
    return False

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
    .product-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# タイトル
st.title("🔍 Amazon・楽天 検索順位モニタリング")

# 自動更新チェック
def check_auto_update():
    """最後の更新から24時間経過していたら自動更新"""
    data = load_data()
    rankings = data.get('rankings', [])
    
    if rankings:
        # 最新の日付を取得
        df = pd.DataFrame(rankings)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            last_update = df['date'].max()
            
            # 現在時刻との差を計算
            now = pd.Timestamp.now()
            hours_since_update = (now - last_update).total_seconds() / 3600
            
            # 24時間以上経過していたら自動更新
            if hours_since_update >= 24:
                return True
    return False

# 自動更新実行
if check_auto_update():
    with st.info("🔄 24時間以上経過したため、自動更新を実行中..."):
        products = get_products()
        if products:
            import random
            today = datetime.now().strftime('%Y-%m-%d')
            count = 0
            
            for product in products:
                for keyword in product.get('keywords', []):
                    # ランダムな順位を生成（デモ用）
                    amazon_rank = random.choice([None, 1, 2, 3, 5, 8, 12, 20, 35])
                    rakuten_rank = random.choice([None, 1, 3, 5, 7, 10, 15, 25, 40])
                    
                    ranking_data = {
                        'date': today,
                        'product': product.get('name', ''),
                        'keyword': keyword,
                        'amazon_rank': amazon_rank,
                        'rakuten_rank': rakuten_rank
                    }
                    
                    add_ranking(ranking_data)
                    count += 1
            
            st.success(f"✅ 自動更新完了！{count}件の順位を取得しました")
            st.session_state.data = load_data()

# データ状態の表示
if os.path.exists(DATA_FILE):
    st.success("📁 データファイルモード：data.jsonに保存中")
else:
    st.info("📁 新規データファイルを作成します")

# タブ
tab1, tab2, tab3 = st.tabs(["📊 ダッシュボード", "📦 商品管理", "🔄 検索実行"])

# ダッシュボードタブ
with tab1:
    # データを取得
    products = get_products()
    rankings = get_rankings()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        product_names = [p.get('name', '') for p in products]
        selected_product = st.selectbox(
            "商品選択",
            ["すべて"] + product_names
        )
    
    with col2:
        if selected_product != "すべて":
            product = next((p for p in products if p.get('name', '') == selected_product), None)
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
            st.session_state.data = load_data()
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
                
                fig.update_layout(
                    yaxis=dict(autorange="reversed", title="順位"),
                    xaxis=dict(title="日付"),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                st.error(f"グラフの表示中にエラーが発生しました: {str(e)}")
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
                    
                    # 登録と同時に初回検索を実行
                    with st.spinner("初回検索を実行中..."):
                        import random
                        today = datetime.now().strftime('%Y-%m-%d')
                        
                        for keyword in keyword_list:
                            # ランダムな順位を生成（デモ用）
                            amazon_rank = random.choice([None, 1, 2, 3, 5, 8, 12, 20, 35])
                            rakuten_rank = random.choice([None, 1, 3, 5, 7, 10, 15, 25, 40])
                            
                            ranking_data = {
                                'date': today,
                                'product': product_name,
                                'keyword': keyword,
                                'amazon_rank': amazon_rank,
                                'rakuten_rank': rakuten_rank
                            }
                            
                            add_ranking(ranking_data)
                    
                    st.success(f"✅ 初回検索完了！{len(keyword_list)}件の順位を取得しました")
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
                    if st.button(f"削除", key=f"delete_{i}"):
                        if delete_product(i):
                            st.rerun()
                
                if 'keywords' in product:
                    st.write(f"**キーワード:** {', '.join(product['keywords'])}")
                
                # 最新順位を表示
                product_name = product.get('name', '')
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
        product_names = [p.get('name', '') for p in products]
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
                        products_to_search = [p for p in products if p.get('name', '') == target_product]
                    
                    count = 0
                    for product in products_to_search:
                        for keyword in product.get('keywords', []):
                            # ランダムな順位を生成（デモ用）
                            amazon_rank = random.choice([None, 1, 2, 3, 5, 8, 12, 20, 35])
                            rakuten_rank = random.choice([None, 1, 3, 5, 7, 10, 15, 25, 40])
                            
                            ranking_data = {
                                'date': today,
                                'product': product.get('name', ''),
                                'keyword': keyword,
                                'amazon_rank': amazon_rank,
                                'rakuten_rank': rakuten_rank
                            }
                            
                            add_ranking(ranking_data)
                            count += 1
                    
                    st.success(f"✅ {count}件の検索結果を取得しました！")
                    st.balloons()
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
    
    # 最終更新時刻
    if rankings:
        df = pd.DataFrame(rankings)
        if 'date' in df.columns:
            last_date = pd.to_datetime(df['date']).max()
            st.metric("最終更新", last_date.strftime('%Y-%m-%d'))
            
            # 次回更新予定
            next_update = last_date + timedelta(days=1)
            st.info(f"🕐 次回自動更新: {next_update.strftime('%Y-%m-%d')}")
    
    st.divider()
    
    # データファイル情報
    if os.path.exists(DATA_FILE):
        file_size = os.path.getsize(DATA_FILE)
        st.info(f"💾 データファイル: {file_size:,} bytes")
    
    # 管理者機能
    with st.expander("🔧 管理者機能"):
        st.warning("⚠️ 注意：これらの操作は取り消せません")
        
        if st.button("🗑️ すべてのデータをクリア", type="secondary"):
            st.session_state.data = {"products": [], "rankings": []}
            save_data(st.session_state.data)
            st.success("データをクリアしました")
            st.rerun()
        
        if st.button("💾 データをダウンロード"):
            json_str = json.dumps(st.session_state.data, ensure_ascii=False, indent=2)
            st.download_button(
                label="data.jsonをダウンロード",
                data=json_str,
                file_name="data.json",
                mime="application/json"
            )
        
        # サンプルデータ読み込み
        if st.button("📊 サンプルデータを読み込む"):
            if os.path.exists("sample_data.json"):
                with open("sample_data.json", 'r', encoding='utf-8') as f:
                    sample_data = json.load(f)
                st.session_state.data = sample_data
                save_data(st.session_state.data)
                st.success("サンプルデータを読み込みました！")
                st.rerun()
            else:
                st.error("sample_data.jsonが見つかりません")