# fashion_news

毎朝、日本語のファッションニュースを RSS から集め、Notion の親ページの下に日次ページ（見出し+リンク）を作ります。
要件は [REQUIREMENTS.md](REQUIREMENTS.md) を参照。

## セットアップ
1. Notion で内部インテグレーションを作り、親ページ「毎日のファッションニュース」に接続する。
2. このリポジトリの Settings → Secrets and variables → Actions に登録する。
   - `NOTION_TOKEN`: インテグレーションのトークン
   - `NOTION_PARENT_PAGE_ID`: `e76065314b0e4bbe87c1ea93b35ef8b5`
3. Actions タブの daily-fashion-news → Run workflow で手動実行し、Notion にページができ、ログで各情報源が取得できていることを確認する。
4. 以降は毎日 6:30 JST（朝刊）と 17:30 JST（夕刊）に自動実行される。

## ローカルでの実行
```bash
pip install -r requirements-dev.txt
PYTHONPATH=src python -m fashion_news --dry-run   # Notion に書かず表示
PYTHONPATH=src python -m pytest
```

## カスタマイズ
- 情報源: `config/sources.yaml`
- ジャンルのキーワード: `config/categories.yaml`
- 掲載済み URL の履歴: `data/seen_urls.json`（30日分を自動で保持）
