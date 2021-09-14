import os, youtube_dl, discord, urllib.request, re
from dotenv import load_dotenv # environmental varaibles
from discord.ext import commands

# load discord token from environment variables (.env file)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()
bot = commands.Bot(command_prefix='$')

queue = {} # track server queues (serverID: [(video_url, video_title),])


def speed_check(s):
    '''Raise error if video download too slow
    '''
    speed = s.get('speed')

    if speed and speed <= 77*1024 and s.get('downloaded_bytes', 0) >= 300000:
        ## <= 77 kb/s
        raise youtube_dl.utils.DownloadError('Abnormal downloading speed drop.')


def intersect(a, b):
    '''Checks if any element in a belongs to b as well
    '''
    for elt in a:
        if elt in b:
            return True
    return False


def get_url(title):
    '''Parse user given title into a watchable youtube link
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
    '''Get video title from youtube url
    '''
    with youtube_dl.YoutubeDL({}) as ydl:
        title = ydl.extract_info(url, download=False)['title']

    return title


def download_as_mp3(url, guild_id):
    '''Download url from youtube and save as mp3
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
        ydl.add_progress_hook(speed_check)
        ydl.download([url])

    return filename


def queue_song(ctx, url, title):
    '''Push new song into queue; play immediately if queue previously empty
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
    '''Play next song in queue
    '''
    if not queue[ctx.guild.id]:
        # queue empty, no song to play next
        return

    if ctx.voice_client:
        url, title = queue[ctx.guild.id][0]
        try:
            filename = download_as_mp3(url, ctx.guild.id) 

            print(f'Playing {title} ({url})')
            source = discord.FFmpegPCMAudio(filename)
            player = ctx.voice_client.play(source, after=lambda e: end_song(ctx))
        
        except youtube_dl.utils.DownloadError:
            print('\n----------\nDownload error, trying again.\n----------\n')
            play_next(ctx)


def end_song(ctx):
    '''Clean up after song ends
    '''
    global queue

    if ctx.guild.id in queue and queue[ctx.guild.id]:
        ## remove song that just finished
        queue[ctx.guild.id] = queue[ctx.guild.id][1:]
        play_next(ctx)


@bot.event
async def on_ready():
    ## startup 
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='play')
async def play(ctx, *title):
    '''Play video from youtube (title or link)
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
    '''List the queue of songs
    '''
    queue_str =  '>>> ' ## format indent on discord
    if ctx.guild.id in queue and queue[ctx.guild.id]:
        pos = 1
        for _, title in queue[ctx.guild.id]:
           queue_str += f'({pos}) *{title}*\n'
           pos += 1
    else:
        queue_str += "*EMPTY*"

    await ctx.send(queue_str)
       

@bot.command(name='skip')
async def skip(ctx):
    '''Skip the current song
    '''
    ctx.voice_client.stop()


@bot.command(name='rm')
async def remove(ctx, n: int):
    '''Remove nth song from queue
    '''
    global queue
    
    if ctx.guild.id not in queue or not queue[ctx.guild.id] or \
            n < 1 or n > len(queue[ctx.guild.id]):
        await ctx.send('Invalid index!')
    elif n == 1:
        ## removing current song = skip
        await skip(ctx)
    else:
        to_remove = queue[ctx.guild.id][n-1][1]
        queue[ctx.guild.id] = queue[ctx.guild.id][:n-1] + queue[ctx.guild.id][n:]
        await ctx.send(f'Removed {to_remove} from queue. Updated queue:')
        await list_queue(ctx) ## display updated queue
    

@bot.command(name='swap')
async def swap(ctx, n: int, m: int):
    '''Swap nth and mth songs in queue (*can't swap with first!)
    '''
    if ctx.guild.id not in queue or not queue[ctx.guild.id] or \
            n < 2 or n > len(queue[ctx.guild.id]) or \
            m < 2 or m > len(queue[ctx.guild.id]):
        await ctx.send('Invalid index!')
    else:
        nth = queue[ctx.guild.id][n-1]
        mth = queue[ctx.guild.id][m-1]
        queue[ctx.guild.id][n-1] = mth
        queue[ctx.guild.id][m-1] = nth
        await list_queue(ctx)


@bot.command(name='clear')
async def clear_queue(ctx):
    '''Clear the queue
    '''
    if ctx.guild.id in queue:
        queue[ctx.guild.id] = None
    ctx.voice_client.stop()


@bot.command(name='die')
async def die(ctx):
    '''Murder the bot
    '''
    queue[ctx.guild.id] = None
    await ctx.voice_client.disconnect()


bot.run(TOKEN)



