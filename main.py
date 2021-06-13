import os
import re
import asyncio
from itertools import cycle


import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# to use repl+uptime monitor
from utils.bot_uptime import start_server
client = commands.Bot(command_prefix=['q', 'Q'], help_command=None)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

with open("data/status_quotes.txt", "r") as file:
    quotes = cycle(file.readlines())


@tasks.loop(seconds=1)
async def bot_status():

    await client.wait_until_ready()

    await client.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name=(next(quotes)).strip()
        )
    )

    await asyncio.sleep(15)


# Comment out this function during development to see the
# traceback of all the errors
@client.event
async def on_command_error(ctx, error):

    # if cooldown error
    if isinstance(error, discord.ext.commands.errors.CommandOnCooldown):

        # Get the current timeout from the error message
        timeout = (re.search(r"\d+\b", str(error))).group(0)

        embed = discord.Embed(
            description=str(error) +
            f"\nThis message will self-destruct in {error.retry_after:.2f}s. \
             You will be able to use the bot again when this message is deleted."
        ).set_footer(text=ctx.message.author)

        message = await ctx.send(embed=embed)

        await asyncio.sleep(int(timeout))
        await message.delete()

    else:
        print(error)

bot_status.start()
start_server()
client.load_extension("exts.cogs.book_search")
client.load_extension("exts.cogs.dictionary_search")
client.load_extension("exts.cogs.dictionary_index")
client.load_extension("exts.cogs.help")
client.load_extension("exts.cogs.settings")
client.run(TOKEN)
