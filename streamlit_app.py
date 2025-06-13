"""
Streamlit版 検索順位モニタリングアプリ
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ページ設定
st.set_page_config(
    page_title="Amazon・楽天 検索順位モニタリング",
    page_icon="🔍",
    layout="wide"
)

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
</style>
""", unsafe_allow_html=True)

# タイトル
st.title("🔍 Amazon・楽天 検索順位モニタリング")

# セッション状態の初期化
if 'products' not in st.session_state:
    st.session_state.products = []
if 'rankings' not in st.session_state:
    st.session_state.rankings = []

# タブ
tab1, tab2, tab3 = st.tabs(["📊 ダッシュボード", "📦 商品管理", "🔄 検索実行"])

# ダッシュボードタブ
with tab1:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        selected_product = st.selectbox(
            "商品選択",
            ["すべて"] + [p['name'] for p in st.session_state.products]
        )
    
    with col2:
        if selected_product != "すべて":
            product = next((p for p in st.session_state.products if p['name'] == selected_product), None)
            if product:
                selected_keyword = st.selectbox(
                    "キーワード",
                    ["すべて"] + product['keywords']
                )
        else:
            selected_keyword = "すべて"
    
    with col3:
        period = st.selectbox(
            "期間",
            ["過去7日間", "過去30日間", "過去90日間", "過去1年間"]
        )
    
    with col4:
        if st.button("🔄 グラフ更新", type="primary"):
            st.rerun()
    
    # グラフ表示
    if st.session_state.rankings:
        df = pd.DataFrame(st.session_state.rankings)
        
        # フィルタリング
        if selected_product != "すべて":
            df = df[df['product'] == selected_product]
        if selected_keyword != "すべて":
            df = df[df['keyword'] == selected_keyword]
        
        if not df.empty:
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
                    fig.add_trace(go.Scatter(
                        x=data['date'],
                        y=data['amazon_rank'],
                        mode='lines+markers',
                        name=f"{product} - {keyword} (Amazon)",
                        line=dict(width=2),
                        marker=dict(size=8)
                    ))
                    
                    # 楽天
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
            
            # 統計情報
            col1, col2, col3 = st.columns(3)
            
            with col1:
                amazon_best = df[df['amazon_rank'].notna()]['amazon_rank'].min()
                st.metric("Amazon最高順位", f"{int(amazon_best)}位" if pd.notna(amazon_best) else "データなし")
            
            with col2:
                rakuten_best = df[df['rakuten_rank'].notna()]['rakuten_rank'].min()
                st.metric("楽天最高順位", f"{int(rakuten_best)}位" if pd.notna(rakuten_best) else "データなし")
            
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
                st.session_state.products.append({
                    'name': product_name,
                    'amazon_url': amazon_url,
                    'rakuten_url': rakuten_url,
                    'asin': asin,
                    'keywords': keyword_list
                })
                
                st.success("商品を登録しました！")
                st.rerun()
            else:
                st.error("必須項目を入力してください")
    
    st.divider()
    
    st.subheader("登録済み商品")
    
    if st.session_state.products:
        for i, product in enumerate(st.session_state.products):
            with st.expander(f"📦 {product['name']}"):
                col1, col2, col3 = st.columns([2, 2, 1])
                
                with col1:
                    st.write(f"**Amazon:** {product['asin'] or 'なし'}")
                    if product['amazon_url']:
                        st.link_button("Amazonで見る", product['amazon_url'])
                
                with col2:
                    st.write(f"**楽天:** {'あり' if product['rakuten_url'] else 'なし'}")
                    if product['rakuten_url']:
                        st.link_button("楽天で見る", product['rakuten_url'])
                
                with col3:
                    if st.button(f"削除", key=f"delete_{i}"):
                        st.session_state.products.pop(i)
                        st.rerun()
                
                st.write(f"**キーワード:** {', '.join(product['keywords'])}")
                
                # 最新順位を表示
                latest_rankings = [r for r in st.session_state.rankings if r['product'] == product['name']]
                if latest_rankings:
                    st.write("**最新順位:**")
                    for keyword in product['keywords']:
                        kr = [r for r in latest_rankings if r['keyword'] == keyword]
                        if kr:
                            latest = sorted(kr, key=lambda x: x['date'])[-1]
                            amazon = f"A:{latest['amazon_rank']}位" if latest['amazon_rank'] else "A:圏外"
                            rakuten = f"R:{latest['rakuten_rank']}位" if latest['rakuten_rank'] else "R:圏外"
                            st.write(f"- {keyword}: {amazon} / {rakuten} ({latest['date']})")
    else:
        st.info("商品が登録されていません")

# 検索実行タブ
with tab3:
    st.subheader("検索実行")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        target_product = st.selectbox(
            "対象商品",
            ["すべての商品"] + [p['name'] for p in st.session_state.products]
        )
    
    with col2:
        if st.button("🔍 検索を実行", type="primary"):
            if st.session_state.products:
                with st.spinner("検索を実行中..."):
                    # ダミーデータを追加（実際の実装では検索処理を行う）
                    import random
                    today = datetime.now().strftime('%Y-%m-%d')
                    
                    products_to_search = st.session_state.products
                    if target_product != "すべての商品":
                        products_to_search = [p for p in st.session_state.products if p['name'] == target_product]
                    
                    count = 0
                    for product in products_to_search:
                        for keyword in product['keywords']:
                            # ランダムな順位を生成（デモ用）
                            amazon_rank = random.choice([None, 1, 2, 3, 5, 8, 12, 20, 35])
                            rakuten_rank = random.choice([None, 1, 3, 5, 7, 10, 15, 25, 40])
                            
                            st.session_state.rankings.append({
                                'date': today,
                                'product': product['name'],
                                'keyword': keyword,
                                'amazon_rank': amazon_rank,
                                'rakuten_rank': rakuten_rank
                            })
                            count += 1
                    
                    st.success(f"✅ {count}件の検索結果を取得しました！")
                    st.balloons()
            else:
                st.error("商品が登録されていません")
    
    st.divider()
    
    # 実行履歴
    st.subheader("実行履歴")
    
    if st.session_state.rankings:
        df = pd.DataFrame(st.session_state.rankings)
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
    st.metric("登録商品数", len(st.session_state.products))
    st.metric("データ件数", len(st.session_state.rankings))
    
    st.divider()
    
    if st.button("🗑️ すべてのデータをクリア"):
        st.session_state.products = []
        st.session_state.rankings = []
        st.rerun()