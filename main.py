import os
import discord
from discord import app_commands
from dotenv import load_dotenv
import httpx  # <-- új import

print(discord.__version__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
print("GUILD_ID from .env:", GUILD_ID)

intents = discord.Intents.default()

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
    name="cat",
    description="Random macskakép",
    guild=discord.Object(id=int(os.getenv("GUILD_ID")))
)
async def cat(interaction: discord.Interaction):
    await interaction.response.send_message("Random macska:\nhttps://cataas.com/cat")


bot.run(TOKEN)
