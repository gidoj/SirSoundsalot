import os, youtube_dl, discord, urllib.request, re
from dotenv import load_dotenv # environmental varaibles
from discord.ext import commands

# load discord token from environment variables (.env file)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()
bot = commands.Bot(command_prefix='$')

queue = {} # track server queues (serverID: [(video_url, video_title),])

def intersect(a, b):
    '''Checks if any element in a belongs to b as well
    '''
    for elt in a:
        if elt in b:
            return True
    return False


def get_url(title):
    '''Parse user given title into a watchable youtube link.
    '''
    if 'youtube.com' in title[0]:
        ## no need to parse if already youtube link
        url = title[0]
    else:
        query = '+'.join(title)
        query_url = f'https://www.youtube.com/results?search_query={query}'
        content = urllib.request.urlopen(query_url).read().decode('utf-8')
        res = re.findall('\/watch\?v=(.{11})', content)
        url = f'https://www.youtube.com/watch?v={res[0]}'
    return url


def title_from_url(url):
    '''Get video title from youtube url.
    '''
    with youtube_dl.YoutubeDL({}) as ydl:
        title = ydl.extract_info(url, download=False)['title']

    return title


def download_as_mp3(url, guild_id):
    '''Download url from youtube and save as mp3.
    '''
    filename = str(guild_id) + '.mp3' # one file per server
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
        ydl.download([url])

    return filename


def queue_song(ctx, url, title):
    '''Push new song into queue; play immediately if queue previously empty.
    '''
    global queue
    
    if ctx.guild.id in queue and queue[ctx.guild.id]:
        # push song into queue
        print(f'Queueing {title}')
        queue[ctx.guild.id].append((url, title))
    else:
        # play immediately if queue previously empty
        queue[ctx.guild.id] = [(url, title),]
        play_next(ctx)


def play_next(ctx):
    '''Play next song in queue.
    '''
    if not queue[ctx.guild.id]:
        # queue empty, no song to play next
        return

    if ctx.voice_client:
        url, title = queue[ctx.guild.id][0]
        filename = download_as_mp3(url, ctx.guild.id) 
    
        print(f'Playing {title} ({url})')
        source = discord.FFmpegPCMAudio(filename)
        player = ctx.voice_client.play(source, after=lambda e: end_song(ctx))


def end_song(ctx):
    '''Clean up after song ends.
    '''
    global queue

    if queue[ctx.guild.id]:
        ## remove song that just finished
        queue[ctx.guild.id] = queue[ctx.guild.id][1:]
        play_next(ctx)


@bot.event
async def on_ready():
    ## startup 
    print(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, youtube_dl.utils.DownloadError):
        await ctx.send('Error downloading link. Clearing queue. Try again.')
        await die(ctx)
    else:
        raise error



@bot.command(name='play')
async def play(ctx, *title):
    '''Play video from youtube (title or link).
    '''

    ## only connect to voice if not already connected
    ## and author in a channel
    if (ctx.author.voice):
        channel = ctx.author.voice.channel
        if (channel not in [bc.channel for bc in bot.voice_clients]):
            if intersect([gc.name for gc in ctx.guild.channels], 
                [bc.channel.name for bc in bot.voice_clients]):
                await ctx.send('You\'re not in the right channel!')
                return
            else: 
                channel = ctx.author.voice.channel
                await channel.connect()
    else:
        await ctx.send('You need to join a voice channel!')
        return

    if not title:
        await ctx.send('Please specify a source.')
        return

    url = get_url(title)
    real_title = title_from_url(url)
    if ctx.guild.id in queue and queue[ctx.guild.id]:
        await ctx.send(f'Queuing {real_title} ({url})')
    else:
        await ctx.send(f'Playing {real_title} ({url})')
    queue_song(ctx, url, real_title)


@bot.command(name='queue')
async def list_queue(ctx):
    '''List the queue of songs.
    '''
    if queue[ctx.guild.id]:
        queue_str =  '>>> ' ## format indent on discord
        pos = 1
        for _, title in queue[ctx.guild.id]:
           queue_str += f'({pos}) *{title}*\n'
           pos += 1

        await ctx.send(queue_str)
       

@bot.command(name='skip')
async def skip(ctx):
    '''Skip the current song.
    '''
    ctx.voice_client.stop()


@bot.command(name='die')
async def die(ctx):
    '''Murder the bot.
    '''
    queue[ctx.guild.id] = None
    await ctx.voice_client.disconnect()


bot.run(TOKEN)



