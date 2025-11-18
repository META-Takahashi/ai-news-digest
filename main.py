import os
from datetime import datetime, timedelta, timezone

import requests
import feedparser
from openai import OpenAI

# ========= 環境変数 =========
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY が設定されていません（GitHub Secrets を確認してください）")

if not LARK_WEBHOOK_URL:
    raise RuntimeError("LARK_WEBHOOK_URL が設定されていません（GitHub Secrets を確認してください）")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ========= ニュースRSSの一覧（AI関連中心） =========
NEWS_FEEDS = [
    # 日本語のAIニュースが多めのフィードをあとで差し替えてOK
    "https://news.google.com/rss/search?q=生成AI+OR+\"generative+AI\"&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=AI+教育+OR+EdTech&hl=ja&gl=JP&ceid=JP:ja",
    "https://news.google.com/rss/search?q=ChatGPT+OR+OpenAI+OR+Claude+OR+Gemini&hl=ja&gl=JP&ceid=JP:ja",
]


# ========= ニュース取得 =========
def fetch_ai_articles(max_articles: int = 10):
    """
    GoogleニュースRSSからAI関連の記事を集める。
    返り値: {"title": str, "link": str, "source": str} のリスト
    """
    articles = []

    for feed_url in NEWS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[WARN] RSS取得に失敗: {feed_url} ({e})")
            continue

        parsed = feedparser.parse(resp.text)
        for entry in parsed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            source = getattr(entry, "source", {}).get("title", "") if hasattr(entry, "source") else ""

            if not title or not link:
                continue

            articles.append(
                {
                    "title": title,
                    "link": link,
                    "source": source or "News",
                }
            )

    # 重複をざっくり削る（タイトル基準）
    uniq = {}
    for a in articles:
        uniq.setdefault(a["title"], a)

    articles_unique = list(uniq.values())[:max_articles]
    return articles_unique


# ========= OpenAI でダイジェスト生成 =========
def build_digest_with_openai(articles):
    """
    取得した記事リストをもとに、AI講師向けのダイジェスト文章を作る。
    geniusAI ブロックは付けない。
    """
    # JST の日付
    today_jst = datetime.now(timezone.utc) + timedelta(hours=9)
    date_str = today_jst.strftime("%Y/%m/%d (%a)")

    # プロンプトに渡す「記事一覧」テキスト（タイトル＋ソースだけ）
    article_list_text = "\n".join(
        f"- {i+1}. {a['title']}（{a['source']}）"
        for i, a in enumerate(articles)
    )

    prompt = f"""
あなたは「AI講師のためのニュース編集者」です。
以下の AI 関連ニュース一覧だけを情報源として、日本語で授業に使いやすいダイジェストを作ってください。

【今日の日付】
{date_str}

【ニュース一覧】
{article_list_text}

【重要ルール】
- 上記のニュース一覧から想像できる範囲でまとめてOKだが、「書いていない事実」を断定しない。
- 事実が分からない部分は、「〜と報じられている」「〜と考えられる」など、少しぼかした書き方にする。
- ニュースの本数や順番はおまかせ（厳選でOK）。ただし、各セクションに必ず1件以上は入れる。
- 出力はプレーンテキストのみ（Markdownのリンク記法 [[...](...)] は使わない）。
- 箇条書きを多めにして、スマホでも読みやすく。

【出力フォーマット】
必ず、次の構造・見出し名を守ってください。

🎨 AIニュースダイジェスト（AI講師向け）
{date_str}
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース
【タイトル1】
・ポイント1
・ポイント2
授業アイデア：
・授業でどう扱えるかを1〜2行で

【タイトル2】
・ポイント
授業アイデア：
・ ...

🏭 2. 企業のAI活用
【タイトル】
・どの業界で、何をしているか
・どんな効果や狙いがあるか
授業ポイント：
・講義や事例紹介での使いどころ

🎓 3. 教育×AI 動向
【タイトル】
・教育現場で何が起きているか
・講師として意識したい論点
授業ポイント：
・ディスカッションの問い or 注意点

🛠️ 4. AIツール最新アップデート
・ツール名：アップデート内容（できるだけ簡潔に）
・ツール名：アップデート内容
※ 3〜5行程度でOK

💡 5. 授業で使えるネタ・実践アイデア
・アイデア1（どんな授業かを一言＋簡単な説明）
・アイデア2
・アイデア3

※ 最後に「参考URL」はこちらで付けるので、本文にはURLを書かないでください。
"""
    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return res.choices[0].message.content.strip()


# ========= 参考URLセクション生成 =========
def build_reference_urls(articles):
    lines = ["📎 参考URL", ""]
    for a in articles:
        lines.append(f"- {a['title']}  {a['link']}")
    return "\n".join(lines)


# ========= Lark へ送信 =========
def send_to_lark(text: str):
    payload = {
        "msg_type": "text",
        "content": {"text": text},
    }
    resp = requests.post(LARK_WEBHOOK_URL, json=payload, timeout=10)
    try:
        resp.raise_for_status()
    except Exception as e:
        print("Lark への送信に失敗しました:", e, resp.text)
        raise


# ========= メイン =========
def main():
    print("Fetching AI news articles...")
    articles = fetch_ai_articles(max_articles=12)
    print(f"Fetched {len(articles)} articles")

    if not articles:
        fallback = "本日のAIニュースを取得できませんでした。後ほど再実行してください。"
        send_to_lark(fallback)
        return

    print("Building digest with OpenAI...")
    digest_text = build_digest_with_openai(articles)

    print("Building reference URLs section...")
    ref_text = build_reference_urls(articles)

    full_message = digest_text + "\n\n" + ref_text

    print("Sending to Lark...")
    send_to_lark(full_message)
    print("Done.")


if __name__ == "__main__":
    main()
