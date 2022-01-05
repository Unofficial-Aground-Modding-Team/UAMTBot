from discord.ext import commands

from ..utils.database import executeQueries


def builder(arg):
    yield arg, None, None


class Admin(commands.Cog):
    """Admin commands for Etrotta only."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="query", aliases=["q"])
    @commands.is_owner()
    async def query(self, ctx, *, arg):
        "Can only be used by @etrotta."
        data, _, description, _ = await executeQueries(builder(arg))
        message = "```" + str(description) + "\n"
        for row in data:
            message += ", ".join(str(element) for element in row) + "\n"
        message += "```"
        if len(message) > 2000:
            await ctx.reply("The message would be too large :[")
        else:
            await ctx.reply(message)

    @commands.command(name="eval", aliases=["e"])
    @commands.is_owner()
    async def evalmsg(self, ctx, *, arg):
        "Can only be used by @etrotta."
        try:
            result = await eval(arg)
        except TypeError:
            result = eval(arg)
        if result:
            await ctx.reply(result)


def setup(bot):
    bot.add_cog(Admin(bot))
