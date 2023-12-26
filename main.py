import discord
from discord.ext import commands
import asyncio
import logging
from discord import Activity, ActivityType
from config import DISCORD_TOKEN
# from garbage_cog import GarbageBot
from music_cog import MusicBot

intents = discord.Intents().all()
activity = Activity(name="the cheers", type=ActivityType.listening)
bot = commands.Bot(command_prefix='!', activity=activity, intents=intents)


async def load():
    # await bot.add_cog(GarbageBot(bot))
    await bot.add_cog(MusicBot(bot))


async def main():
    await load()


if __name__ == "__main__":
    handler = logging.StreamHandler()
    handler.addFilter(lambda record: "Error in the pull function" not in record.msg)
    handler.addFilter(lambda record: "IO error" not in record.msg)

    asyncio.run(main())
    bot.run(DISCORD_TOKEN, log_handler=handler)
