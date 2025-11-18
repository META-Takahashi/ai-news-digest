import os
from datetime import datetime, timedelta, timezone
import urllib.parse
import xml.etree.ElementTree as ET

import requests
from openai import OpenAI

# ===== 環境変数 =====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY が設定されていません。GitHub Secrets を確認してください。")
if not LARK_WEBHOOK_URL:
    raise RuntimeError("LARK_WEBHOOK_URL が設定されていません。GitHub Secrets を確認してください。")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ===== Google News RSS からニュース取得 =====

GOOGLE_NEWS_RSS_BASE = "https://news.google.com/rss/search"

def fetch_google_news_rss(query: str, max_items: int = 5):
    """
    Google News のRSS検索から記事リストを取得する。
    戻り値: [{'title': ..., 'link': ...}, ...]
    """
    params = {
        "q": query,
        "hl": "ja",
        "gl": "JP",
        "ceid": "JP:ja",
    }
    url = f"{GOOGLE_NEWS_RSS_BASE}?{urllib.parse.urlencode(params)}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"[WARN] RSS取得失敗: {e}")
        return []

    items = []
    try:
        root = ET.fromstring(resp.text)
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item")[:max_items]:
            title_el = item.find("title")
            link_el = item.find("link")
            if title_el is None or link_el is None:
                continue
            title = (title_el.text or "").strip()
            link = (link_el.text or "").strip()
            if not title or not link:
                continue
            items.append({"title": title, "link": link})
    except Exception as e:
        print(f"[WARN] RSSパース失敗: {e}")
        return []

    return items

# ===== OpenAI でダイジェスト本文を作る =====

def build_digest_with_openai(sections, today_str: str) -> str:
    """
    sections: dict
      {
        "gen_ai": [ {title, link}, ... ],
        "business_ai": [ ... ],
        "edu_multi": [ ... ],
      }
    today_str: "2025/11/18 (Tue)" みたいな文字列
    """
    # プロンプト用に記事一覧をテキスト化
    def format_articles_for_prompt(label, articles):
        lines = []
        for idx, art in enumerate(articles, start=1):
            lines.append(f"- ({label}{idx}) タイトル: {art['title']} / URL: {art['link']}")
        return "\n".join(lines) if lines else "- （該当ニュースが少ない場合は、一般的な最近の傾向を短くまとめてください）"

    gen_ai_list = sections.get("gen_ai", [])
    biz_ai_list = sections.get("business_ai", [])
    edu_multi_list = sections.get("edu_multi", [])

    gen_ai_block = format_articles_for_prompt("G", gen_ai_list)
    biz_ai_block = format_articles_for_prompt("B", biz_ai_list)
    edu_block = format_articles_for_prompt("E", edu_multi_list)

    # 事業分野一覧（教育×AI・業界別で意識させる）
    business_domains = """
- 情報通信（IT・AI）
- マーケティング・広告
- 人材・HR
- コンサルティング
- 小売・EC
- 飲食
- 観光・交通
- クリエイティブ・エンタメ
- 教育・スクール
- 金融・投資
- 不動産
- ヘルスケア・美容
- サブスク・メンバーシップ
- メディア・コミュニティ
    """.strip()

    prompt = f"""
あなたは「AI講師のためのニュースレター編集者」です。

# 目的
- AI講師が「そのまま授業・研修・講演に使える」ニュースダイジェストを毎日届ける。
- 情報源は、こちらで取得した実ニュース（Google News RSS）です。

# 入力されるニュース一覧
[生成AIニュース候補]
{gen_ai_block}

[企業のAI活用ニュース候補]
{biz_ai_block}

[教育・各業界×AIニュース候補]
{edu_block}

# 業界カテゴリ（3. 教育×AI・業界別動向で意識してほしいリスト）
{business_domains}

# 出力フォーマット（この形を守ってください・参考URL一覧は書かない）
以下の「本文だけ」を出力してください。参考URL一覧は書かないこと。（参考URLは別処理で付けます）

フォーマット例：

🎨 AIニュースダイジェスト（AI講師向け）
2025/11/18 (Tue)
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース
● タイトル1
要約本文（2〜3行）
授業アイデア：
→ 授業での使い方を1〜2行で

● タイトル2
…

🏭 2. 企業のAI活用
● 企業事例1
要約本文（2〜3行）
授業ポイント：
→ ここをどう説明するとわかりやすいか 1〜2行

🎓 3. 教育×AI・各業界動向
- 上記の事業分野一覧を意識しつつ、教育・研修・各業界でのAI活用の動きを2〜3件にまとめる
- 入力ニュースに直接対応しない場合は、「最近よく見られる傾向」として一般化して書いてOK
- AI講師として意識すべきポイント（3個程度）を箇条書きにする

🛠️ 4. AIツール最新アップデート
- ニュース一覧にツール名が含まれていれば、それを優先してまとめる
- なければ、一般的に話題になっている主要ツール（ChatGPT, Claude, Gemini, Runway, Suno など）の最近の傾向をコンパクトにまとめる
- 「講師としてどの科目・場面と相性が良さそうか」を添える

💡 5. 授業で使えるネタ・実践アイデア
- 今日のニュースをもとにした授業・ワークショップ案を 3〜5個
- 例：
  - 「生成AIでフェイク画像を検証する授業」
  - 「企業のAI導入事例を分析して、メリット・デメリットをディスカッション」 など

# 出力の条件
- 出力はすべて日本語。
- 絵文字はサンプルと同じくらい（増やしすぎない）。
- 入力にない具体的な事実を捏造しない。一般論を書く場合は「〜といった動きが見られます」のように表現をぼかす。
- テキストはLarkのプレーンテキストで読みやすいように、改行と箇条書きをうまく使う。
- 「参考URL一覧」は絶対に書かない（こちらで後から追加します）。

今日の日付は {today_str} です。フォーマット2行目の日付部分にはこの文字列を入れてください。
"""

    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )
    return res.choices[0].message.content


