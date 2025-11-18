import os
from datetime import datetime, timedelta, timezone
import requests
from xml.etree import ElementTree

from openai import OpenAI

# ===== 環境変数（GitHub Secrets から） =====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ===== 対象とするAIニュース系RSSフィード（Google News 検索RSS） =====
# 実際のニュースソースはここから取得される
RSS_FEEDS = [
    (
        "general",
        "https://news.google.com/rss/search?q=%22生成AI%22+OR+%22generative+AI%22&hl=ja&gl=JP&ceid=JP:ja",
    ),
    (
        "business",
        "https://news.google.com/rss/search?q=AI+%E5%B7%A5%E4%BD%9C%E6%95%88%E7%8E%87+OR+AI%E5%B0%8E%E5%85%A5+OR+AI%E4%BC%81%E6%A5%AD&hl=ja&gl=JP&ceid=JP:ja",
    ),
    (
        "education",
        "https://news.google.com/rss/search?q=AI+%E6%95%99%E8%82%B2+OR+EdTech+AI&hl=ja&gl=JP&ceid=JP:ja",
    ),
    (
        "tools",
        "https://news.google.com/rss/search?q=AI+%E3%83%84%E3%83%BC%E3%83%AB+OR+AI+%E3%82%B5%E3%83%BC%E3%83%93%E3%82%B9+OR+%22ChatGPT%22+OR+%22Claude%22+OR+%22Gemini%22&hl=ja&gl=JP&ceid=JP:ja",
    ),
]

# ===== 事業分野一覧（セクション3で必ず全部出す） =====
BUSINESS_FIELDS = [
    "情報通信（IT・AI）",
    "マーケティング・広告",
    "人材・HR",
    "コンサルティング",
    "小売・EC",
    "飲食",
    "観光・交通",
    "クリエイティブ・エンタメ",
    "教育・スクール",
    "金融・投資",
    "不動産",
    "ヘルスケア・美容",
    "サブスク・メンバーシップ",
    "メディア・コミュニティ",
]


# ===== RSSからAIニュース候補を取得 =====
def fetch_ai_news_from_rss(max_items: int = 20):
    """
    Google News のRSSからAI関連ニュースのタイトルとURLを取得してリストで返す。
    戻り値: [{"title": ..., "url": ..., "tag": ...}, ...]
    """
    articles = []
    seen = set()

    for tag, feed_url in RSS_FEEDS:
        try:
            resp = requests.get(feed_url, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[WARN] RSS取得失敗: {feed_url} - {e}")
            continue

        try:
            root = ElementTree.fromstring(resp.content)
        except Exception as e:
            print(f"[WARN] RSSパース失敗: {feed_url} - {e}")
            continue

        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el = item.find("link")
            if title_el is None or link_el is None:
                continue

            title = (title_el.text or "").strip()
            url = (link_el.text or "").strip()
            if not title or not url:
                continue

            key = (title, url)
            if key in seen:
                continue

            seen.add(key)
            articles.append(
                {
                    "title": title,
                    "url": url,
                    "tag": tag,
                }
            )

            if len(articles) >= max_items:
                return articles

    return articles


# ===== OpenAIでダイジェスト文章に整形 =====
def build_digest_with_openai(articles: list[dict]) -> str:
    """
    RSSから取得したarticlesを元に、
    指定フォーマットの「AIニュースダイジェスト（AI講師向け）」テキストを生成する。
    """
    # 日付（JST）
    now_jst = datetime.now(timezone.utc) + timedelta(hours=9)
    today_date_str = now_jst.strftime("%Y/%m/%d (%a)")

    # ニュース候補一覧をテキスト化（LLMへのインプット用）
    if not articles:
        articles_text = "（RSSからニュースが取得できませんでした）"
    else:
        lines = []
        for idx, art in enumerate(articles, start=1):
            lines.append(
                f"{idx}. [{art['tag']}] {art['title']}\n   URL: {art['url']}"
            )
        articles_text = "\n".join(lines)

    business_fields_str = ", ".join(BUSINESS_FIELDS)

    prompt = f"""あなたは「AI講師向けニュースレター」の編集者です。
以下の「ニュース候補一覧」だけを情報源として、AI講師が授業・研修ですぐ使える形にニュースを整理してください。

【ニュース候補一覧】
{articles_text}

重要:
- 上記の「タイトル」と「URL」以外の具体的な数値・発言・出来事を勝手に作らないでください。
- 分からない部分は一般的な表現にとどめてください（例：「〜などのテーマが議論されています」）。
- 最後に「📎 参考URL」として、上記ニュース候補の中から使えそうなタイトルとURLを列挙してください。
- 出力はすべて日本語。
- 絵文字や見出しのフォーマットは下記をそのまま使ってください。

出力フォーマットは次のとおりです。このフォーマットから外れないでください:

🎨 AIニュースダイジェスト（AI講師向け）  
{today_date_str}  
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース
ここには「モデル・技術・サービス・AIソフト」寄りのニュースを3〜5件、次のミニブロック形式でまとめてください：

● タイトル（できるだけ具体的に）
  概要：2〜3文で要約（ニュース候補一覧を元に）
  授業アイデア：授業やワークに使えるアイデアを1〜2文

🏭 2. 企業のAI活用
企業や組織のAI導入事例っぽいニュースを2〜4件まとめてください：

● 企業名 or 業界＋取り組み内容
  概要：2〜3文
  授業ポイント：AI導入のメリット・課題など、講師目線の解説ポイントを1〜2文

🎓 3. 業界別AI動向
以下の事業分野ごとに、該当しそうなニュースがあれば1〜2文でまとめてください。
完全に該当するニュースが見つからない分野は「現時点では目立ったニュースは無し（今後の様子見）」のように一言コメントしてください。

事業分野一覧：
{business_fields_str}

出力形式の例（あくまで形式だけ参考に）：
- 情報通信（IT・AI）：〜〜〜
- マーケティング・広告：〜〜〜
（上のリストにある全分野をこの形式で出してください）

🛠️ 4. AIツール最新アップデート
上記ニュース候補の中から「ツール・サービスの機能アップデート/新機能」に当たりそうなものを3〜5件ピックアップして：

- ツール名：アップデート内容（ニュース候補に基づいて大まかに）
  講師視点：どんな授業・研修で使えそうか一言

💡 5. 授業で使えるネタ・実践アイデア
今日のニュースを元にした授業ネタ・ワークショップ案を4〜6個、箇条書きで出してください。
各アイデアは「タイトル：一言説明」の形で、シンプルに書いてください。

最後に、次のような形で「📎 参考URL」セクションを付けてください。
ここでは、ニュース候補一覧で使った（または関連が深い）記事を中心にタイトルとURLを列挙してください。

📎 参考URL
- [タイトル1](URL1)
- [タイトル2](URL2)
- ...

以上のフォーマットに沿って、AI講師が読みやすく・そのまま転用しやすいテキストを出力してください。
"""

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

    payload = {"msg_type": "text", "content": {"text": text}}
    resp = requests.post(LARK_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()


# ===== メイン処理 =====
def main():
    print("Fetching RSS news...")
    articles = fetch_ai_news_from_rss(max_items=20)

    print(f"Fetched {len(articles)} articles from RSS.")
    digest_text = build_digest_with_openai(articles)

    print("Sending digest to Lark...")
    send_to_lark(digest_text)
    print("Done!")


if __name__ == "__main__":
    main()
