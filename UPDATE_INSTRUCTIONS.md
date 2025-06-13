# スプレッドシートの列構成変更手順

## 新しい列構成

以下の順番で列を設定してください：

| A列 | B列 | C列 | D列 | E列 | F列以降 |
|-----|-----|-----|-----|-----|---------|
| 商品名 | Amazon URL | 楽天URL | KW1 | KW2 | KW3... |

## 変更手順

1. **既存のスプレッドシートを開く**

2. **1行目のヘッダーを以下のように変更：**
   - A1: 商品名
   - B1: Amazon URL
   - C1: 楽天URL
   - D1: KW1
   - E1: KW2
   - F1: KW3
   - （必要に応じて追加）

3. **2行目以降にデータを入力：**
   - A列: 商品名（例：リノンロックオイル）
   - B列: Amazon商品URL（例：https://www.amazon.co.jp/dp/B08XXXXX）
   - C列: 楽天商品URL（例：https://item.rakuten.co.jp/shop/product/）
   - D列以降: 検索キーワード

## 注意事項

- ASINを手動で入力する必要はありません。Amazon URLから自動的に抽出されます
- Amazon URLは以下の形式に対応しています：
  - https://www.amazon.co.jp/dp/B01XXXXX
  - https://www.amazon.co.jp/gp/product/B01XXXXX
  - https://www.amazon.co.jp/商品名/dp/B01XXXXX

## 実行確認

スプレッドシートを更新したら、ツールを実行してください：

```bash
cd /Users/senjin/search-ranking-monitor
source venv/bin/activate
python src/main.py
```