# 🚀 デプロイ手順（みんなでデータを共有）

## 1. Deta Spaceでデータベースを作成（無料）

1. [Deta Space](https://deta.space)にアクセス
2. アカウントを作成（無料）
3. 「Create a Project」をクリック
4. プロジェクト名を入力（例：search-ranking）
5. 作成されたら「Project Key」をコピー（後で使います）

## 2. GitHubにコードをアップロード

```bash
# GitHubで新しいリポジトリを作成してから
git init
git add .
git commit -m "初回コミット"
git remote add origin https://github.com/あなたのユーザー名/search-ranking-monitor.git
git push -u origin main
```

## 3. Streamlit Community Cloudでデプロイ

1. [Streamlit Community Cloud](https://share.streamlit.io)にアクセス
2. GitHubアカウントでログイン
3. 「New app」をクリック
4. 以下を設定：
   - Repository: `あなたのユーザー名/search-ranking-monitor`
   - Branch: `main`
   - Main file path: `streamlit_shared_app.py`

5. 「Advanced settings」をクリック
6. 「Secrets」に以下を入力：
   ```toml
   DETA_PROJECT_KEY = "コピーしたProject Key"
   ```

7. 「Deploy!」をクリック

## 4. 完成！

- URLが発行されます（例：`https://yourapp.streamlit.app`）
- このURLを知っている人は誰でもアクセス可能
- **全員が同じデータを見て、編集できます**

## 重要な注意事項

- データは全員で共有されます
- 誰かが商品を追加・削除すると、全員に反映されます
- 管理者機能でデータを削除すると、全員のデータが消えます

## オプション：アクセス制限

もしアクセス制限をかけたい場合は、以下の方法があります：

1. **Basic認証を追加**（コードの修正が必要）
2. **URLを秘密にする**（簡単だが完全ではない）
3. **Streamlit for Teamsを使う**（有料）

## トラブルシューティング

- **「DETA_PROJECT_KEY not found」エラー**: Secretsの設定を確認
- **データが保存されない**: Deta Spaceの接続を確認
- **アプリが起動しない**: requirements_streamlit.txtを確認