import json
import time
import math
import sqlite3
from configparser import ConfigParser

from discord import Colour

parser = ConfigParser()
parser.read("src/config.ini")

BOT_TOKEN = parser["Bot"]["BOT_TOKEN"]
BOT_COLOR = Colour(0xe784ee)

USER = parser["Postgre"]["user"]
PASSWORD = parser["Postgre"]["password"]
DATABASE = parser["Postgre"]["database"]
HOST = parser["Postgre"]["host"]

API_KEY = parser["Modio"]["API_KEY"]


# modio cog - timer
def getsetTime(identifier: str, *, floor = False):
    """Retrieves the current Time on the file and updates it to Now"""
    now = time.time()
    if floor:
        now = math.floor(now)
    with open("src/config.json", "r+") as file:
        data = json.load(file)
        if identifier in data:
            value = data[identifier]
        else:
            print(f"{identifier} not found in config.json, defaulting to now")
            value = now
        data[identifier] = now
        file.seek(0)
        json.dump(data, file)
        file.truncate()
    return value


# authflow / modio cogs - connect to database to get user data
def registerUser(discord_id, modio_id):
    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO users (discord_id, modio_id, allow_dms) VALUES (?, ?, True)",
        (discord_id, modio_id)
    )
    connection.commit()
    connection.close()


def getUser(*, discord = None, modio = None):
    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()
    try:
        if discord:
            cursor.execute("SELECT * FROM users WHERE discord_id = ?", (int(discord),))
        elif modio:
            cursor.execute("SELECT * FROM users WHERE modio_id = ?", (int(modio),))
    except Exception:
        print(f"Interface error with Discord ID {discord} and Mod.io ID {modio}")
        raise
    result = cursor.fetchall()
    connection.close()
    if result:
        return {"discord": result[0][0], "modio": result[0][1], "allow_dms": result[0][2]}
    return None


def updateUser(user, **kwargs):
    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()
    query = "UPDATE users "
    for arg, value in kwargs.items():
        query += f"SET {arg} = {value} "
    query += f"WHERE users.discord_id = {user['discord']} AND users.modio_id = {user['modio']}"
    # print(query)
    cursor.execute(query)
    connection.commit()
    connection.close()


if __name__ == "__main__":
    connection = sqlite3.connect("users.db")
    cursor = connection.cursor()
    # """
    # CREATE TABLE IF NOT EXISTS users (
    #     discord_id INTEGER,
    #     modio_id INTEGER,
    #     allow_dms BOOLEAN DEFAULT TRUE
    # )
    # """
    # cursor.execute(
    #     """INSERT INTO users (discord_id, modio_id) VALUES (?, ?)""",
    #     (256442550683041793, 32129)  # etrotta's
    # )
    # cursor.execute(
    #     "ALTER TABLE users ADD COLUMN allow_dms BOOLEAN DEFAULT TRUE"  # I added it some time after creating the table :x
    # )
    cursor.execute("SELECT * FROM users WHERE discord_id = ?", (256442550683041793,))
    print(cursor.fetchall()[0])
    # connection.commit()
    connection.close()
