# ============================================
# Original Author: Poppyly
# Project: Tier Testing Bot
# License: CC BY-NC 4.0
#
# You may use and modify this code for
# NON-COMMERCIAL purposes only.
#
# You MUST give credit to the original author.
# Do not remove this notice.
# ============================================
import os
import asyncio
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

import config
from utils.ui import WaitlistView, QueueView

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not BOT_TOKEN:
    logging.critical("CRITICAL ERROR: DISCORD_BOT_TOKEN not found in .env file.")

class TestingBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix=commands.when_mentioned_or("!#$UNUSED"), intents=intents)

    async def setup_hook(self):
        self.add_view(WaitlistView())
        for region_key in config.REGION_DATA:
            if 'maps_to' not in config.REGION_DATA[region_key]:
                self.add_view(QueueView(region=region_key, queue_open=True))
        
        logging.info("Initialized all persistent views.")
        
        cogs_dir = 'cogs'
        for filename in os.listdir(f'./{cogs_dir}'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logging.info(f"Loaded cog: {filename}")
                except Exception as e:
                    logging.error(f"Failed to load cog {filename}: {e}", exc_info=True)
        
        try:
            guild = discord.Object(id=config.GUILD_ID)
            synced = await self.tree.sync(guild=guild)
            logging.info(f"Synced {len(synced)} application commands to guild {config.GUILD_ID}.")
        except Exception as e:
            logging.error(f"Failed to sync command tree: {e}")

bot = TestingBot()

if BOT_TOKEN:
    bot.run(BOT_TOKEN)