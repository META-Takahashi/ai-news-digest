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

    prompt = f"""
あなたは「AI講師のためのニュース編集者」です。
AI・生成AI・AIツール・教育（EdTech）領域の情報を、
『スマホで読みやすい授業ネタニュースレター』としてまとめます。

# 出力全体のトーン
- 日本語、です・ます調
- 句読点と改行を多めにして、「行間が広くて読みやすいLINEメッセージ」風にする
- 絵文字は各ブロックの先頭にだけ使う（行中では多用しない）

# 固定フォーマット（この形を必ず守る）

🎨 AIニュースダイジェスト（AI講師向け）
{today_str}
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース
（※ここは 2〜3 トピック）

◆ トピック1
【タイトル】
〜〜〜

【概要】（2〜3文）
〜〜〜

【授業アイデア】（1〜2個）
- 〜〜〜
- 〜〜〜

【参考URL】
https://......

◆ トピック2
（同じフォーマットで）

🏭 2. 企業のAI活用
（※ここも 2〜3 トピック、同じフォーマット）

◆ トピック1
【タイトル】
〜〜〜
【概要】
〜〜〜
【授業ポイント】
- 〜〜〜
- 〜〜〜
【参考URL】
https://......

🎓 3. 教育×AI 動向
（1〜2トピック、上と同じ構造）

🛠️ 4. AIツール最新アップデート
（3〜5ツール）

◆ ツール名1
【アップデート内容】
- 〜〜〜
【どんな講師向けか】
- 〜〜〜
【参考URL】
https://......

💡 5. 授業で使えるネタ・実践アイデア
（5個）

1) 授業タイトル
・どんな授業か（1〜2文）
・どの単元で使えそうか

2) 授業タイトル
（同様）

---

# 厳守ルール
- 見出しと見出しのあいだは、必ず1行以上の空行を入れる
- 箇条書きは「- 」か「・」を使う
- 1つの段落は最大2〜3文までにして、すぐ改行する
- セクションタイトル行（🎨, 🌟, 🏭, 🎓, 🛠️, 💡）はそのまま使う
"""


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
