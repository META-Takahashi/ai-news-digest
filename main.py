import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
import feedparser
from openai import OpenAI
import google.generativeai as genai  # 将来用（いまは未使用）


# ===== 環境変数（GitHub Secrets から来る） =====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ===== 日付ヘルパー（日本時間） =====
def get_today_jst():
    jst_now = datetime.now(timezone.utc) + timedelta(hours=9)
    date_str = jst_now.strftime("%Y/%m/%d (%a)")
    return date_str


# ===== ニュースRSSから実記事を取得 =====
def fetch_ai_articles(max_items=8):
    """AI関連ニュースのRSSをいくつか叩いて、タイトル・概要・URLを集める"""
    feeds = [
        # AI全般（Google News）
        "https://news.google.com/rss/search?q=人工知能+OR+AI+OR+生成AI&hl=ja&gl=JP&ceid=JP:ja",
        # TechCrunch AI
        "https://techcrunch.com/tag/artificial-intelligence/feed/",
        # The Verge AI
        "https://www.theverge.com/rss/artificial-intelligence/index.xml",
    ]

    articles = []
    for feed_url in feeds:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries:
            link = entry.get("link")
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()

            if not link or not title:
                continue

            domain = urlparse(link).netloc.replace("www.", "")
            articles.append(
                {
                    "title": title,
                    "summary": summary,
                    "link": link,
                    "source": domain,
                }
            )

    # 重複を簡易的に削る（URLベース）
    unique = {}
    for a in articles:
        if a["link"] not in unique:
            unique[a["link"]] = a

    articles = list(unique.values())[:max_items]
    return articles


# ===== OpenAI で「AI講師向けニュース」に整形 =====
def build_digest_with_openai(articles):
    today_str = get_today_jst()

    if not articles:
        base_news_list = "ニュース記事が取得できませんでした。AI講師向けの汎用トピックを出してください。"
    else:
        lines = []
        for i, a in enumerate(articles, start=1):
            lines.append(
                f"{i}. {a['title']}\n"
                f"   source: {a['source']}\n"
                f"   url   : {a['link']}\n"
                f"   summary: {a['summary'][:240]}..."
            )
        base_news_list = "\n\n".join(lines)

    prompt = f'''
あなたは「AI講師のためのニュース編集者」です。
以下の “実際のニュース記事リスト” をもとに、
Lark（スマホ）で読みやすい形のニュースダイジェストを作ってください。

# 前提
- 対象：AIリテラシーやAI活用を教える「講師・先生・研修担当」
- トーン：専門的だけど、噛み砕かれていて安心できる感じ
- 行間多め・セクションごとに空行を入れてスマホで読みやすく
- 箇条書き・見出し・絵文字を活用して、「流し読み」でも要点がわかること
- ニュースの内容は、下の「ニュース候補リスト」からのみ要約して使うこと
  （URLやタイトルを勝手に捏造しない）

# 出力フォーマット（この形を守る）

🎨 AIニュースダイジェスト（AI講師向け）
{today_str}
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース（2〜3本）
それぞれについて：
- タイトル
- 概要（2〜3文）
- 授業アイデア（「→」で始まる箇条書き 1〜2個）

🏭 2. 企業のAI活用（2本程度）
- どの業界で、どんなAI活用か
- その事例が授業でどう使えるか（ポイントを2〜3行）

🎓 3. 教育×AI 動向（1〜2本）
- どの教育現場か（学校・大学・企業研修 など）
- 講師が押さえるべき観点（3つくらい）

🛠️ 4. AIツール最新アップデート
- ChatGPT / Claude / Gemini / Runway / Suno / Notion AI などから
- 講師目線で「どんな授業パーツとして使えそうか」を短くコメント

💡 5. 授業で使えるネタ・実践アイデア（3〜5個）
- 授業タイトル案や、ワークショップ案を箇条書きで

────────────
🔗 参考URL
最後に、「[1] サイト名『タイトル』: URL」という形式で、
上で使ったニュース記事のURLだけを一覧で出してください。
※ここでは、必ず入力として渡したURLだけを使うこと。新しいURLは作らないこと。

# ニュース候補リスト
{base_news_list}
'''

    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return res.choices[0].message.content


# ===== Lark へ送信 =====
def send_to_lark(text: str):
    if not LARK_WEBHOOK_URL:
        raise RuntimeError(
            "LARK_WEBHOOK_URL が設定されていません。GitHub Secrets を確認してください。"
        )

    payload = {
        "msg_type": "text",
        "content": {
            "text": text,
        },
    }
    resp = requests.post(LARK_WEBHOOK_URL, json=payload)
    resp.raise_for_status()


# ===== メイン処理 =====
def main():
    print("Fetching raw AI news articles...")
    articles = fetch_ai_articles()

    print(f"Fetched {len(articles)} articles. Building digest with OpenAI...")
    digest_text = build_digest_with_openai(articles)

    print("Sending to Lark...")
    send_to_lark(digest_text)
    print("Done!")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
