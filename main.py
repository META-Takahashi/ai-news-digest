import os
from datetime import datetime, timedelta, timezone
import requests
from openai import OpenAI

# ====== Keys ======
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ====== 固定テキスト：geniusAI紹介 ======
GENIUS_AI_TEXT = """
① コンテンツ生成の全自動化
・SNS投稿（TikTok / Instagram / X）を完全自動生成
・LP / 広告コピー / 営業メールも生成
・動画編集の自動化（カット / テロップ / BGM / サムネ）

② 採用・人材紹介のAI自動化
・応募最大化の構成
・求人コピー
・LINEステップ構成
・マッチング推薦

③ 営業DX
・企業URLから事業分析
・営業文・追撃文
・商談メモ要約
・CRM自動記録

④ デザイン自動化
・ロゴ / カラー / 世界観
・Canvaテンプレ
・パッケージ案

⑤ 事業 / 経営サポート
・収益予測（PL）
・事業計画
・初期ロンチ戦略
・競合分析
・企画資料自動生成

⑥ AI社員
・問い合わせ対応
・DM / LINE自動運用
・FAQ自動生成

⑦ エンジニアリングAI
・Next.js / Prisma
・API自動生成
・バグ修正 / コードレビュー
"""


# ====== Step1：AIニュースを収集（Google News API → GPTで要約） ======
def fetch_news_articles():
    """
    AI系ニュースを Google News RSS から集める（無料）
    """
    import feedparser

    FEEDS = [
        "https://news.google.com/rss/search?q=AI+生成AI&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=ChatGPT&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=Google+AI&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=OpenAI&hl=ja&gl=JP&ceid=JP:ja",
    ]

    articles = []
    for url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            articles.append({
                "title": entry.title,
                "url": entry.link,
                "summary": entry.summary if hasattr(entry, "summary") else ""
            })

    return articles[:12]  # 12件だけ使う


# ====== Step2：GPTでニュースを講師向けに整形 ======
def build_digest_with_openai(articles):
    today = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = today.strftime("%Y/%m/%d (%a)")

    prompt = f"""
あなたは「AI講師のためのニュース編集者」です。
以下のニュース記事をもとに、授業で使いやすい “最高に読みやすいダイジェスト“ を作ってください。
ルール：
- 必ず日本語
- 箇条書きを多用
- 各ニュースには「授業アイデア」も付ける
- 参考URLを必ず1つ付ける

【今日の日付】
{today_str}

【入力記事】
{articles}

出力フォーマット：

🎨 AIニュースダイジェスト（AI講師向け）
{today_str}
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース
（ここにGPTが生成）

🏭 2. 企業のAI活用
（ここにGPTが生成）

🎓 3. 教育×AI 動向
（ここにGPTが生成）

🛠️ 4. AIツール最新アップデート
（ここにGPTが生成）

💡 5. 授業で使えるネタ・実践アイデア
（ここにGPTが生成）

最後に、参考URL一覧もまとめてください。
"""

    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )

    return res.choices[0].message.content


# ====== Step3：Larkへ送信 ======
def send_to_lark(text: str):
    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }

    resp = requests.post(LARK_WEBHOOK_URL, json=payload)
    resp.raise_for_status()


# ====== Main ======
def main():
    print("Fetching raw AI news articles...")
    articles = fetch_news_articles()
    print(f"Fetched {len(articles)} articles.")

    print("Building digest with OpenAI...")
    digest_text = build_digest_with_openai(articles)

    full_text = digest_text + "\n\n────────────\n🤖 geniusAI ができること\n" + GENIUS_AI_TEXT

    print("Sending to Lark...")
    send_to_lark(full_text)
    print("Done!")


if __name__ == "__main__":
    main()
