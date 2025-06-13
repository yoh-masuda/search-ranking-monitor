// グローバル変数
let chartInstance = null;
let productsData = [];

// ページ読み込み時の処理
document.addEventListener('DOMContentLoaded', function() {
    loadOptions();
    loadProducts();
    updateChart();
    
    // フォームのイベントリスナー
    document.getElementById('product-form').addEventListener('submit', handleProductSubmit);
});

// タブ切り替え
function showTab(tabName) {
    // すべてのタブコンテンツを非表示
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // すべてのタブボタンを非アクティブ
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // 選択されたタブを表示
    document.getElementById(tabName).classList.add('active');
    
    // 対応するボタンをアクティブ
    event.target.classList.add('active');
}

// オプションを読み込み
async function loadOptions() {
    try {
        const response = await axios.get('/api/options');
        if (response.data.status === 'success') {
            const skuFilter = document.getElementById('sku-filter');
            const searchSku = document.getElementById('search-sku');
            
            // SKUフィルタを更新
            skuFilter.innerHTML = '<option value="">すべて</option>';
            searchSku.innerHTML = '<option value="">すべての商品</option>';
            
            response.data.sku_names.forEach(sku => {
                skuFilter.innerHTML += `<option value="${sku}">${sku}</option>`;
                searchSku.innerHTML += `<option value="${sku}">${sku}</option>`;
            });
        }
    } catch (error) {
        console.error('オプション読み込みエラー:', error);
    }
}

// キーワードフィルタを更新
async function updateKeywords() {
    const skuName = document.getElementById('sku-filter').value;
    const keywordFilter = document.getElementById('keyword-filter');
    
    try {
        const response = await axios.get('/api/rankings/history', {
            params: { sku_name: skuName }
        });
        
        if (response.data.status === 'success') {
            const keywords = [...new Set(response.data.data.map(item => item.キーワード))];
            
            keywordFilter.innerHTML = '<option value="">すべて</option>';
            keywords.forEach(keyword => {
                keywordFilter.innerHTML += `<option value="${keyword}">${keyword}</option>`;
            });
        }
    } catch (error) {
        console.error('キーワード更新エラー:', error);
    }
}

// グラフを更新
async function updateChart() {
    const skuName = document.getElementById('sku-filter').value;
    const keyword = document.getElementById('keyword-filter').value;
    const days = document.getElementById('period-filter').value;
    
    try {
        const response = await axios.get('/api/rankings/history', {
            params: {
                sku_name: skuName,
                keyword: keyword,
                days: days
            }
        });
        
        if (response.data.status === 'success') {
            const data = response.data.data;
            
            // グラフデータを準備
            const dates = [...new Set(data.map(item => item.日付))].sort();
            
            // SKUとキーワードの組み合わせを取得
            const combinations = {};
            data.forEach(item => {
                const key = `${item.SKU名} - ${item.キーワード}`;
                if (!combinations[key]) {
                    combinations[key] = {
                        amazon: {},
                        rakuten: {}
                    };
                }
                combinations[key].amazon[item.日付] = item.Amazon順位;
                combinations[key].rakuten[item.日付] = item.楽天順位;
            });
            
            // データセットを作成
            const datasets = [];
            const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'];
            let colorIndex = 0;
            
            Object.keys(combinations).forEach(key => {
                const color = colors[colorIndex % colors.length];
                
                // Amazon
                datasets.push({
                    label: `${key} (Amazon)`,
                    data: dates.map(date => combinations[key].amazon[date] || null),
                    borderColor: color,
                    backgroundColor: color + '33',
                    borderWidth: 2,
                    pointRadius: 4,
                    tension: 0.1
                });
                
                // 楽天
                datasets.push({
                    label: `${key} (楽天)`,
                    data: dates.map(date => combinations[key].rakuten[date] || null),
                    borderColor: color,
                    backgroundColor: color + '33',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 4,
                    tension: 0.1
                });
                
                colorIndex++;
            });
            
            // グラフを描画
            drawChart(dates, datasets);
            
            // 統計を更新
            updateStats(data);
        }
    } catch (error) {
        console.error('グラフ更新エラー:', error);
    }
}

// グラフを描画
function drawChart(labels, datasets) {
    const ctx = document.getElementById('rankingChart').getContext('2d');
    
    // 既存のチャートを破棄
    if (chartInstance) {
        chartInstance.destroy();
    }
    
    chartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '検索順位推移',
                    font: {
                        size: 16
                    }
                },
                legend: {
                    display: true,
                    position: 'bottom'
                }
            },
            scales: {
                y: {
                    reverse: true,
                    beginAtZero: false,
                    min: 1,
                    ticks: {
                        stepSize: 1
                    },
                    title: {
                        display: true,
                        text: '順位'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: '日付'
                    }
                }
            }
        }
    });
}

// 統計を更新
function updateStats(data) {
    if (data.length === 0) {
        document.getElementById('amazon-best').textContent = '-';
        document.getElementById('rakuten-best').textContent = '-';
        document.getElementById('last-update').textContent = '-';
        return;
    }
    
    // Amazon最高順位
    const amazonRanks = data.filter(d => d.Amazon順位).map(d => d.Amazon順位);
    const amazonBest = amazonRanks.length > 0 ? Math.min(...amazonRanks) : null;
    document.getElementById('amazon-best').textContent = amazonBest ? `${amazonBest}位` : '圏外';
    
    // 楽天最高順位
    const rakutenRanks = data.filter(d => d.楽天順位).map(d => d.楽天順位);
    const rakutenBest = rakutenRanks.length > 0 ? Math.min(...rakutenRanks) : null;
    document.getElementById('rakuten-best').textContent = rakutenBest ? `${rakutenBest}位` : '圏外';
    
    // 最終更新
    const lastDate = data.map(d => d.日付).sort().pop();
    document.getElementById('last-update').textContent = lastDate || '-';
}

