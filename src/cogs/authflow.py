import aiohttp
import discord
from discord.ext import commands

from ..utils.config import registerUser, getUser, updateUser, API_KEY

"""
$auth register email@whatever.com

$auth check
discord ID, modio ID
"""


class Auth(commands.Cog):
    #"""---TESTING PHASE, DO NOT USE THIS YET---"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def auth(self, ctx):
        "A comand group for Authentication related commands"
        if ctx.invoked_subcommand is None:
            await ctx.reply("Invalid auth subcommand passed.")

    @auth.command()
    async def register(self, ctx, *, email: str = None):
        "Binds your Discord account to your mod.io account through email."
        if email is None:
            await ctx.reply("You must provide the email registered on your mod.io account to authenticate.")
            return
        try:
            async with aiohttp.ClientSession() as session:
                # First POST the email
                async with session.post(
                    "https://api.mod.io/v1/oauth/emailrequest",
                    data = {
                        "api_key": API_KEY,
                        "email": email
                    }
                ) as response:
                    pass

                # Then wait for the code
                await ctx.reply("Email sent - check your Inbox and say the code.")
                code = await self.bot.wait_for("message", check = lambda x: len(x.content) == 5 and x.author == ctx.message.author, timeout=300)

                async with session.post(
                    "https://api.mod.io/v1/oauth/emailexchange",
                    data = {
                        "api_key": API_KEY,
                        "security_code": code.content
                    }
                ) as response:
                    access_token = (await response.json())["access_token"]

                # Get the user's ID
                async with session.get(
                    "https://api.mod.io/v1/me",
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/json"
                    }
                ) as response:
                    registerUser(ctx.author.id, (await response.json())["id"])

                await ctx.reply("Validation successful!")
        except Exception as e:
            print(e)
            raise

    @auth.command(aliases = ["from"])
    @commands.is_owner()
    async def register_author(self, ctx, member: discord.Member, link: str):
        "Can only be used by Etrotta."
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.mod.io/v1/games/34/mods",
                params = {
                    "api_key": API_KEY,
                    "name_id": link.strip("<>").split("/")[-1],
                    "_limit": 1
                }
            ) as response:
                author = (await response.json())["data"][0]["submitted_by"]
        registerUser(member.id, author["id"])
        await ctx.reply(f"Registered used {member} as {author['username']}")

    @auth.command()
    async def check(self, ctx):
        "Verifies that your Discord ID and mod.io ID are linked."
        await ctx.reply(str(getUser(discord=int(ctx.message.author.id))))

    @auth.command(aliases=["toggle", "dm", "dms"])
    async def toggledms(self, ctx):
        "Toggles whenever or not you'll be notified via DMs when your mods receive new comments."
        user = getUser(discord=ctx.message.author.id)
        updateUser(user, allow_dms=not user["allow_dms"])
        await ctx.reply(f"Updated your allow_dms preference to {not user['allow_dms']}")  # "Not" here as well because the member object in memory is not updated, only the database registry


def setup(bot):
    bot.add_cog(Auth(bot))
