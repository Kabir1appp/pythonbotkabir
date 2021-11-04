import discord
from asyncio.queues import Queue
from re import search
from typing import MutableSequence
from asyncio.base_events import Server
from discord import voice_client
from discord import guild
from discord.member import VoiceState
from discord.utils import get
from discord import FFmpegAudio
import youtube_dl
import asyncio
from async_timeout import timeout
from functools import partial
from discord.ext import commands
import itertools

# wrapper / decorator

bot = commands.Bot(command_prefix='!',help_command=None)


youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extrac    tor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5" ## song will end if no this line
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')

        # YTDL info dicts (data) have other useful information you might want
        # https://github.com/rg3/youtube-dl/blob/master/README.md

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(cls, ctx, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        await ctx.send(f'```ini\n[Added {data["title"]} to the Queue.]\n```') #delete after can be added

        if download:
            source = ytdl.prepare_filename(data)
        else:
            return {'webpage_url': data['webpage_url'], 'requester': ctx.author, 'title': data['title']}

        return cls(discord.FFmpegPCMAudio(source, **ffmpeg_options), data=data, requester=ctx.author)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""
        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url'], **ffmpeg_options), data=data, requester=requester)

class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds to listen to different playlists
    simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = ('bot', '_guild', '_channel', '_cog', 'queue', 'next', 'current', 'np', 'volume')

    def __init__(self, ctx):
        self.bot = ctx.bot
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = .5
        self.current = None

        ctx.bot.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            self.next.clear()

            try:
                # Wait for the next song. If we timeout cancel the player and disconnect...
                async with timeout(300):  # 5 minutes...
                    source = await self.queue.get()
            except asyncio.TimeoutError:
                return await self.destroy(self._guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(source, loop=self.bot.loop)
                except Exception as e:
                    await self._channel.send(f'There was an error processing your song.\n'
                                             f'```css\n[{e}]\n```')
                    continue

            source.volume = self.volume
            self.current = source

            self._guild.voice_client.play(source, after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set))
            self.np = await self._channel.send(f'**Now Playing:** `{source.title}` requested by '
                                               f'`{source.requester}`')
            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

            try:
                # We are no longer playing this song...
                await self.np.delete()
            except discord.HTTPException:
                pass

    async def destroy(self, guild):
        """Disconnect and cleanup the player."""
        del players[self._guild]
        await self._guild.voice_client.disconnect()
        return self.bot.loop.create_task(self._cog.cleanup(guild))

############

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.command()
async def rog(ctx):
    print("Hello")
    await ctx.channel.send("Hello")

@bot.command()
async def send(ctx):
    print(ctx.channel)
    await ctx.channel.send('Hello')


@bot.event #async/await
async def on_message(message):
    if message.content == '555':
        await message.channel.send('ขำไรมึง')  
    if message.content == 'เอ๋อ':
        await message.channel.send('มึงอะเอ๋อไอควาย')
    if message.content == 'รัก':
        await message.channel.send('รักเขาเเต่เขาไม่รักมึงอะนะ')
    if message.content == 'รักนะ':
        await message.channel.send('รักเขาเเต่เขาไม่รักมึงอะนะ')    
    if message.content == '...':
        await message.channel.send('จุดเริ่มต้นของเขากับคนใหม่ ไม่ใช่มึง!!')
    if message.content == 'ควยบอท':
        await message.channel.send('ด่าเค้าทำไมอะเตง งื้อ🥺')
    if message.content == 'บอทโง่':
        await message.channel.send('🥺')
    if message.content == 'บอท':
        await message.channel.send('ว่าไงวัยรุ่น')
    if message.content == 'บอทเเม่งเอ๋อ':
        await message.channel.send('มึงอะเอ๋อไอควาย')
    if message.content == 'บอทแม่งเอ๋อ':
        await message.channel.send('มึงอะเอ๋อไอควาย')
    if message.content == 'บอทเอ๋อ':
        await message.channel.send('🥺')
    await bot.process_commands(message)

@bot.command()
async def rp(ctx,* ,search: str):
    channel = ctx.author.voice.channel
    voice_client = get(bot.voice_clients, guild=ctx.guild)

    if voice_client == None:
        ctx.channel.send("Joined")
        await channel.connect()
        voice_client = get(bot.voice_clients, guild=ctx.guild)

    _player = get_player(ctx) 
    source = await YTDLSource.create_source(ctx, search, loop=bot.loop, download=False)

    await _player.queue.put(source)
    

players = {}
def get_player(ctx):
    try:
        player = players[ctx.guild.id]
    except:
        player = MusicPlayer(ctx)
        players[ctx.guild.id] = player

    return player


@bot.command()
async def stop(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client == None:
        await ctx.channel.send("Bot is not connected to vc")
        return

    if voice_client.channel != ctx.author.voice.channel:
        await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
        return

    voice_client.stop()


@bot.command()
async def pause(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client == None:
        await ctx.channel.send("Bot is not connected to vc")
        return

    if voice_client.channel != ctx.author.voice.channel:
        await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
        return

    voice_client.pause()



@bot.command()
async def resume(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client == None:
        await ctx.channel.send("Bot is not connected to vc")
        return

    if voice_client.channel != ctx.author.voice.channel:
        await ctx.channel.send("The bot is currently connected to {0}".format(voice_client.channel))
        return

    voice_client.resume()
    

@bot.command()
async def leave(ctx):
    del players[ctx.guild.id]
    await ctx.voice_client.disconnect()


@bot.command()
async def rplist(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)
    if voice_client == None or not voice_client.is_connected():
        await ctx.channel.send("Bot is not connected to vc", delete_after=10)
        return

    player = get_player(ctx)
    if player.queue.empty():
        return await ctx.send('There are currently no more queued songs')

    # 1 2 3
    upcoming = list(itertools.islice(player.queue._queue,0,player.queue.qsize()))
    fmt = '\n'.join(f'**`{_["title"]}`**' for _ in upcoming)
    embed = discord.Embed(title=f'Upcoming - Next {len(upcoming)}', description=fmt)
    await ctx.send(embed=embed)

@bot.command()
async def rpskip(ctx):
    voice_client = get(bot.voice_clients, guild=ctx.guild)

    if voice_client == None or not voice_client.is_connected():
        await ctx.channel.send("Bot is not connected to vc", delete_after=10)
        return

    if voice_client.is_paused():
        pass
    elif not voice_client.is_playing():
        return

    voice_client.stop()
    await ctx.send(f'**`{ctx.author}`**: Skipped the song!')


@bot.command()
async def rpclear(ctx, amount=5):
    await ctx.channel.purge(limit=amount)

@bot.command()
async def rpkick(ctx, member : discord.Member, *, reason=None):
    await member.kick(reason=reason)

@bot.command()
async def rpban(ctx, member : discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f'เเบนไอโง่ {member.mention}')

@bot.command()
async def rpunban(ctx, *, member):
    banned_users = await ctx.guild.bans()
    member_name, member_discriminator = member.split('#')

    for ban_entry in banned_users:
        user = ban_entry.user

        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f'Unbanned {user.mention}')
            return

@bot.command()
async def rphelp(ctx):
    emBed = discord.Embed(title="Tutorial Bot help", description="คำสั่ง", color=0x8892f1)
    emBed.add_field(name="เล่นเพลง", value="!rp ชื่อเพลง(ลิ้งค์)", inline=False)
    emBed.add_field(name="ลิสต์เพลง", value="!rplist)", inline=False)
    emBed.add_field(name="เเบน,ปลดเเบน", value="!rpban, !rpunban", inline=False)
    emBed.add_field(name="เตะ", value="!rpkick", inline=False)
    emBed.add_field(name="เคลียร์ข้อความ", value="!rpclear (จำนวน)", inline=False)
    emBed.set_thumbnail(url='https://media.discordapp.net/attachments/897880154024583229/903921796410142730/1634839226399.png?width=701&height=701')
    await ctx.channel.send(embed=emBed)


bot.run('OTAxMDc5NzkwNTIwNTIwNzA0.YXKp8w.KFEo0CaHxM6Rr3kXbj-R_xtG9-o')
