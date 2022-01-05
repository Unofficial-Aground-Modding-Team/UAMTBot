import asyncio

import aiohttp

from discord import Embed
from discord.ext import commands, tasks

from ..utils.config import BOT_COLOR, API_KEY, getsetTime, getUser

DEBUG_MODE = False


class Modio(commands.Cog):
    # guild: int = 422847864172183562  # UAMT server
    # channel: int = 518607442901204992  # Dyno Logs channel
    # channel = 535760186351157249  # Bot commands channel
    channel = 535760186351157249 if not DEBUG_MODE else 518607442901204992
    prefix = "https://api.mod.io/v1/games/{game}/mods"  # 34 = Aground
    headers = {
        'Accept': 'application/json'
    }

    def __init__(self, bot):
        self.bot = bot
        if not self.new_comments.is_running():
            self.new_comments.start()

    @staticmethod
    async def fetch(session, url, **kargs):
        async with session.get(url, **kargs) as response:
            return await response.json()

    async def getEvents(self, prefix: str, session, timeGate: int):
        params = {"_limit": 20, "api_key": API_KEY, "date_added-min": timeGate, "event_type": "MOD_COMMENT_ADDED"}
        async with session.get(
            f"{prefix}/events",
            params = params,
            headers = self.headers
        ) as events:
            if events.status != 200:
                print(events)
                raise Exception(f"Request received Status Code {events.status} when asking for recent events.")
            return (await events.json())["data"]

    async def getModsAndComments(self, prefix, session, events, timeGate):
        links = []
        visited_mods = set()
        if DEBUG_MODE:
            comment_params = {"api_key": API_KEY, "_limit": 4}
        else:
            comment_params = {"api_key": API_KEY, "date_added-min": timeGate}

        for event in events:
            mod_id = event["mod_id"]
            # New event(s) on mod with ID: {mid}
            if mod_id in visited_mods:
                continue
            visited_mods.add(mod_id)
            links.append(asyncio.ensure_future(self.fetch(
                url = f"{prefix}/{mod_id}",
                session = session,
                params={"api_key": API_KEY},
                headers= self.headers
            )))
            links.append(asyncio.ensure_future(self.fetch(
                url = f"{prefix}/{mod_id}/comments",
                session = session,
                params = comment_params,
                headers= self.headers
            )))

        return await asyncio.gather(*links)

    async def getGame(self, prefix, session):
        async with session.get(
            prefix[:-5],
            params = {"api_key": API_KEY},
            headers = self.headers
        ) as response:
            return await response.json()

    @tasks.loop(minutes=10)
    async def new_comments(self):
        if DEBUG_MODE:
            timeGate = None
        else:
            timeGate = getsetTime("modio", floor=True) - 5
        print("Looking for new comments...")
        async with aiohttp.ClientSession() as session:
            for game in self.bot.games.values():
                prefix = self.prefix.format(game = game)

                if DEBUG_MODE:
                    events = ({'mod_id': 144}, )  # MagicPlus
                    # events = ({'mod_id': 73829}, )  # Expansive Mod
                    # events = ({'mod_id': 161098}, )  # Locatinator
                else:
                    events = await self.getEvents(prefix, session, timeGate)

                if len(events) == 0:
                    print("No new comments")
                    return

                game = await self.getGame(prefix, session)
                data = await self.getModsAndComments(prefix, session, events, timeGate)
                channel = self.bot.get_channel(self.channel)

                for mod, comments in zip(data[::2], data[1::2]):
                    if "error" in mod:
                        continue

                    # Ignore mods and comments with error
                    comments = list(filter(lambda c: "error" not in c, reversed(comments["data"])))

                    content = await self.makeFields(comments, session=session, prefix=prefix, mod_id=mod["id"])

                    author = getUser(modio=int(mod["submitted_by"]["id"]))

                    embed = Embed(color = BOT_COLOR, title=f"New comments in {mod['name']}!", url=mod["profile_url"], description=content)
                    embed.set_author(
                        name= game["name"],
                        url = game["profile_url"],
                        icon_url = game["icon"]["thumb_128x128"]
                    )

                    if author:
                        discord_user = await self.bot.fetch_user(author["discord"])
                        embed.set_footer(text=discord_user.display_name, icon_url=discord_user.avatar.url)
                        if author["allow_dms"] and any(comment["user"]["id"] != mod["submitted_by"]["id"] for comment in comments):
                            if DEBUG_MODE and str(author["discord"]) != "256442550683041793":
                                raise RuntimeError("Tried to DM someone that is not Etrotta while in DEBUG mode")
                            else:
                                await discord_user.send(embed=embed)
                    else:
                        embed.set_footer(text=mod["submitted_by"]["username"], icon_url=mod["submitted_by"]["avatar"]["thumb_50x50"])

                    await channel.send(embed=embed)
        print("Done looking for new comments.")

    async def makeFields(self, comments, **kwargs):
        content = ""
        for comment in comments:
            content += await self.makeField(comment, **kwargs)
        return content

    async def makeField(self, comment, **kwargs):
        content = ""
        if comment["reply_id"] != 0:
            content += await self.makeReply(comment["reply_id"], **kwargs)
        user = getUser(modio=int(comment["user"]["id"]))
        if user:
            content += f"**<@{user['discord']}>** said: {comment['content'].strip()}\n"
        else:
            content += f"**{comment['user']['username']}** said: {comment['content'].strip()}\n"
        return content

    async def makeReply(self, reply_id, indent = 1, **kwargs):
        comment = await self.fetchReply(reply_id, **kwargs)
        content = ""
        if comment["reply_id"] != 0:
            content += await self.makeReply(comment["reply_id"], indent, **kwargs)
            indent += 1
        if indent == 1:
            content = "\n"
        user = getUser(modio=int(comment["user"]["id"]))
        if user:
            content += f"In response to **<@{user['discord']}>** saying: {comment['content'].strip()}\n{'.'*(indent*4)}"
        else:
            content += f"In response to **{comment['user']['username']}** saying: {comment['content'].strip()}\n{'.'*(indent*4)}"
        return content

    async def fetchReply(self, reply_id, *, session, prefix, mod_id):
        async with session.get(f"{prefix}/{mod_id}/comments", params = {"api_key": API_KEY, "id": reply_id}, headers = self.headers) as response:
            return (await response.json())["data"].pop()

    @new_comments.before_loop
    async def before_new_comments(self):
        await self.bot.db_loaded.wait()


def setup(bot):
    bot.add_cog(Modio(bot))
