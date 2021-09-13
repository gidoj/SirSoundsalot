import os
from dotenv import load_dotenv
import urllib.request
import re

import discord
from discord.ext import commands

# load discord token from environment variables (.env file)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='-')

def get_url(title):
    url = ''
    if ('youtube.com' in title[0]):
        url = title[0]
    else:
        query = '+'.join(title)
        query_url = f'https://www.youtube.com/results?search_query={query}'
        content = urllib.request.urlopen(query_url).read().decode('utf-8')
        res = re.findall('\/watch\?v=(.{11})', content)
        url = f'https://www.youtube.com/watch?v={res[0]}'
    return url

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='play')
async def play(ctx, *title):
    if title:
        url = get_url(title)
        response = f'Playing {url}'
        await ctx.send(response)
    else:
        await ctx.send('Please specify a source.')

bot.run(TOKEN)

