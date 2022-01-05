from collections import namedtuple

import asyncio
# from functools import cache
# from async_lru import alru_cache
import asyncpg
from asyncpg.exceptions import PostgresError

from .config import USER, PASSWORD, HOST, DATABASE


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # Don't ask me


def remember(function):
    result = None

    async def wrapper():
        nonlocal result
        if result is None:
            result = await function()
            return result
        else:
            return result
    return wrapper


class TableNotFoundError(Exception):
    pass


class GameNotFoundError(Exception):
    pass


async def executeQueries(builder):
    """
    Execute queries provided by a Builder generator.
    Expects (query, arguments, mode) to be provided by next() every time.
    Returns the data (query result), description, the amount of rows and details (provided by the builder) of the first query that provides a result.
    """
    connection = await getConnection()
    data = None
    details = []
    try:
        while not data:
            query, arguments, *details = next(builder)

            if arguments:
                data = await connection.fetch(query, *arguments)
            else:
                data = await connection.fetch(query)
    except StopIteration:
        return data, None, 0, *[None]*len(details)  # None N times, where N is the length of details
    except PostgresError:
        print(f"Got an Error while handling query: \n{query}\nArguments provided: {arguments}")
        raise
    else:
        builder.close()
    finally:
        await connection.close()
    nt = namedtuple("QueryData", dict(data[0]).keys())
    return (nt(*entry) for entry in data), tuple(dict(data[0]).keys()), len(data), *details


@remember
async def getGames():
    """Request all games from the Database.
    Formatted as (Name, Tables, Mod.io ID)"""
    connection = await getConnection()
    query = """
    SELECT name, tables, modio
    FROM games
    """
    games = await connection.fetch(query)
    await connection.close()
    return [(game[0], game[1], game[2]) for game in games]


@remember
async def getPool():
    pool = await asyncpg.create_pool(user=USER, password=PASSWORD, host=HOST, database=DATABASE)
    return pool


async def closePool():
    pool = await getPool()
    await pool.close()


async def getConnection():
    # connection = await asyncpg.connect(user=USER, password=PASSWORD, host=HOST, database=DATABASE)
    connection = await (await getPool()).acquire(timeout = 30)
    return connection


game_shorthands = {"a": "aground", "ag": "aground", "s": "stardander", "az": "aground_zero"}  # I only have Aground in the db but still added the rest anyway


def validateGame(game: str, bot):
    "Validates a game's name."
    types = bot.games
    if game in game_shorthands:
        game = game_shorthands[game]
    if game in types:
        return game, types[game]
    else:
        raise GameNotFoundError("Specified game not found")


def validateType(game: str, type: str, bot):
    """
    Tries to validate a type, checking against a list of (game, type) tuples.
    If any likely matches are found, returns it. Otherwise, raises TableNotFoundError.
    """
    types = bot.dbtypes
    game, _ = validateGame(game, bot)
    if (game, type) in types:
        node = type
    elif (game, type[:-1]) in types:
        node = type[:-1]
    elif (game, type[:-3] + "y") in types:
        node = type[:-3] + "y"
    else:
        raise TableNotFoundError("Specified type not found")
    return game + "_" + node, node


if __name__ == "__main__":
    # games = asyncio.run(getGames())
    # print(games)

    def test():
        yield "SELECT id, path FROM aground_item WHERE id LIKE '%wyrm%'", None
    entries, keys, size = asyncio.run(executeQueries(test()))
    print(keys)
    for row in entries:
        print(row)
        print(row.id)
