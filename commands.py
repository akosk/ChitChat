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

