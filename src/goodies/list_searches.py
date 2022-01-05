import discord
from discord.ext import commands

from ..utils.database import executeQueries
from ..utils.config import BOT_COLOR

from ..cogs.searches import validateargs


class ModSelection(discord.ui.Select):
    "A class for the dropdown Select menu"

    def __init__(self, items):
        self.items = {}
        options = []
        for item in items:
            key = item.path + item.id
            options.append(
                discord.SelectOption(
                    label = item.id,
                    description = item.path,
                    value = key
                )
            )
            self.items[key] = item.xml
        super().__init__(
            placeholder = "Select one...",
            options = options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            content = self.sendDetails(self.items[self.values[0]]),
            ephemeral = True
        )

    @staticmethod
    def sendDetails(item):
        message = "```xml\n"
        # for item in items:
        #     message += item[1] + "\n"
        message += item + "\n"
        message += "```"
        if len(message) >= 2000:  # Shouldn't ever happen in getpath by the way
            message = message[:1900] + "```\n.....well, it was too big to display all in one place. Try using getpath and looking yourself"
        return message


class ListItemsView(discord.ui.View):
    "The class for the actual View"

    def __init__(self, modlist):
        super().__init__(timeout = 5*60)
        self.add_item(ModSelection(modlist))

    async def on_timeout(self):
        embed = discord.Embed(title="This message has timed out, please use the command again.", color = BOT_COLOR)
        try:
            await self.message.edit(embed=embed)  # Not gonna bother to remove nor update the View since the paths are still useful.
        except discord.errors.NotFound:
            print("Failed to edit the message. It may have been deleted.")


class ListSearches(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    def buildQueries(self, table, identifier):
        """
        Create queries that returns fields from table, where the ID matches the identifier.
        The first query uses mode Single and exact matching.
        The second query ues the provided Mode and LIKE matching.
        """
        query = f"""
        SELECT id, path, xml
        FROM {table}
        WHERE id LIKE $1
        LIMIT 25
        """
        yield query, ("%"+identifier+"%",)

    @commands.command(name="list", aliases=["l"])
    @validateargs(limit = 25)
    async def list_search(self, ctx, game: str = None, type: str = None, identifier: str = None, maximum: int = 25):
        """Searches my database for IDs and returns a dropdown menu with the matches.
        Example usage:
        $list aground item wyrm
        Fetches all items with "wyrm" in the ID, up to 25 results."""
        # the Type is converted to the right table by the wrapper
        queries = self.buildQueries(type, identifier)
        data, desc, size = await executeQueries(queries)
        if size == 0:  # No matches
            await ctx.reply(embed=discord.Embed(title = "No matching data found", color=BOT_COLOR))
            return
        else:
            embed = discord.Embed(title = f"Select which {type.split('_')[1]} you want to see:", color = BOT_COLOR)
            view = ListItemsView(data)
            view.message = await ctx.reply(embed = embed, view = view)


def setup(bot):
    bot.add_cog(ListSearches(bot))
