import os
from datetime import datetime, timedelta, timezone

import requests
from openai import OpenAI
import google.generativeai as genai  # 今はほぼ使ってないけど将来用


# ===== 環境変数（GitHub Secrets から渡ってくる） =====
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
LARK_WEBHOOK_URL = os.environ.get("LARK_WEBHOOK_URL")

# OpenAI クライアント
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Gemini（今は呼ばないが、キーがあれば設定だけしておく）
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ===== OpenAI からニュースを作る =====
def fetch_openai_news():
    """OpenAI (ChatGPT) を使って、AI講師向けのニュース要約をつくる。"""
    # 日本時間
    today = datetime.now(timezone.utc) + timedelta(hours=9)
    today_str = today.strftime("%Y-%m-%d (%a)")

    prompt = f"""
あなたは「AI講師のためのニュース編集者」です。

目的：
AI・生成AI・AIツール・教育（EdTech）領域の最新情報を、
“AI講師が授業・研修・講演で使いやすい形” に整理して提供してください。

出力条件：
- すべて日本語
- 難しい専門用語が出たら（カッコ内で一言解説）を添える
- 断定しすぎず、「一般的には〜とされています」のような丁寧なトーン
- 読みやすいように箇条書きを活用する

出力フォーマット（この構造を必ず守る）：

# 今日のAIニュ
