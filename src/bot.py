import asyncio

import discord
from discord.ext import commands
from asyncpg.exceptions import PostgresError

from .utils.database import getGames, GameNotFoundError, TableNotFoundError, closePool
from .utils.config import BOT_TOKEN


class Bot(commands.Bot):
    """Class for my Bot"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_loaded = asyncio.Event()

    async def on_ready(self):  # This can run more than once, if the bot goes offline or I put my PC in Sleeping mode
        if not self.db_loaded.is_set():  # idk if it will still cause issues should the bot try to run this again before it has finished loading but whatever
            games = await getGames()  # List[(game, tables, mod.io id)]
            self.games = {game[0]: game[2] for game in games}
            self.dbtypes = []
            for game in games:
                for table in game[1]:
                    self.dbtypes.append((game[0], table))
            self.db_loaded.set()
        print("Ready to go!")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.UserInputError):
            print(error)
            await ctx.reply("You just raised an user input error, congratulations & ping etrotta if you need more details or help\n>:[")
            return
        if isinstance(error, commands.CheckFailure):
            await ctx.reply("You cannot use that command!")
            return
        if isinstance(error, commands.CommandNotFound):
            await ctx.reply("Command not found.")
            return
        if isinstance(error, commands.ConversionError):
            await ctx.reply("The type conversion failed for the arguments you passed.")
            return
        if isinstance(error, commands.CommandError) and isinstance(error.__cause__, PostgresError):
            await ctx.reply("My database did not like that command!!!")
            return
        if isinstance(error, commands.CommandError) and isinstance(error.__cause__, TableNotFoundError):
            await ctx.reply("Specified Table not found in my database >:[")
            return
        if isinstance(error, commands.CommandError) and isinstance(error.__cause__, GameNotFoundError):
            await ctx.reply("Specified Game not found in my database >:[")
            return
        await ctx.reply("I got an error and I do not know what to do about it D:")
        raise error


activity = discord.Game("with fishes")
bot = Bot(command_prefix="$", activity=activity)
bot.allowed_mentions = discord.AllowedMentions.none()

bot.load_extension(".cogs.admin", package="src")
bot.load_extension(".cogs.searches", package="src")
bot.load_extension(".cogs.xmlsearch", package="src")
bot.load_extension(".cogs.modio", package="src")
bot.load_extension(".cogs.authflow", package="src")
bot.load_extension(".goodies.list_mods", package="src")
bot.load_extension(".goodies.list_searches", package="src")

try:
    bot.run(BOT_TOKEN)
finally:
    asyncio.run(closePool())  # I'm pretty sure that this doesn't works tbh
