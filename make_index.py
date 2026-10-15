"""
インデックスページ生成
feeds/*.xml の一覧をブラウザで見られるHTMLに出力
"""
import datetime as dt
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CFG = ROOT / "config" / "sources.yaml"
FEEDS_DIR = ROOT / "feeds"
OUT = ROOT / "index.html"

CATEGORY_LABEL = {
    "government": "政府・規制",
    "financial": "金融・銀行・暗号",
    "tech": "Tech / AI / サイバー",
    "retail": "小売 / 関税",
    "food": "飲食 / 食品",
    "realestate": "住宅・不動産",
    "telecom": "通信",
    "publicservice": "公共サービス",
    "energy": "エネルギー",
    "labor": "人材・労働・移民",
    "logistics": "物流・運輸",
    "environment": "環境",
    "business": "ビジネス",
    "voicetracking": "🗣 一般市民の声 (Reddit)",
    "legal": "法務・判例",
}

PRIO_COLOR = {
    "critical": "#dc2626",
    "high": "#ea580c",
    "medium": "#ca8a04",
    "low": "#65a30d",
}


def count_items(xml_path: Path) -> int:
    if not xml_path.exists():
        return 0
    text = xml_path.read_text(encoding="utf-8")
    return len(re.findall(r"<entry>", text)) + len(re.findall(r"<item>", text))


def main():
    cfg = yaml.safe_load(CFG.read_text(encoding="utf-8"))
    sources = cfg["sources"]
    cats = {}
    for s in sources:
        cats.setdefault(s["category"], []).append(s)

    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = []
    for cat, items in sorted(cats.items()):
        for s in items:
            xml = FEEDS_DIR / f"{s['id']}.xml"
            n = count_items(xml)
            status = "✅" if n > 0 else "❌"
            rows.append((cat, s, n, status))

    html = ["""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<title>US専門ニュース・制度変更トラッカー</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 1100px; margin: 32px auto; padding: 0 16px; color: #1f2937; }
  h1 { font-size: 1.6em; }
  .meta { color: #6b7280; font-size: 0.9em; }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; }
  th, td { padding: 8px 12px; border-bottom: 1px solid #e5e7eb; text-align: left;
           font-size: 0.9em; }
  th { background: #f9fafb; font-weight: 600; }
  .cat { background: #f3f4f6; font-weight: 600; color: #4b5563; }
  .prio { display: inline-block; padding: 2px 6px; border-radius: 4px; color: white;
          font-size: 0.75em; }
  .endpoint { font-family: monospace; font-size: 0.8em; color: #6b7280; }
  a { color: #2563eb; text-decoration: none; }
  a:hover { text-decoration: underline; }
</style></head><body>"""]

    html.append(f"<h1>🇺🇸 US 専門ニュース・制度変更トラッカー</h1>")
    html.append(f'<div class="meta">最終更新: {now} ・ '
                f'{sum(1 for _,_,n,_ in rows if n>0)}/{len(rows)} フィード稼働中</div>')
    html.append('<p>アメリカ政府・規制・金融・小売・飲食・労働などの専門ニュースを自動集約し、'
                'Atom 2.0 形式で配信。RSSリーダに登録してご利用ください。</p>')

    html.append("<table>")
    html.append("<tr><th>ステータス</th><th>カテゴリ</th><th>タイトル</th>"
                "<th>優先度</th><th>取得元</th><th>件数</th></tr>")

    current_cat = None
    for cat, s, n, status in rows:
        if cat != current_cat:
            html.append(f'<tr class="cat"><td colspan="6">'
                        f'{CATEGORY_LABEL.get(cat, cat)} ({cat})</td></tr>')
            current_cat = cat
        prio = s.get("priority", "low")
        color = PRIO_COLOR.get(prio, "#6b7280")
        ep = (s.get("endpoint") or s.get("list_endpoint", "—"))[:55]
        html.append(
            f'<tr><td>{status}</td><td>—</td>'
            f'<td><a href="feeds/{s["id"]}.xml">{s["title"]}</a></td>'
            f'<td><span class="prio" style="background:{color}">{prio}</span></td>'
            f'<td class="endpoint">{ep}</td>'
            f'<td>{n}</td></tr>'
        )

    html.append("</table>")
    html.append("<h2>使い方</h2>")
    html.append("<ul>")
    html.append("<li><b>RSSリーダ</b>: Feedly, NetNewsWire, Inoreader などに "
                "<code>feeds/&lt;id&gt;.xml</code> を登録</li>")
    html.append("<li><b>全件Atom</b>: 個別フィードを1つずつ、またはこのマスタを流して "
                "カスタムパイプラインへ</li>")
    html.append("<li><b>更新</b>: <code>python aggregator.py --fetch-all</code> で再生成"
                "</li>")
    html.append("</ul>")
    html.append("</body></html>")

    OUT.write_text("\n".join(html), encoding="utf-8")
    print(f"WROTE {OUT}  ({OUT.stat().st_size} bytes)")
    print(f"稼働中: {sum(1 for _,_,n,_ in rows if n>0)}/{len(rows)} フィード")


if __name__ == "__main__":
    main()