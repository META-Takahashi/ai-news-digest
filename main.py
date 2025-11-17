import os
import requests
import google.generativeai as genai
from openai import OpenAI

# ====== API Keys ======
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LARK_WEBHOOK_URL = os.getenv("LARK_WEBHOOK_URL")

# ====== Setup clients ======
openai_client = OpenAI(api_key=OPENAI_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

# ====== Get news from OpenAI ======
def fetch_openai_news():
    """OpenAI (ChatGPT) を使って、AI講師向けのニュース要約をつくる。"""
    today = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = today.strftime("%Y-%m-%d (%a)")

    prompt = f"""
あなたは「AI講師のためのニュース編集者」です。

目的：
AI・生成AI・AIツール・教育（EdTech）領域の最新情報を、
“AI講師が授業・研修・講演で使いやすい形” に整理して提供する。

出力条件：
- すべて日本語
- 難しい用語は（カッコ）で一言補足
- 内容は断定しすぎず、専門家として丁寧に
- 文章は読みやすく、箇条書きを活用する

出力フォーマット（必ず守る）：

# 今日のAIニュース {today_str}

## 1. 生成AIニュース（最新3〜5件）
- タイトル
- 概要（2〜3文）
- 背景
- AI講師として押さえるポイント（2〜3個）
- 授業・研修での使いどころ

## 2. 企業のAI活用・導入ニュース（2〜3件）
- タイトル
- どの業界で何が起きたか
- 活用されているAI技術の種類
- 現場での課題と効果
- AI講師としての使い所

## 3. 教育（EdTech）× AI 最新動向（1〜3件）
- タイトル
- 学校・大学・研修領域で何が変化しているか
- 注意点・期待される効果
- 指導者が知るべきポイント

## 4. AIツールの最新アップデート（5件）
（例：ChatGPT・Claude・Gemini・Runway・Suno・Notion AI・Recraft 等）
- ツール名 + 最近のアップデート内容
- どんな用途の講師に便利か
- 生徒・社内研修での活用例

---

# 授業で使えるアウトプット・ネタ
AI講師として今日から使える授業ネタ・企画案を5個

"""

    res = openai_client.chat_completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    return res.choices[0].message.content



# ===== Get news from Gemini =====
def fetch_gemini_news():
    """
    今はChatGPTメインでニュース取得。
    Gemini側は後で安定してから接続する想定なので、
    とりあえず固定メッセージを返しておく。
    """
    return "※Gemini側のニュースは現在調整中です。（後日アップデート予定）"



# ====== Send message to Lark ======
def send_to_lark(text):
    payload = {"msg_type": "text", "content": {"text": text}}
    requests.post(LARK_WEBHOOK_URL, json=payload)


# ====== Main job ======
def main():
    print("Fetching AI news...")

    openai_news = fetch_openai_news()
    gemini_news = fetch_gemini_news()

    message = f"""
【AIニュースまとめ】

🔥 OpenAI 最新ニュース
{openai_news}

🟦 Gemini 最新ニュース
{gemini_news}

"""

    print("Sending to Lark...")
    send_to_lark(message)
    print("Done!")


if __name__ == "__main__":
    main()
