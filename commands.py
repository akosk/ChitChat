"""
Discord bot commands.
Contains all slash command definitions for the bot.
"""
import io
import os
import random
import discord
from discord import app_commands
import httpx
from services import fetch_random_joke, ask_gpt
import json

def register_commands(bot):
    """
    Register all slash commands to the bot's command tree.
    """
    GUILD_ID = int(os.getenv("GUILD_ID"))

    # GUILD-SPECIFIKUS PARANCS: /repeat
    @bot.tree.command(
        name="repeat",
        description="Megismétli a szöveget",
        guild=discord.Object(id=GUILD_ID)
    )
    @app_commands.describe(text="A megismétlendő szöveg")
    async def repeat(interaction: discord.Interaction, text: str):
        await interaction.response.send_message(f"Te ezt írtad: {text}")

    # GUILD-SPECIFIKUS PARANCS: /joke
    @bot.tree.command(
        name="joke",
        description="Random vicc az Official Joke API-ból",
        guild=discord.Object(id=GUILD_ID)
    )
    async def joke(interaction: discord.Interaction):
        # jelezzük Discordnak, hogy dolgozunk (nem blokkoló várakozás jön)
        await interaction.response.defer(thinking=True)

        try:
            setup, punchline = await fetch_random_joke()
            # punchline spoiler tagben, hogy kattintani kelljen
            await interaction.followup.send(f"{setup}\n||{punchline}||")
        except Exception as e:
            await interaction.followup.send("Hiba történt a vicc lekérésekor. Próbáld meg később újra.")

    @bot.tree.command(
        name="gpt",
        description="Ask ChatGPT a question",
        guild=discord.Object(id=GUILD_ID)
    )
    async def gpt(interaction: discord.Interaction, text: str):
        await interaction.response.defer(thinking=True)

        try:
            response = await ask_gpt(text)
            await interaction.followup.send(response)
        except Exception as e:
            await interaction.followup.send("Hiba történt az OpenAI-jal való kommunikáció során.")

    @bot.tree.command(
        name="cat",
        description="Random macskakép",
        guild=discord.Object(id=GUILD_ID)
    )
    async def cat(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        # cache-busting query param, hogy biztosan új képet kérjünk a CATAAS-tól
        url = f"https://cataas.com/cat?random={random.randint(1, 10_000_000)}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                image_bytes = resp.content
        except Exception as e:
            await interaction.followup.send("Nem sikerült macskát letölteni. Próbáld meg később.")
            return

        # BytesIO-ból Discord fájl
        file = discord.File(io.BytesIO(image_bytes), filename="cat.png")

        # opcionálisan embedben is megjeleníthető
        embed = discord.Embed(title="Random Cat")
        embed.set_image(url="attachment://cat.png")

        await interaction.followup.send(embed=embed, file=file)

    @bot.tree.command(
        name="memes",
        description="Friss virális mémek az utóbbi 2 hétből",
        guild=discord.Object(id=GUILD_ID)
    )
    async def memes(interaction: discord.Interaction, days_back: int=14, max_memes: int=8):
        await interaction.response.defer(thinking=True)

        # API URL – ha kell, állíthatod env-ben: MEME_API_URL
        api_url = os.getenv("MEME_API_URL", "http://localhost:8000/memes")

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.get(api_url, params={"days_back": days_back, "max_memes": max_memes})
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            await interaction.followup.send("Nem sikerült lekérni a mémeket az API-tól. Próbáld meg később.")
            return

        memes_list = []

        # 1) Ha a backend úgy küld, mint a példában: [{"raw_output": "[{...}, {...}]"}]
        if isinstance(data, list) and data and isinstance(data[0], dict) and "raw_output" in data[0]:
            try:
                memes_list = json.loads(data[0]["raw_output"])
            except Exception:
                memes_list = []
        # 2) Ha egyszer majd közvetlenül listát küldesz: [{...}, {...}]
        elif isinstance(data, list):
            memes_list = data

        if not memes_list:
            await interaction.followup.send("Nem találtam friss virális mémeket.")
            return

        # Egy embed, minden mém külön field
        embed = discord.Embed(
            title="Friss virális mémek",
            description="Az utóbbi 14 napban népszerűvé vált mémek.",
        )

        # Biztonság kedvéért limitáljuk mondjuk 5-re, hogy ne legyen túl hosszú az üzenet
        for meme in memes_list[:5]:
            title = meme.get("title", "Ismeretlen mém")
            platform = meme.get("primary_platform", "ismeretlen platform")
            summary = meme.get("summary", "Nincs leírás.")
            started = meme.get("started_around", "ismeretlen")
            tags = meme.get("tags") or []
            evidence_links = meme.get("evidence_links") or []

            tags_str = ", ".join(tags) if tags else "nincsenek megadva"
            if isinstance(evidence_links, list) and evidence_links:
                links_str = " ".join(f"[{i+1}]({url})" for i, url in enumerate(evidence_links[:3]))
            else:
                links_str = "nincs link"

            field_value = (
                f"**Platform:** {platform}\n"
                f"**Kezdete:** {started}\n"
                f"**Címkék:** {tags_str}\n"
                f"**Leírás:** {summary}\n"
                f"**Linkek:** {links_str}"
            )

            embed.add_field(name=title, value=field_value, inline=False)

        await interaction.followup.send(embed=embed)