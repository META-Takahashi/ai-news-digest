import os
from datetime import datetime, timedelta, timezone

import requests
from openai import OpenAI
import google.generativeai as genai  # 将来用


# ===== 環境変数（GitHub Secrets から来る） =====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ===== OpenAI からニュース作成 =====
def fetch_openai_news():
    """OpenAI (ChatGPT) を使って、AI講師向けのニュース要約をつくる。"""
    # 日本時間
    today = datetime.now(timezone.utc) + timedelta(hours=9)
    date_str = today.strftime("%Y/%m/%d (%a)")

    prompt = f'''あなたは「AI講師のためのニュース編集者」です。

目的：
AI・生成AI・AIツール・教育（EdTech）領域の最新情報を、
AI講師が授業・研修・講演で“そのまま使える形”に整理して提供してください。

出力フォーマットは、下記の構造と記号・絵文字を厳守してください。
（サンプルの文言は置き換えてOKですが、「見出しの形」と「階層構造」は崩さないこと）

🎨 AIニュースダイジェスト（AI講師向け）
{date_str}
未来の授業づくりにすぐ活かせる「今日のAIトピック」を厳選してお届けします。

🌟 1. 生成AIニュース
● タイトル１（例：🚀 新モデル〜 など）
概要：2〜3文で要約
ポイント：
- 重要な変化・特徴を箇条書きで2〜3個
授業アイデア：
→ 授業や研修でどう活かせるかを1〜2文で具体的に

● タイトル２
概要：
ポイント：
授業アイデア：

🏭 2. 企業のAI活用
● タイトル１（例：業界 × どんなAI活用か）
背景・ねらい：
- 業界や部門の課題
- どのようにAIで解決しようとしているか
授業ポイント：
→ 「AIが得意なこと／不得意なこと」が分かる説明を1〜2文

● タイトル２
背景・ねらい：
授業ポイント：

🎓 3. 教育×AI 動向
● タイトル１
内容：
- 学校／大学／企業研修のどの部分にAIが入ってきているか
講師が意識すべきポイント：
- 3つ前後、箇条書き

🛠️ 4. AIツール最新アップデート
（ChatGPT / Claude / Gemini / Runway / Suno / Notion AI / Recraft など、実在の有名ツール名を優先）
💬 ツール名１：アップデート内容の要約
→ どんな講師・授業に向いているか（1行）

💬 ツール名２：アップデート内容の要約
→ どんな講師・授業に向いているか（1行）

💬 ツール名３：アップデート内容の要約
→ どんな講師・授業に向いているか（1行）

💡 5. 授業で使えるネタ・実践アイデア
（今日のニュースをもとに、すぐ実践できる授業案を3〜5個）
🎨 アイデア１：
→ どんな授業か／どんな流れかを2〜3文で

🎶 アイデア２：
→ どんな授業か／どんな流れかを2〜3文で

🏭 アイデア３：
→ どんな授業か／どんな流れかを2〜3文で

可能な限り、実在しそうな企業・業界・ツール名を用いつつ、
事実と断定できない部分は「〜と言われています」「〜が想定されます」のような表現にしてください。
難しい専門用語には（かっこで一言解説）を添えてください。'''

    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )
    return res.choices[0].message.content


# ===== Gemini 側（今はダミー） =====
def fetch_gemini_news():
    return "※Gemini 側のニュース連携は現在調整中です。（後日、画像・論文要約などで拡張予定）"


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
    print("Fetching AI news...")

    openai_news = fetch_openai_news()
    gemini_part = fetch_gemini_news()

    message = f'''📚 AIニュースダイジェスト（AI講師向け）

{openai_news}

---
📝 Gemini からの補足
{gemini_part}
'''

    print("Sending to Lark...")
    send_to_lark(message)
    print("Done!")


if __name__ == "__main__":
    main()
