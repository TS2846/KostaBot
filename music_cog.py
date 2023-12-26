from typing import List, Union
import discord
from discord.ext import commands
from config import FFMPEG_OPTIONS
from music import Song, extract_music
from asyncio import run_coroutine_threadsafe
from errors import InvalidClient, JoinError
from random import shuffle
from functools import partial


class MusicBot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.queue: {int: List[Song]} = {}
        self.curr_song: {int, Song} = {}
        self.voice_client: {int, discord.VoiceClient} = {}

    @staticmethod
    def get_id(ctx: commands.Context) -> int:
        return int(ctx.guild.id)

    async def join_voice_channel(self, ctx: commands.Context, client: discord.VoiceState):
        if not client:
            raise InvalidClient("client is null")
        guild_id = self.get_id(ctx)
        current_client = self.get_voice_client(guild_id)
        if current_client:
            # we are already in a voice channel
            current_client.pause()
            await current_client.move_to(client.channel)
        else:
            # else attempt connecting to the user channel
            current_client = await client.channel.connect()
        if not current_client:
            raise JoinError("could not join client")
        self.voice_client[guild_id] = current_client

    def get_voice_client(self, guild_id) -> Union[discord.VoiceClient, None]:
        return self.voice_client.get(guild_id, None)

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            guild_id = int(guild.id)
            self.queue[guild_id] = []
            self.curr_song[guild_id] = None
            self.voice_client[guild_id] = None

    @commands.command(
        name="join",
        aliases=["j"]
    )
    async def join(self, ctx: commands.Context) -> discord.VoiceClient | None:
        try:
            await self.join_voice_channel(ctx, ctx.author.voice)
            guild_id = self.get_id(ctx)
            vc = self.get_voice_client(guild_id)
            await ctx.send(f"Joined channel {ctx.author.voice.channel}.")
            return vc
        except InvalidClient:
            await ctx.send("You are not in a voice channel...")
        except JoinError:
            await ctx.send("Couldn't not join your voice channel")

    @commands.command(
        name="leave",
        aliases=["l"]
    )
    async def leave(self, ctx: commands.Context):
        guild_id = self.get_id(ctx)
        vc = self.get_voice_client(guild_id)
        if not vc:
            return
        if vc.is_playing() and self.curr_song[guild_id]:
            self.queue[guild_id].insert(0, self.curr_song[guild_id])
        await vc.disconnect()
        self.voice_client[guild_id] = None
        await ctx.send("Bot disconnected.")

    @commands.command(
        name="play",
        aliases=["p"]
    )
    async def play(self, ctx: commands.Context, *args):
        # if not connected then join user Channel
        guild_id = self.get_id(ctx)
        vc = self.get_voice_client(guild_id)
        if not (vc or (vc := await self.join(ctx))):
            return

        # if paused then resume
        if vc.is_paused():
            vc.resume()
            await ctx.send("Resumed.")

        query = " ".join(args)
        # if there's a query then add the results to queue
        if query:
            # retrieve song from YT and add to queue
            await self.add_to_queue(ctx, query)

        # if queue is empty alert the user
        if not self.queue[guild_id]:
            self.curr_song[guild_id] = None
            await ctx.send("Queue is empty!")
            return

        # if already playing then return
        if vc.is_playing():
            return

        # Otherwise start playing the first song in the queue
        song = self.queue[guild_id].pop(0)

        # what to do once song has finished playing
        def play_after(_):
            _vc = self.get_voice_client(guild_id)
            if not _vc or not _vc.is_connected() or _vc.is_playing() or _vc.is_paused():
                return
            future = run_coroutine_threadsafe(self.play(ctx), self.bot.loop)
            try:
                future.result()
            except Exception as e:
                print(e)

        vc.play(discord.FFmpegPCMAudio(song.source, **FFMPEG_OPTIONS), after=play_after)
        self.curr_song[guild_id] = song
        await self.nowplaying(ctx)

    @commands.command(
        name="next",
        aliases=["n"]
    )
    async def add_next(self, ctx: commands.Context, *args):
        query = " ".join(args)

        if not query:
            await ctx.send("No arguments given...")
            return

        await self.add_to_queue(ctx, query, 0)
        await self.play(ctx)

    @commands.command(
        name="skip"
    )
    async def skip(self, ctx: commands.Context, *args):
        skip = 1
        guild_id = self.get_id(ctx)
        if self.queue[guild_id]:
            try:
                skip = int(args[0] if args else 1)
            except ValueError:
                await ctx.send("Invalid skip value")
                return

            if not (0 <= skip <= len(self.queue[guild_id])):
                await ctx.send(f"Cannot skip {skip} songs there are only {len(self.queue[guild_id])} in the queue")
                return

            if skip == 0:
                return

            self.queue[guild_id] = self.queue[guild_id][skip - 1:]

        vc = self.get_voice_client(guild_id)
        if vc:
            # just stop the current song
            # the after function will take care of playing the next song
            vc.stop()

    @commands.command(
        name="pause"
    )
    async def pause(self, ctx: commands.Context):
        guild_id = self.get_id(ctx)
        vc = self.get_voice_client(guild_id)
        if vc and vc.is_playing():
            vc.pause()
            await ctx.send("Paused.")

    @commands.command(
        name="clear",
        aliases=["c"]
    )
    async def clear(self, ctx: commands.Context):
        await self.pause(ctx)
        guild_id = self.get_id(ctx)
        vc = self.get_voice_client(guild_id)
        if vc:
            vc.stop()
        self.queue[guild_id] = []

    @commands.command(
        name="queue",
        aliases=["q"]
    )
    async def _queue(self, ctx: commands.Context, *args):
        guild_id = self.get_id(ctx)
        if not self.queue[guild_id]:
            await ctx.send("Nothing in the Queue!")
            return
        queue_count = int(args[0]) if args else 10
        msg = f"Queued ({len(self.queue[guild_id])} songs):\n" + "\n".join(
            [f"{i + 1}. {song.title}" for i, song in zip(range(queue_count), self.queue[guild_id])])
        embed = discord.Embed(title=f"Queue", description=f"Requested by - {ctx.message.author.mention}",
                              color=0xFF5733)
        # print the next 5 songs in the queue
        embed.add_field(name="Now playing", value=msg)
        embed.add_field(name=f"Up Next ({len(self.queue[self.get_id(ctx)])} total) ",
                        value=f"\n".join(
                            [f"{i + 1}. {song.title}" for i, song in zip(range(10), self.queue[self.get_id(ctx)])]),
                        inline=True
                        )
        embed.set_thumbnail(url=f"https://i.ytimg.com/vi/{self.queue[guild_id][0].songId}/default.jpg")
        await ctx.send(msg)

    @commands.command(
        name="repeat",
        aliases=["r"]
    )
    async def repeat(self, ctx: commands.Context):
        guild_id = self.get_id(ctx)
        vc = self.get_voice_client(guild_id)
        if not vc or not self.curr_song[guild_id]:
            return

        await self.pause(ctx)
        self.queue[guild_id].insert(0, self.curr_song[guild_id])
        vc.stop()

    async def add_to_queue(self, ctx: commands.Context, query, index=-1) -> Union[List[Song], None]:
        guild_id = self.get_id(ctx)
        songs = []
        if query:
            try:
                songs, error_count = await extract_music(query, self.bot.loop)
            except Exception as e:
                print(e)
                await ctx.send("Something went wrong... Try again")
                return
            if not songs:
                await ctx.send("Unable to extract any songs from the query... :(")
                return
            if error_count:
                await ctx.send(f"Couldn't download {error_count} songs from Youtube")
            # add songs to the queue
            if index == -1:
                for song in songs:
                    self.queue[guild_id].append(song)
            else:
                for song in reversed(songs):
                    self.queue[guild_id].insert(index, song)

        vc = self.get_voice_client(guild_id)

        # if already playing music, do nothing
        if vc and vc.is_playing():
            if songs:
                msg = "Added to Queue: " + ", ".join(
                    [song.title for _, song in zip(range(5), songs)])
                msg = msg + ", and more..." if len(songs) > 5 else msg
                await ctx.send(msg)
        return songs

    @commands.command(
        name="shuffle",
        aliases=['s']
    )
    async def shuffle(self, ctx: commands.Context):
        guild_id = self.get_id(ctx)
        if len(self.queue[guild_id]) < 1:
            await ctx.send("Queue is empty.")
            return
        shuffle(self.queue[guild_id])
        await ctx.send(f"Shuffled {len(self.queue[guild_id])} songs.")

    # removes song at index
    @commands.command(
        name="remove"
    )
    async def remove(self, ctx: commands.Context, *args):
        guild_id = self.get_id(ctx)
        remove = 1
        if self.queue[guild_id]:
            try:
                remove = int(args[0] if args else 1)
            except ValueError:
                await ctx.send("Invalid value!")
                return
            if not (0 <= remove <= len(self.queue[guild_id])):
                await ctx.send(f"Cannot skip song at position {remove} as there are only "
                               f"{len(self.queue[guild_id])} songs in the queue")
                return
        self.queue[guild_id].remove(remove - 1)

    @commands.command(
        name="nowplaying",
        aliases=['np']
    )
    async def nowplaying(self, ctx: commands.Context):
        if not self.curr_song[self.get_id(ctx)]:
            await ctx.send("Nothing is playing.")
        song = self.curr_song[self.get_id(ctx)]
        embed = discord.Embed(title=f"Now Playing - {song.title}", url=f"https://www.youtube.com/watch?v={song.songId}",
                              description=f"Requested by - {ctx.message.author.mention}",
                              color=0xFF5733)
        # print the next 5 songs in the queue
        embed.set_author(name="MusicBot", url='https://www.youtube.com/watch?v=m2OR_JaXDaM',
                         icon_url='https://i.imgur.com/8x96Le5.png')
        embed.add_field(name=f"Up Next ({len(self.queue[self.get_id(ctx)])} total) ",
                        value=f"\n".join(
                            [f"{i + 1}. {song.title}" for i, song in zip(range(5), self.queue[self.get_id(ctx)])]),
                        inline=True
                        )
        embed.set_thumbnail(url=f"https://i.ytimg.com/vi/{song.songId}/default.jpg")

        view = discord.ui.View()
        skipbutton = discord.ui.Button(label="Skip", style=discord.ButtonStyle.green)
        skipbutton.callback = partial(self.button_skip, ctx=ctx)
        clearbutton = discord.ui.Button(label="Clear", style=discord.ButtonStyle.red)
        clearbutton.callback = partial(self.button_clear, ctx=ctx)
        view.add_item(skipbutton)
        view.add_item(skipbutton)
        await ctx.send(embed=embed, view=view)

    async def button_skip(self, interaction, ctx=None):
        await self.skip(ctx)

    async def button_clear(self, interaction, ctx=None):
        await self.clear(ctx)

# class MusicView(discord.ui.View):
#     def __init__(self):
#         super().__init__()
#
#     @discord.ui.button(label='Next', style=discord.ButtonStyle.primary, emoji='🦧')
#     async def button_callback(self, interaction, button):
#         await interaction.response.send_message("you stupid ni")
