from string import Template

from discord import Embed
from discord.ext import commands

from ..utils.database import executeQueries, validateType, TableNotFoundError
from ..utils.config import BOT_COLOR


def checkClean(parameter: str):
    if any(dangerous in parameter for dangerous in "();\\/?[]{}&*^$#!+|\"'`/*+`"):  # most of these are probably safe but are not used so whatever
        return False
    return True


def attributeAndFormat(parameter):
    if "." in parameter:
        *prefixes, parameter = parameter.split(".")
    else:
        prefixes = None
    attribute, castAs, *_ = parameter.split(":") + ["text"]
    if castAs == "text":
        return (attribute, "::" + castAs, prefixes)
    else:
        return (attribute, "::text::" + castAs, prefixes)


class ParsingError(Exception):
    pass


class XmlSearch(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def BuildXQuery(columns, table, node, filterby, orderby):
        query = ""  # Define empty / base query

        query += "SELECT "  # Add the SELECT statement
        for col in columns:
            if col[2] is not None:  # prefixes
                prefixes = col[2]
                if len(prefixes) == 2 and prefixes[0] == "" and prefixes[1] == "":
                    query += f"(xpath('//@{col[0]}', xml))[1]{col[1]} as {col[0]}, "
                else:
                    query += f"(xpath('/{node}/{'/'.join(prefixes)}/@{col[0]}', xml))[1]{col[1]} as {col[0]}, "
            else:
                query += f"(xpath('/{node}/@{col[0]}', xml))[1]{col[1]} as {col[0]}, "  # Add each XPATH (Xml Path) attribute requested
        query = query[:-2]  # Removes the last ", "

        query += f"\nFROM {table}"  # Add the FROM statement

        if filterby:  # If there any Filters, add them
            query += "\nWHERE "
            for (key, op, value) in filterby:
                query += f"xpath_exists('/{node}/@{key[0]}', xml) AND "
                if op == "~" and value != "":
                    query += f"(xpath('/{node}/@{key[0]}', xml))[1]{key[1]} LIKE '%{value}%' AND "  # Add each XPATH (Xml Path) attribute requested
                else:
                    query += f"(xpath('/{node}/@{key[0]}', xml))[1]{key[1]} {op} '{value}'{key[1]} AND "  # Add each XPATH (Xml Path) attribute requested
                # (xpath('(/item/@attack)', xml))[1]::text::int
            query = query[:-4]  # Removes the extra "AND "

        if orderby:
            query += "\nORDER BY "
            for (key, order) in orderby:
                query += f"{key[0]} {order}, "
            query = query[:-2]

        query += "\nLIMIT 50"

        yield query, None

    @commands.command(name = "xmlsearch", aliases=["xs", "xsearch", "xmls"])
    async def XMLsearch(self, ctx, game, *, message: str):
        """
        Searches for XML attributes in the target table.
        Example: $xsearch id, attack:int desc @items id~fire attack:int>10
        Returns the ID and Attack of all items with fire in the ID AND the attack higher than 10, sorted by attack (descending)

        *There must be no spaces between key=value (= ~ > <) filters. >= and <= are not supported
        **Commas are optional and ignored if present, use spaces to separate attributes
        ***Limited to 50 results
        """
        columns = []  # XML Attributes to return, such as id, type or element
        orderby = []  # Which returned ones shall be used to sort the results, if any
        filterby = []  # Filter attributes by attribute:type=value, <, > or ~ (~ is a implemented as LIKE). For "exists", you can use "attribute~"
        table = None  # Table, such as Item
        try:

            for parameter in message.replace(",", "").split(" "):

                if parameter.startswith(("!", "$", "@", "%")):  # Specify TABLE (from)
                    table, node = self.parseTable(game, parameter)

                elif any((sep := s) in parameter for s in "<>~="):  # Specify FILTERS (where)
                    filterby.append(self.parseFilter(parameter, sep))  # noqa... dw it works, the linter is being dumb

                elif parameter == "desc" or parameter == "asc":  # Specify ORDER BY (desc / asc), based on the last Attribute requested
                    orderby.append(self.parseSort(parameter, columns))

                else:  # Add Attributes, and if specified which type to cast it to - example attack:int
                    if checkClean(parameter):
                        columns.append(attributeAndFormat(parameter))
                    else:
                        raise ParsingError("The parameters include non-allowed characters, try again without special characters.")
        except ParsingError as e:
            await ctx.reply(e.args[0])
            return
        if columns == [] or table is None:  # Checks if it's valid
            await ctx.reply("You must specify at least one column and the source table. If you specified the table, it might not be available.")
            return

        query = self.BuildXQuery(columns, table, node, filterby, orderby)

        data, description, size = await executeQueries(query)

        await ctx.reply(**self.generateEmbed(data, 50, description, size, table.replace("_", " ").title()))

    def parseTable(self, game, parameter):
        if checkClean((p := parameter[1:])):
            try:
                return validateType(game, p, self.bot)
            except TableNotFoundError:
                raise ParsingError(f"{p} is not a valid type in my database!")
        else:
            raise ParsingError("The parameters include non-allowed characters, try again without special characters.")

    @staticmethod
    def parseFilter(parameter, separator):
        if parameter.count(separator) >= 2:
            raise ParsingError(f"Malformed filter at {parameter}")
        elif separator == "<" and (i := parameter.index("<")+1) < len(parameter) and parameter[i] == ">":
            separator = "<>"
        key, value = parameter.split(separator)

        if separator == "~" and key == "" and value != "":
            key, value = value, key

        if key and (value or separator == "~") and checkClean(key) and checkClean(value):
            return (attributeAndFormat(key), separator, value)
        raise ParsingError("Invalid filtering statement!")

    @staticmethod
    def parseSort(parameter, columns):
        try:
            return (columns[-1], parameter)
        except IndexError:
            raise ParsingError("You cannot search by DESC / ASC alone - those are used to sort the results based on the previous attribute")

    @staticmethod
    def generateEmbed(items, maximum, description, size, header):
        result = {}
        if size == 0:  # No matches
            embed = Embed(title = "No matching items found", color=BOT_COLOR)
            result["embed"] = embed

        else:  # List each value
            template = Template("$desc=$value\n")
            message = f'```ini\n[{header}]\n'
            for item in items:
                for i, desc in enumerate(description):
                    if type(item[i]) == str:
                        message += template.substitute(desc=desc, value=f'"{item[i]}"')
                    else:
                        message += template.substitute(desc=desc, value = item[i])
                message += "\n"
            if len(message) >= 2000:
                result["content"] = message[:1900] + "```...aaand it was far too long to display :{"
            else:
                result["content"] = message[:-1] + '```'
        return result


def setup(bot):
    bot.add_cog(XmlSearch(bot))
