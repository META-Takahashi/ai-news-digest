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
    prompt = """
    最新のAIニュースを3つ、箇条書きで短くまとめてください。
    重要ポイントだけでOK。
    """
    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content


# ====== Get news from Gemini ======
def fetch_gemini_news():
    prompt = """
    最新のAIツール・AI業界ニュースを日本語で3つ。
    箇条書きで、短く、重要ポイントのみ。
    """
    model = genai.GenerativeModel("gemini-1.5-flash")
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
