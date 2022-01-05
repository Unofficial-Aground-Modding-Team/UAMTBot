import os
import asyncio
import asyncpg
from xml.dom import minidom
import re
from collections import defaultdict
from configparser import ConfigParser

ignored_tags = [
    "image", "animation", "tile", "tilesheet",  # image related
    "sound", "volume", "soundSet", "bar", "font",  # sound and settings|misc
    "textGroup", "renderOverlay", "set", "defaultFishing", "offsets",  # more misc
    "name", "description", "author", "version", "include", "versionCheck", "website", "disableWarning"  # mod.xml
]

prefixes = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Aground\data\core",
    r"C:\Program Files (x86)\Steam\steamapps\common\Aground\data\mods\full"
]

langs = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Aground\data\core\lang\en_US.xml",
    r"C:\Program Files (x86)\Steam\steamapps\common\Aground\data\mods\full\lang\en_US.xml",
    r"C:\Program Files (x86)\Steam\steamapps\common\Aground\data\mods\full\hybrid_path\en_US.xml"
]

data = defaultdict(list)

expression = re.compile(r"<(?=[0-9 =]+)")


def listStuff(filepath):
    # WHY ARE THE HYBRID PATH LANGS NOT IN A LANG FOLDER, WHY AIROM WHY
    if "en_US" in filepath or "pt_BR" in filepath or "de_DE" in filepath or "ru_RU" in filepath or "smileys" in filepath:
        return
    with open(filepath, "r") as file:
        try:
            content = file.read()
        except Exception:
            print(filepath)
            raise
    # relative path ; the remove the prefix (see: prefixes)
    relpath = filepath[46:].replace("\\", "/")
    content = content.replace(r"&", r"&amp;")  # Escapes &
    content = expression.sub(string=content, repl="&lt;")  # Escapes <, when it comes before numbers

    for element in minidom.parseString(content).childNodes[0].childNodes:
        type = element.nodeName
        if type == "init":
            for sub in element.childNodes:
                if hasattr(element, "getAttribute") and type not in ignored_tags:
                    data[type].append((element.getAttribute("id"), element.toxml(), relpath))
        elif hasattr(element, "getAttribute") and type not in ignored_tags:
            data[type].append((element.getAttribute("id"), element.toxml(), relpath))


for prefix in prefixes:
    for root, dirs, files in os.walk(prefix):
        for file in files:
            if file[-4:] == ".xml":
                listStuff(root+"\\"+file)


async def insertRecords(data):
    parser = ConfigParser()
    parser.read("dbinfo.ini")

    connection = await asyncpg.connect(
        host=parser["Postgre"]["host"],
        database=parser["Postgre"]["database"],
        user=parser["Postgre"]["user"],
        password=parser["Postgre"]["password"]  # Yeah yeah I know password in plain text whatever
    )
    await connection.execute("""CREATE TABLE IF NOT EXISTS games
    (name TEXT, modio INTEGER, tables TEXT[])""")
    await connection.execute("DELETE FROM games WHERE name = 'aground'")
    await connection.execute("INSERT INTO games (name, modio, tables) VALUES ('aground', 34, $1)", [*data.keys()])
    for table, values in data.items():
        # await connection.execute("DROP TABLE IF EXISTS $1", f"aground_{table}")
        await connection.execute(f"DROP TABLE IF EXISTS aground_{table}")
        # await connection.execute("CREATE TABLE IF NOT EXISTS $1 (id TEXT, xml XML, path TEXT)", f"aground_{table}")
        await connection.execute(f"CREATE TABLE IF NOT EXISTS aground_{table} (id TEXT, xml XML, path TEXT)")
        # await connection.executemany("INSERT INTO $1 VALUES $2", zip(repeat(f"aground_{table}"), values))
        await connection.executemany(f"INSERT INTO aground_{table} VALUES ($1, $2, $3)", values)
    await connection.close()

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(insertRecords(data))
