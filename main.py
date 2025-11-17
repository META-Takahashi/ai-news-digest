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
def fetch_gemini_news():
    prompt = """
    最新のAIツール・AI業界ニュースを日本語で3つ。
    箇条書きで、短く、重要ポイントのみ。
    """
    try:
        # まずはこのモデルでトライ（将来ここだけ差し替えればOK）
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
        res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        # Gemini側でエラーが出ても全体が止まらないようにする
        print("Gemini error:", e)
        return "※Gemini側のニュース取得でエラーが発生したため、今回はChatGPT側の情報のみです。"


# ====== Get news from Gemini ======
def fetch_gemini_news():
    prompt = """
    最新のAIツール・AI業界ニュースを日本語で3つ。
    箇条書きで、短く、重要ポイントのみ。
    """
    model = genai.GenerativeModel("gemini-pro")
    res = model.generate_content(prompt)
    return res.text


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
