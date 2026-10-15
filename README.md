# US 専門ニュース・制度変更トラッカー

アメリカの政府機関・規制当局・金融/暗号資産・小売/関税・飲食/食品・不動産・労働・物流など、**制度変更と市場シグナルを自動検知する Atom 2.0 フィード集**。

## 仕組み

`aggregator.py` が `config/sources.yaml` に登録された各ソースを巡回し、HTML / JSON / RSS を **正規化 → Atom 2.0 として `feeds/` 配下に書き出す**。

4つの取得モード:

| mode | 説明 |
|---|---|
| `rss` | 公式 RSS をそのまま流用 |
| `govdelivery` | GovDelivery topic feed (無料・公式) |
| `api` | 公式 JSON/HTML API → Atom生成 |
| `scrape` | HTMLをスクレイプ → Atom生成 |

`adapters/<source_id>.py` に個別スクレイパを実装。未対応のサイトは `generic_scrape` にフォールバック。

## 使い方

```bash
python aggregator.py --list          # 全ソース一覧
python aggregator.py --fetch-all     # 全件再生成
python aggregator.py --fetch <id>    # 単体ソース

python make_index.py                 # index.html 生成
```

`feeds/` 配下に `<id>.xml` が出力される。RSS リーダや `index.html` から購読可能。

## 稼働状況 (2026-10-15)

- **53 ソース登録 / 45 フィード稼働 (85%)**
- 政府・規制、金融・暗号資産、Tech/AI、小売/関税、飲食/食品、住宅・不動産、人材/労働、物流/運輸、エネルギー、サイバーすべてに配信

## 残課題

| ID | 状態 | 対策案 |
|---|---|---|
| `federal_register_rss` | 一部で 500（一時的） | JSON APIで代替稼働中 |
| `occ_news` | スクレイパ未調整 | 構造調査のうえ書き直し |
| `usps` | JS レンダリング | GovDelivery経由 |
| `fsis_recalls` / `ferc` / `fmcsa` | IP/地域で 403 | GovDelivery経由 or クラウドIP |
| `nlrb` | 接続タイムアウト | リトライ機構追加 |
| `usps` press | JSレンダリング | GovDelivery |

## 構造

```
us-news-rss/
├── aggregator.py          # 集約器本体
├── make_index.py          # インデックスHTML生成
├── config/sources.yaml    # ソース一覧（マスタ）
├── adapters/              # 個別スクレイパ
│   ├── occ_news.py
│   ├── uscis.py
│   ├── cfpb.py
│   └── ...
├── feeds/                 # 生成された Atom フィード
├── logs/                  # 実行ログ
└── index.html             # ブラウザで閲覧できる一覧
```

## 次の一手

1. **GitHub Pages で公開**: `feeds/` + `index.html` をpush、`https://<user>.github.io/us-news-rss/feeds/<id>.xml` として配信
2. **定期実行**: GitHub Actions で 30 分ごとに `aggregator.py --fetch-all` を回す
3. **失敗ソースの自動GovDeliveryフォールバック**: 3回連続で失敗 → GovDelivery URL に自動切替
4. **通知**: 重要フィード (priority=critical) で新規エントリ → Slack/Discord webhook
5. **レポーティング**: フィードタイトルからキーワード抽出 → 日次ダイジェスト Markdown