# ===== Lark に送る =====

def send_to_lark(text: str):
    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        },
    }
    resp = requests.post(LARK_WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()


# ===== メイン処理 =====

def main():
    # 日本時間
    now_jst = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str_short = now_jst.strftime("%Y/%m/%d (%a)")

    print("Fetching RSS news...")

    # 各セクションごとのRSS検索クエリ
    sections = {
        "gen_ai": fetch_google_news_rss('生成AI OR "generative AI"', max_items=5),
        "business_ai": fetch_google_news_rss('企業 生成AI 導入 OR "AI 活用 事例"', max_items=5),
        "edu_multi": fetch_google_news_rss('教育 AI OR EdTech AI OR "AI 研修"', max_items=5),
    }

    # 参考URL用にフラットなリストを作る（重複タイトルは一応避ける）
    seen = set()
    ref_articles = []
    for key, arts in sections.items():
        for art in arts:
            k = (art["title"], art["link"])
            if k in seen:
                continue
            seen.add(k)
            ref_articles.append(art)

    print("Building digest with OpenAI...")
    digest_body = build_digest_with_openai(sections, today_str_short)

    # 参考URL一覧を自前で付ける
    if ref_articles:
        ref_lines = []
        for art in ref_articles:
            # Larkのプレーンテキストでも分かりやすいように、Markdown風に
            ref_lines.append(f"- [{art['title']}]({art['link']})")
        refs_text = "\n".join(ref_lines)
        full_text = f"""{digest_body}

📎 参考URL一覧
{refs_text}
"""
    else:
        full_text = digest_body + "\n\n（※参考URLは本日は取得できませんでした）"

    print("Sending to Lark...")
    send_to_lark(full_text)
    print("Done.")


if __name__ == "__main__":
    main()
