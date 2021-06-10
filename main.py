import os
import re
import asyncio
import aiohttp

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

# to use repl+uptime monitor
from utils.bot_uptime import start_server
client = commands.Bot(command_prefix=['q', 'Q'], help_command=None)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


@client.event
async def on_ready():
    await client.change_presence(
        activity=discord.Game(name="qhelp")
    )


@tasks.loop(seconds=10.0)
async def bot_uptime():

    await client.wait_until_ready()

    while not client.is_closed():
        async with aiohttp.ClientSession() as session:
            async with session \
                    .get("https://quote-finder-bot.roguedev1.repl.co/") as response:

                await asyncio.sleep(20)


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

bot_uptime.start()
start_server()
client.load_extension("exts.cogs.book_search")
client.load_extension("exts.cogs.dictionary_search")
client.load_extension("exts.cogs.dictionary_index")
client.load_extension("exts.cogs.help")
client.run(TOKEN)
