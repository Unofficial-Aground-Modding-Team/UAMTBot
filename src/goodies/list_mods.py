import aiohttp
import discord
from discord.ext import commands

from ..utils.config import getUser, API_KEY, BOT_COLOR
from ..utils.database import validateGame


class ModSelection(discord.ui.Select):
    "A class for the dropdown Select menu"

    def __init__(self, mods):
        self.mods = {str(mod["id"]): mod for mod in mods}
        options = []
        for mod in mods:
            desc = mod["summary"]
            if len(desc) >= 99:
                desc = desc[:95] + "..."
            options.append(
                discord.SelectOption(
                    label = mod["name"],
                    value = mod["id"],
                    description = desc
                )
            )
        super().__init__(
            placeholder = "Select a mod...",
            options = options
        )

    def makeEmbed(self, mod_id):
        mod = self.mods[str(mod_id)]
        desc = mod["description_plaintext"]
        if len(desc) >= 1500:
            desc = desc[:1490] + "[...]\n(check the mod's page for the entire description)"
        embed = discord.Embed(
            color = BOT_COLOR,
            title = mod["name"],
            description = desc,
            url = mod["profile_url"]
        )
        embed.set_thumbnail(url = mod["logo"]["thumb_640x360"])
        embed.set_author(
            name=mod["submitted_by"]["username"],
            url = mod["submitted_by"]["profile_url"],
            icon_url = mod["submitted_by"]["avatar"]["thumb_50x50"]
        )
        embed.add_field(
            name = "Mod Statistics",
            value = f"**Subscribers**: {mod['stats']['subscribers_total']}\n**Downloads**: {mod['stats']['downloads_total']}"
        )
        embed.set_footer(text=f"ID: {mod_id}")
        return embed

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed = self.makeEmbed(self.values[0]),
            ephemeral = True
        )


class ModSelectorView(discord.ui.View):
    "The class for the actual View"

    def __init__(self, modlist):
        super().__init__()
        self.add_item(ModSelection(modlist))


class ModUtils(commands.Cog):
    """---TESTING PHASE, DO NOT USE THIS YET---"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def modio(self, ctx):
        "A comand group for some Modio related commands."
        if ctx.invoked_subcommand is None:
            await ctx.reply("Invalid subcommand.")

    @modio.command(aliases=["mods", "user"])
    async def mods_by_user(self, ctx, game: str = None, member: discord.User = None):
        "Retrieves a list of all mods published by @member. Defaults to you, if none specified."
        game_name, game_id = validateGame(game, self.bot)
        if member is None:
            member = ctx.author
        user = getUser(discord = member.id)
        if user is None:
            await ctx.reply(f"Could not find the data for user {member}. They must register through `$auth register` on DMS or contacting etrotta first.")
            return
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.mod.io/v1/games/{game_id}/mods?api_key={API_KEY}&submitted_by={user['modio']}&_limit=25"
            ) as response:
                data = await response.json()
        view = ModSelectorView(data["data"])
        await ctx.send(f"Select which of <@{user['discord']}>'s mods you want to learn more about:", view = view)


def setup(bot):
    bot.add_cog(ModUtils(bot))
