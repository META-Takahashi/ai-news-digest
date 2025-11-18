import os
from datetime import datetime, timedelta, timezone
import requests
import xml.etree.ElementTree as ET

from openai import OpenAI


# ===== 環境変数 =====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Google News のAI関連RSS（必要に応じて入れ替えてOK）
RSS_FEEDS = [
    # 生成AI全般（日本語）
    "https://news.google.com/rss/search?q=生成AI+OR+AI+when:1d&hl=ja&gl=JP&ceid=JP:ja",
    # 教育×AI
    "https://news.google.com/rss/search?q=教育+AI+when:1d&hl=ja&gl=JP&ceid=JP:ja",
    # 企業のAI活用
    "https://news.google.com/rss/search?q=企業+AI+導入+when:1d&hl=ja&gl=JP&ceid=JP:ja",
]


# ===== RSS から記事を取得 =====
def fetch_articles_from_rss(max_articles: int = 10):
    articles = []
    seen_links = set()

    for feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"RSS取得エラー: {feed_url} - {e}")
            continue

        try:
            root = ET.fromstring(resp.text)
        except Exception as e:
            print(f"RSS解析エラー: {feed_url} - {e}")
            continue

        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")

            title = title_el.text if title_el is not None else ""
            link = link_el.text if link_el is not None else ""
            desc = desc_el.text if desc_el is not None else ""

            if not title or not link:
                continue
            if link in seen_links:
                continue

            seen_links.add(link)
            articles.append(
                {
                    "title": title.strip(),
                    "link": link.strip(),
                    "summary": (desc or "").strip(),
                }
            )

            if len(articles) >= max_articles:
                break
        if len(articles) >= max_articles:
            break

    return articles


# ===== OpenAIでダイジェストを生成 =====
def build_digest_with_openai(articles):
    """
    articles: [{title, link, summary}, ...]
    """

    # 日本時間
    today = datetime.now(timezone.utc) + timedelta(hours=9)
    date_str = today.strftime("%Y/%m/%d (%a)")

    if not articles:
        return f"""🎨 AIニュースダイジェスト（AI講師向け）
{date_str}
今日は取得できるAI関連ニュースが少なかったため、
新規トピックはありませんでした。

代わりに、最近の授業で扱えるテーマ例をいくつか：

- 生成AIと著作権
- AIとフェイクニュース
- 教育現場でのAI活用のメリット・デメリット
"""

    # モデルに渡す「ニュース一覧テキスト」
    sources_text_lines = []
    for i, a in enumerate(articles, start=1):
        sources_text_lines.append(
            f"{i}. タイトル: {a['title']}\n   URL: {a['link']}"
        )
        if a["summary"]:
            sources_text_lines.append(f"   概要候補: {a['summary']}")
    sources_text = "\n".join(sources_text_lines)

    prompt = f"""
あなたは「AI講師のためのニュース編集者」です。

## 目的
下記のニュースソース一覧だけを使って、
AI講師が授業や研修にすぐ活かせる“1日のまとめレター”を作成してください。

## 出力のトーン・ルール
- すべて日本語
- テキストはシンプルで読みやすく（余計な装飾は不要）
- 箇条書きは短く、1項目は最大2〜3行まで
- 見出しには最低限の絵文字はOK（例：🌟, 🏭, 🎓, 🛠️, 💡）
- 事実は必ず「ニュースソース一覧」に含まれる情報からのみ取り出すこと
- 想像で新しい企業名・サービス名・製品名を作らないこと
- 日付は必ず指定された日付を使うこと

## フォーマット（必ずこの形に従う）

🎨 AIニュースダイジェスト（AI講師向け）
{date_str}
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース
- 見出し1：要点（2〜3文）
- 見出し2：要点（2〜3文）

🏭 2. 企業のAI活用
- 事例1：要点（2〜3文）
- 事例2：要点（2〜3文）

🎓 3. 教育×AI 動向
- トピック1：要点（2〜3文）
- トピック2：要点（2〜3文）

🛠️ 4. AIツール最新アップデート
- ツール/サービス1：要点（2〜3文）
- ツール/サービス2：要点（2〜3文）

💡 5. 授業で使えるネタ・実践アイデア
- アイデア1（どんな授業で、どんな体験ができるかを1〜2文で）
- アイデア2
- アイデア3

## ニュースソース一覧
以下のニュースソースだけをもとに、上記フォーマットの本文を作成してください：

{sources_text}
"""

    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
    )
    return res.choices[0].message.content


# ===== 参考URLリストを作る =====
def build_reference_list(articles):
    if not articles:
        return "（本日のニュースソースは取得できませんでした）"

    lines = []
    for a in articles:
        # Markdown形式のリンク
        lines.append(f"- [{a['title']}]({a['link']})")
    return "\n".join(lines)


# ===== Lark へ送信 =====
def send_to_lark(text: str):
    if not LARK_WEBHOOK_URL:
        raise RuntimeError("LARK_WEBHOOK_URL が設定されていません。GitHub Secrets を確認してください。")

    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        },
    }
    resp = requests.post(LARK_WEBHOOK_URL, json=payload)
    resp.raise_for_status()


# ===== メイン処理 =====
def main():
    print("Fetching RSS articles...")
    articles = fetch_articles_from_rss(max_articles=10)

    print(f"Got {len(articles)} articles from RSS.")
    digest = build_digest_with_openai(articles)
    refs = build_reference_list(articles)

    message = f"""{digest}

────────────
🔗 参考URL（自動取得）
{refs}
"""

    print("Sending to Lark...")
    send_to_lark(message)
    print("Done!")


if __name__ == "__main__":
    main()
