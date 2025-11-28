"""
Service functions for the Discord bot.
Contains helper functions for external API calls and AI interactions.
"""
import httpx
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)


async def fetch_random_joke() -> tuple[str, str]:
    """
    Fetch a random joke from the Official Joke API.
    Returns a tuple of (setup, punchline).
    """
    url = "https://official-joke-api.appspot.com/jokes/random"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        setup = data.get("setup", "Nem érkezett poén.")
        punchline = data.get("punchline", "")
        return setup, punchline


async def ask_gpt(prompt: str) -> str:
    """
    Call OpenAI Responses API with gpt-5.1 and return plain text only.
    """
    print("ask_gpt: prompt =", prompt)
    enhanced_prompt = f"{prompt}\n\nPlease provide a concise answer."
    try:
        response = await openai_client.responses.create(
            model="gpt-5.1",
            # simple text input is fine for a Discord command
            input=enhanced_prompt,
            # force text output so we always get a message item (important for GPT-5.x)
            text={"format": {"type": "text"}},
            max_output_tokens=512,
        )
        # `output_text` is a convenience helper that concatenates all text content
        text = response.output_text or ""
        return text.strip()
    except Exception as e:
        print(f"[ERROR] ask_gpt failed: {type(e).__name__}: {e}")
        raise


async def check_moderation(text: str):
    """
    Use omni-moderation-latest to check if text is harmful/vulgar.
    Translates text to English first for better accuracy.
    Returns the first moderation result, or None on error.
    """
    try:
        # First, translate to English using a cheaper model (gpt-4o-mini)
        print("[check_moderation] Translating text to English...")
        translation_response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a translator. Translate the following text to English. If it's already in English, return it unchanged. Only return the translation, nothing else."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            max_tokens=200,
            temperature=0.3
        )

        english_text = translation_response.choices[0].message.content.strip()
        print(f"[check_moderation] Translated text: {english_text}")

        # Now run moderation on the English text
        resp = await openai_client.moderations.create(
            model="omni-moderation-latest",
            input=english_text,
        )
        # resp.results is a list; we only care about the first one
        if not resp.results:
            return None
        return resp.results[0]
    except Exception as e:
        print(f"[ERROR] moderation failed: {type(e).__name__}: {e}")
        return None