// 商品一覧を読み込み
async function loadProducts() {
    try {
        const response = await axios.get('/api/products');
        if (response.data.status === 'success') {
            productsData = response.data.data;
            displayProducts();
        }
    } catch (error) {
        console.error('商品読み込みエラー:', error);
    }
}

// 商品一覧を表示
function displayProducts() {
    const tbody = document.querySelector('#products-table tbody');
    tbody.innerHTML = '';
    
    productsData.forEach(product => {
        const row = document.createElement('tr');
        
        // URLを短く表示（ASINまたは商品IDのみ）
        let amazonDisplay = '-';
        if (product.asin) {
            amazonDisplay = `<a href="${product.amazon_url || `https://www.amazon.co.jp/dp/${product.asin}`}" target="_blank" class="product-link">ASIN: ${product.asin}</a>`;
        } else if (product.amazon_url) {
            const asinMatch = product.amazon_url.match(/\/dp\/([A-Z0-9]{10})/);
            if (asinMatch) {
                amazonDisplay = `<a href="${product.amazon_url}" target="_blank" class="product-link">ASIN: ${asinMatch[1]}</a>`;
            } else {
                amazonDisplay = `<a href="${product.amazon_url}" target="_blank" class="product-link">Amazon商品</a>`;
            }
        }
        
        let rakutenDisplay = '-';
        if (product.rakuten_url) {
            const idMatch = product.rakuten_url.match(/\/([^\/]+)\/([^\/\?]+)/);
            if (idMatch && idMatch[2]) {
                rakutenDisplay = `<a href="${product.rakuten_url}" target="_blank" class="product-link">楽天ID: ${idMatch[2]}</a>`;
            } else {
                rakutenDisplay = `<a href="${product.rakuten_url}" target="_blank" class="product-link">楽天商品</a>`;
            }
        }
        
        // 最新順位情報を整理
        let latestRankings = '';
        if (product.latest_rankings && Object.keys(product.latest_rankings).length > 0) {
            const rankings = [];
            for (const [keyword, data] of Object.entries(product.latest_rankings)) {
                const amazonRank = data.amazon ? `A:${data.amazon}位` : 'A:圏外';
                const rakutenRank = data.rakuten ? `R:${data.rakuten}位` : 'R:圏外';
                rankings.push(`<div class="ranking-item"><strong>${keyword}</strong>: ${amazonRank} / ${rakutenRank}<br><small class="date-info">${data.date}</small></div>`);
            }
            latestRankings = rankings.join('');
        } else {
            latestRankings = '<span class="no-data">データなし</span>';
        }
        
        row.innerHTML = `
            <td>${product.sku_name}</td>
            <td>${amazonDisplay}</td>
            <td>${rakutenDisplay}</td>
            <td class="keywords-cell">${product.keywords.join(', ')}</td>
            <td class="rankings-cell">${latestRankings}</td>
            <td>
                <button class="btn btn-secondary" onclick="editProduct(${product.row_number})">編集</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// キーワード入力欄を追加
function addKeywordInput() {
    const container = document.getElementById('keywords-container');
    const inputCount = container.querySelectorAll('.keyword-input').length;
    
    if (inputCount < 10) {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'keyword-input';
        input.placeholder = `キーワード${inputCount + 1}`;
        container.appendChild(input);
    } else {
        alert('キーワードは最大10個まで登録できます。');
    }
}

// 商品登録フォームの送信
async function handleProductSubmit(event) {
    event.preventDefault();
    
    const keywordInputs = document.querySelectorAll('.keyword-input');
    const keywords = Array.from(keywordInputs)
        .map(input => input.value.trim())
        .filter(kw => kw !== '');
    
    const productData = {
        sku_name: document.getElementById('sku-name').value,
        amazon_url: document.getElementById('amazon-url').value,
        rakuten_url: document.getElementById('rakuten-url').value,
        keywords: keywords
    };
    
    try {
        const response = await axios.post('/api/products', productData);
        if (response.data.status === 'success') {
            alert('商品を登録しました！');
            document.getElementById('product-form').reset();
            document.getElementById('keywords-container').innerHTML = 
                '<input type="text" class="keyword-input" placeholder="キーワード1">';
            loadProducts();
            loadOptions();
        }
    } catch (error) {
        alert('エラーが発生しました: ' + error.response.data.message);
    }
}

// 検索を実行
async function runSearch() {
    const button = document.querySelector('#search button');
    const buttonText = document.getElementById('search-button-text');
    const spinner = document.getElementById('search-spinner');
    const resultDiv = document.getElementById('search-result');
    
    // ボタンを無効化
    button.disabled = true;
    buttonText.textContent = '検索中...';
    spinner.style.display = 'inline-block';
    resultDiv.classList.remove('show');
    
    const skuName = document.getElementById('search-sku').value;
    
    try {
        const response = await axios.post('/api/run-search', {
            sku_name: skuName
        });
        
        if (response.data.status === 'success') {
            resultDiv.innerHTML = `
                <h3>✅ 検索完了</h3>
                <p>${response.data.message}</p>
                <p>ダッシュボードタブで結果を確認できます。</p>
            `;
            resultDiv.classList.add('show');
            
            // グラフを更新
            loadOptions();
            updateChart();
        }
    } catch (error) {
        resultDiv.innerHTML = `
            <h3>❌ エラー</h3>
            <p>${error.response.data.message}</p>
        `;
        resultDiv.classList.add('show');
    } finally {
        // ボタンを有効化
        button.disabled = false;
        buttonText.textContent = '検索を実行';
        spinner.style.display = 'none';
    }
}