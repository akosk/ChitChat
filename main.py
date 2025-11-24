import os
import discord
from discord import app_commands
from dotenv import load_dotenv

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

# GUILD-SPECIFIKUS PARANCS
@bot.tree.command(
    name="repeat",
    description="Megismétli a szöveget",
    guild=discord.Object(id=int(os.getenv("GUILD_ID")))
)
@app_commands.describe(text="A megismétlendő szöveg")
async def repeat(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(f"Te ezt írtad: {text}")

bot.run(TOKEN)
