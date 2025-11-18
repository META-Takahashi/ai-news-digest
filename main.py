import os
import re
import html
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

import requests
from openai import OpenAI


# ===== 環境変数（GitHub Secrets から来る） =====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY が設定されていません。GitHub Secrets を確認してください。")
if not LARK_WEBHOOK_URL:
    raise RuntimeError("LARK_WEBHOOK_URL が設定されていません。GitHub Secrets を確認してください。")

openai_client = OpenAI(api_key=OPENAI_API_KEY)


# ===== シンプルな HTML除去 =====
def strip_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    # ごく簡単にタグを消す
    text = re.sub(r"<.*?>", "", text)
    # 改行と余分な空白を整形
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


# ===== Google News RSS から AI 関連ニュースを取得 =====
GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q=AI+OR+%22人工知能%22+OR+%22生成AI%22"
    "&hl=ja&gl=JP&ceid=JP:ja"
)


def fetch_rss_articles(max_items: int = 20):
    """
    Google News RSS から AI 関連ニュースを最大 max_items 件取ってくる
    戻り値: [{title, link, description}, ...]
    """
    resp = requests.get(GOOGLE_NEWS_RSS_URL, timeout=10)
    resp.raise_for_status()
    xml_text = resp.text

    root = ET.fromstring(xml_text)
    items = []
    # RSS の item ノードをざっくり取る
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = strip_html(item.findtext("description") or "")
        if not title or not link:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "description": desc,
            }
        )
        if len(items) >= max_items:
            break
    return items


# ===== OpenAI でダイジェスト文面を生成 =====
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


def build_digest_with_openai(articles):
    """
    RSS から取ってきた実ニュース一覧を GPT に渡して
    AI講師向けニュースレター形式に整形してもらう
    """
    if not articles:
        return "🎨 AIニュースダイジェスト（AI講師向け）\n今日は取得できたAIニュースがありませんでした。"

    # 日本時間
    today = datetime.now(timezone.utc) + timedelta(hours=9)
    today_date_str = today.strftime("%Y/%m/%d (%a)")

    # モデルに渡す「生の素材」
    # 形式: 1. タイトル :: URL :: 説明
    article_lines = []
    for i, art in enumerate(articles, start=1):
        line = f"{i}. {art['title']} :: {art['link']} :: {art['description']}"
        article_lines.append(line)
    raw_list_text = "\n".join(article_lines)

    # プロンプト
    system_prompt = (
        "あなたは日本の『AI講師向けニュースレター編集者』です。"
        "渡された実ニュース一覧だけを元に、指定フォーマットで日本語のダイジェストを作成してください。"
        "必ず渡されたURLだけを参考URLとして使い、URLを捏造したり、存在しないサービス名・モデル名を発明しないでください。"
    )

    user_prompt = f"""
以下に、Google News RSS から取得した「AI関連ニュース記事の一覧」があります。

それぞれの形式は：
番号. タイトル :: URL :: 説明
です。

========
{raw_list_text}
========

これらの実ニュースだけを元にして、
AI講師が「そのまま授業・研修に使える」形のダイジェストを作成してください。

【重要な制約】
- 出力はすべて日本語
- 存在しないモデル名・サービス名・ニュースを新しく作らない
- 参考URLは、必ず上記一覧に含まれている URL のみを使う
- 一つのニュースを複数のセクションで使ってもよいが、話を盛りすぎない
- 見やすさ優先で、シンプルなテキスト＋最低限の記号だけにする（Larkで読みやすいように）

【出力フォーマット】

🎨 AIニュースダイジェスト（AI講師向け）
{today_date_str}
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース
ここには「モデル・技術・サービス」寄りのニュースを2〜4件、以下のミニブロック形式で書いてください：

● タイトル（できるだけ具体的に）
  概要：2〜3文で要約
  授業アイデア：授業やワークに使えるアイデアを1〜2文

🏭 2. 企業のAI活用
企業や組織のAI導入事例っぽいニュースを2〜4件まとめてください：

● 企業名 or 業界＋取り組み内容
  概要：2〜3文
  授業ポイント：AI導入のメリット・課題など、講師目線の解説ポイントを1〜2文

🎓 3. 教育×AI / 業界別AI動向
以下の事業分野ごとに、該当しそうなニュースがあれば1〜2文でまとめてください。
完全に該当するニュースが見つからない分野は「現時点では目立ったニュースは無し（今後の様子見）」のように一言コメントしてください。

事業分野一覧：
{", ".join(BUSINESS_FIELDS)}

出力例（形式だけ参考に）：
- 情報通信（IT・AI）：〜〜〜
- マーケティング・広告：〜〜〜
（以下、全分野分続ける）

🛠️ 4. AIツール最新アップデート
上記ニュースの中から「ツール・サービスの機能アップデート/新機能」に当たりそうなものを3〜5件ピックアップして：

- ツール名：アップデート内容
  講師視点：どんな授業・研修で使えそうか一言

💡 5. 授業で使えるネタ・実践アイデア
今日のニュースを元にした授業ネタ・ワークショップ案を4〜6個、箇条書きで出してください。
各アイデアは「タイトル：一言説明」の形で。

📎 参考URL
最後に、上の本文中で実際に触れたニュースの URL だけを、以下の形式でまとめてください：

- [ニュースタイトル](URL)

※ 参考URLには、必ず実在する上記のURLだけを使い、数も多すぎず（5〜10件程度）にしてください。
"""

    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    return res.choices[0].message.content


# ===== Lark へテキスト送信 =====
def send_to_lark(text: str):
    payload = {
        "msg_type": "text",
        "content": {"text": text},
    }
    resp = requests.post(LARK_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()


# ===== メイン処理 =====
def main():
    print("Fetching RSS articles...")
    articles = fetch_rss_articles(max_items=20)

    print(f"Fetched {len(articles)} articles from Google News RSS.")
    digest_text = build_digest_with_openai(articles)

    print("Sending digest to Lark...")
    send_to_lark(digest_text)
    print("Done.")


if __name__ == "__main__":
    main()
