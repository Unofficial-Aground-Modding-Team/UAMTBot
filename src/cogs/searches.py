from functools import wraps

from discord import Embed
from discord.ext import commands

from ..utils.database import executeQueries, validateType, TableNotFoundError
from ..utils.config import BOT_COLOR


def validateargs(*, limit: int):
    """Decorator function used to validate the arguments passed to bot commands.
    Returns a function which returns another because I wanted to specify the limit parameter for each."""
    def _helper(function: callable):
        @wraps(function)
        async def wrapper(self, ctx, game: str = None, type: str = None, identifier: str = None, maximum: int = 25):
            if maximum > limit:
                await ctx.reply(f"{maximum} maximum results? You're kidding me right?")
                return
            if any(thing == "" or thing is None for thing in (game, type, identifier)):
                await ctx.reply("Try that again, saying from where (aground items, aground enemies etc) and what (evo_gem, fire_boar etc) you want this time.")
                return
            try:
                type, _ = validateType(game, type, self.bot)
            except TableNotFoundError:
                await ctx.reply(f"{type} is not a valid type in my database. \nIf you think that this is a mistake, ping etrotta.")
                return
            return await function(self, ctx, game, type, identifier, maximum)
        return wrapper
    return _helper


class Searches(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def buildQueries(self, fields, table, identifier, mode):
        """
        Create queries that returns fields from table, where the ID matches the identifier.
        The first query uses mode Single and exact matching.
        The second query ues the provided Mode and LIKE matching.
        """
        query = f"""
        SELECT {" ,".join(fields)}
        FROM {table}
        WHERE id = $1
        """
        yield query, (identifier,), "single"

        query = f"""
        SELECT {" ,".join(fields)}
        FROM {table}
        WHERE id LIKE $1
        """
        yield query, ("%"+identifier+"%",), mode

    @commands.command(name="search", aliases=["s"])
    @validateargs(limit = 50)
    async def search(self, ctx, game: str = None, type: str = None, identifier: str = None, maximum: int = 25):
        """Searches my database for IDs and returns matches.
        Example usage:
        $search aground item wyrm
        Fetches items with wyrm in the ID, up to 50 maximum results.
        If there's only one match, it returns the XML. Else, it returns the ID of each"""
        # the Type is converted to the right table by the wrapper
        queries = self.buildQueries(["id", "xml"], type, identifier, "multiple")
        data, desc, size, mode = await executeQueries(queries)
        content = self.generateEmbed(data, maximum, mode, desc, size)
        await ctx.reply(**content)

    @commands.command(name="getpath", aliases=["getpaths", "gp", "path", "paths", "searchpath", "sp"])
    @validateargs(limit= 50)
    async def getpath(self, ctx, game: str = None, type: str = None, identifier: str = None, maximum: int = 25):
        """Searches my database for IDs and returns the path of matches.
        Example usage:
        $search aground enemies fire 50
        Fetches the Path of all enemies with fire in the ID, up to 50 maximum results.
        If there are any exact matches, it returns them. Otherwise, it compares using SQL "LIKE" operator."""
        # the Type is converted to the right table by the wrapper
        queries = self.buildQueries(["id", "path"], type, identifier, "list_each")
        data, desc, size, mode = await executeQueries(queries)
        content = self.generateEmbed(data, maximum, mode, desc, size)

        await ctx.reply(**content)

    @staticmethod
    def generateEmbed(items, maximum, mode, description, size):
        result = {}
        if size == 0:  # No matches
            embed = Embed(title = "No matching items found", color=BOT_COLOR)
            result["embed"] = embed

        elif size == 1:  # One match, used by search and getpath
            message = f"```xml\n{next(items)[1]}\n```"
            if len(message) >= 2000:
                message = message[:1900] + "```\n.....well, it was too big to display all in one place. Try using getpath and looking yourself"
            result["content"] = message

        elif mode == "single":  # Multiple matches, but all the exact same ID. Used by search and getpath
            message = "Found- well... It's complicated... ```xml\n"
            for item in items:
                message += item[1] + "\n"
            message += "```"
            if len(message) >= 2000:  # Shouldn't ever happe in getpath by the way
                message = message[:1900] + "```\n.....well, it was too big to display all in one place. Try using getpath and looking yourself"
            else:
                result["content"] = message

        elif size < maximum:  # 2 to (default: 25, Limit: 50)
            embed = Embed(title = "Multiple matches found", color=BOT_COLOR)
            if mode == "list_each":  # Used by getpath
                for item in items:
                    embed.add_field(name=item[0], value = item[1], inline = False)
            else:  # used by search
                embed.add_field(name="IDs:", value = "\n".join(item[0] for item in items), inline = False)
            embed.set_footer(text = "Try searching for the specific ID.")
            result["embed"] = embed

        else:
            embed = Embed(title = "Too many matches were found!", color=BOT_COLOR)
            result["embed"] = embed
        return result


def setup(bot):
    bot.add_cog(Searches(bot))
