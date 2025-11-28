import io
import os
import discord
from discord import app_commands
from dotenv import load_dotenv
import httpx  # <-- új import
import random
from openai import AsyncOpenAI

print(discord.__version__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
print("GUILD_ID from .env:", GUILD_ID)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

intents = discord.Intents.default()
intents.message_content = True


class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild_obj = discord.Object(id=GUILD_ID)
        try:
            cmds = await self.tree.sync(guild=guild_obj)
            print(f"[setup_hook] Synced {len(cmds)} commands to guild {GUILD_ID}")
            for c in cmds:
                print(f"  - {c.name} (guild={c.guild_id})")
        except Exception as e:
            print("[setup_hook] Command sync failed:", repr(e))

    async def on_ready(self):
        print("Bot ready as", self.user)
        print("Guild-ok, ahol bent van:")
        for g in self.guilds:
            print(" ", g.name, g.id)

    async def on_message(self, message: discord.Message):
        # ignore the bot's own messages to avoid loops
        if message.author == self.user:
            return

        # 1) "Subscribe" behavior: you see every message here
        print(f"[on_message] #{message.channel} | {message.author}: {message.content}")

        # 2) Example: simple keyword reaction
        if message.content.lower().startswith("ping"):
            await message.channel.send("pong")

        # 3) Example: react with an emoji
        if "macska" in message.content.lower():
            try:
                await message.add_reaction("🐱")
            except discord.HTTPException:
                pass

        # 4) Moderation check with omni-moderation-latest
        content = (message.content or "").strip()
        if not content:
            return  # ignore purely empty messages

        moderation_result = await check_moderation(content)
        if moderation_result is None:
            return  # fail-open: if moderation fails, do nothing extra

        # moderation_result.flagged is True if anything is over threshold
        if getattr(moderation_result, "flagged", False):
            # Ask GPT to rephrase the message politely
            try:
                polite_rephrase = await ask_gpt(
                    "Rewrite the following Discord message to be polite, "
                    "respectful, and non-offensive, keeping the same meaning. "
                    "Only return the rewritten sentence.\n\n"
                    f"Original: {content}"
                )
            except Exception:
                # If GPT fails, send a simple warning only
                await message.reply(
                    f"{message.author.mention} Ez nem volt túl kedves. "
                    "Kérlek, fogalmazd át szebben."
                )
                return

            # Reply to the user with a warning + suggested rephrase
            # (Hungarian text to match your existing style)
            warn_text = (
                f"{message.author.mention} Ez nem volt túl kedves. "
                "Így lehetne szebben mondani:\n"
                f"> {polite_rephrase}"
            )
            await message.reply(warn_text)

bot = MyBot()

# === SEGÉDFÜGGVÉNY: VICC LEKÉRÉSE ASZINKRON HTTP-VEL ===
async def fetch_random_joke() -> tuple[str, str]:
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
    Returns the first moderation result, or None on error.
    """
    try:
        resp = await openai_client.moderations.create(
            model="omni-moderation-latest",
            input=text,
        )
        # resp.results is a list; we only care about the first one
        if not resp.results:
            return None
        return resp.results[0]
    except Exception as e:
        print(f"[ERROR] moderation failed: {type(e).__name__}: {e}")
        return None

# GUILD-SPECIFIKUS PARANCS: /repeat
@bot.tree.command(
    name="repeat",
    description="Megismétli a szöveget",
    guild=discord.Object(id=int(os.getenv("GUILD_ID")))
)
@app_commands.describe(text="A megismétlendő szöveg")
async def repeat(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(f"Te ezt írtad: {text}")

# GUILD-SPECIFIKUS PARANCS: /joke
@bot.tree.command(
    name="joke",
    description="Random vicc az Official Joke API-ból",
    guild=discord.Object(id=int(os.getenv("GUILD_ID")))
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
    guild=discord.Object(id=int(os.getenv("GUILD_ID")))
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
    guild=discord.Object(id=int(os.getenv("GUILD_ID")))
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



bot.run(TOKEN)
