import os
from dotenv import load_dotenv # environmental varaibles
import urllib.request, re ## opening and parsing webpages
import youtube_dl

import discord
from discord.ext import commands

# load discord token from environment variables (.env file)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()
bot = commands.Bot(command_prefix='$')

players = {} # track players for each server (serverID: player)

def get_url(title):
    '''Parse user given title into a watchable youtube link.
    '''
    url = ''
    if ('youtube.com' in title[0]):
        ## no need to parse if already youtube link
        url = title[0]
    else:
        query = '+'.join(title)
        query_url = f'https://www.youtube.com/results?search_query={query}'
        content = urllib.request.urlopen(query_url).read().decode('utf-8')
        res = re.findall('\/watch\?v=(.{11})', content)
        url = f'https://www.youtube.com/watch?v={res[0]}'
    return url


def download_as_mp3(url, guild_id):
    '''Download url from youtube and save as mp3
    '''
    filename = str(guild_id) + '.mp3'
    if os.path.exists(filename):
        os.remove(filename)
    ydl_opts = {
            'outtmpl': filename,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            }
    
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        title = ydl.extract_info(url, download=False)['title']
        ydl.download([url])

    return (title, filename)


def intersect(a, b):
    '''Checks if any element in a belongs to b as well
    '''
    for elt in a:
        if elt in b:
            return True
    return False

@bot.event
async def on_ready():
    ## startup 
    print(f'{bot.user.name} has connected to Discord!')

@bot.event
async def on_command_error(ctx, error):
    raise error

@bot.command(name='play')
async def play(ctx, *title):
    '''Search youtube for title (unless already link) and play in user's voice channel
    '''
    if (ctx.author.voice):
        channel = ctx.author.voice.channel
        if (channel not in [bc.channel for bc in bot.voice_clients]):
            if (intersect([gc.name for gc in ctx.guild.channels], [bc.channel.name for bc in bot.voice_clients])):
                await ctx.send('You\'re not in the right channel!')
                return
            else: 
                channel = ctx.author.voice.channel
                voice = await channel.connect()
    else:
        await ctx.send('You need to join a voice channel!')
        return

    if not title:
        await ctx.send('Please specify a source.')
        return

    ## download youtube link to play as mp3
    url = get_url(title)
    real_title, filename = download_as_mp3(url, ctx.guild.id) 

    response = f'Playing {real_title} ({url})'
    await ctx.send(response)

    source = discord.FFmpegPCMAudio(filename)
    player = voice.play(source)
    


@bot.command(name='die')
async def die(ctx):
    await ctx.voice_client.disconnect()

bot.run(TOKEN)

