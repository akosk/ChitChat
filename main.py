import os
import discord
from discord import app_commands
from dotenv import load_dotenv
from services import ask_gpt, check_moderation
from commands import register_commands

print(discord.__version__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
print("GUILD_ID from .env:", GUILD_ID)

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
        print("[on_message] Checking moderation for content:", repr(content))
        if not content:
            return  # ignore purely empty messages

        moderation_result = await check_moderation(content)
        if moderation_result is None:
            return  # fail-open: if moderation fails, do nothing extra

        print ("[on_message] Moderation result:", moderation_result)
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

# Register all slash commands
register_commands(bot)

bot.run(TOKEN)


