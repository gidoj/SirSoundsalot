import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

# load discord token from environment variables (.env file)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.bot(command_prefix='-')

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

bot.run(TOKEN)
