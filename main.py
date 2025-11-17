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
    # 日本時間
    today = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = today.strftime("%Y-%m-%d (%a)")

    prompt = f'''あなたは「AI講師のためのニュース編集者」です。

目的：
AI・生成AI・AIツール・教育（EdTech）領域の最新情報を、
AI講師が授業・研修・講演で使いやすい形に整理して提供してください。

出力条件：
- すべて日本語
- 難しい専門用語が出たら（カッコ内で一言解説）を添える
- 断定しすぎず、「一般的には〜とされています」のような丁寧なトーン
- 読みやすいように箇条書きを活用する

出力フォーマット（この構造を必ず守る）：

# 今日のAIニュース {today_str}

## 1. 生成AIニュース（最新3〜5件）
- タイトル
- 概要（2〜3文）
- 背景（なぜこのニュースが出てきたか）
- AI講師として押さえるポイント（2〜3個）
- 授業・研修での使いどころ（1〜2文）

## 2. 企業のAI活用・導入ニュース（2〜3件）
- タイトル
- どの業界で何をしているか
- 使われているAI技術のイメージ（例：生成AIチャットボット、需要予測など）
- 現場での課題と効果のポイント
- AI講師としての使い所（研修ネタのヒント）

## 3. 教育（EdTech）× AI 最新動向（1〜3件）
- タイトル
- 学校・大学・企業研修など、どの領域の話か
- 何が変わりつつあるのか
- 指導者・講師が知っておくべきポイント

## 4. AIツールの最新アップデート（5件程度）
（例：ChatGPT / Claude / Gemini / Runway / Suno / Notion AI / Recraft など）
それぞれについて：
- ツール名 + 最近のアップデート内容
- どんな講師・現場に向いているか
- 授業・ワークショップでの活用例（短く）

---

# 授業で使えるアウトプット・ネタ
AI講師として今日から使える授業タイトル案・ワークショップ案を5個、
箇条書きで提案してください。'''

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
