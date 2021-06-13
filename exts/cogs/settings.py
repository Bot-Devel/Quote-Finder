import os
import re
import time
import random
import string
import portalocker
from subprocess import Popen

from discord import Embed, File
from discord.ext.commands import command, Cog

from exts import config

bot_dev = [x.strip() for x in (config.get(
    'users', 'bot_dev')).split(",")]

archivist = [x.strip() for x in (config.get(
    'users', 'archivist')).split(",")]


class Settings(Cog):
    def __init__(self, client):
        self.client = client

    @command(aliases=['update'])
    async def update_data(self, ctx):
        """ Command to fetch latest dictionary files from google
            sheets
        """

        start = time.time()

        if ctx.message.author == self.client.user:
            return

        if not str(ctx.message.author.id) in bot_dev+archivist:
            return await ctx.message.reply(
                embed=Embed(
                    description="You are not authorized to use this command."),
                mention_author=False
            )

        message = await ctx.message.reply(
            embed=Embed(description="Starting update..."),
            mention_author=False
        )

        pos_sheet1 = "data/dictionary/POS Dictionary - Sheet1.csv"
        pos_sheet2 = "data/dictionary/POS Dictionary - Sheet2.csv"

        request_id = ''.join(random.choice(string.ascii_lowercase)
                             for i in range(10))

        with open(f"data/update_{request_id}.log", "wb") as logfile:
            with portalocker.Lock(pos_sheet1):
                process_sheet1 = Popen(['wget', '-O', pos_sheet1,
                                        'https://docs.google.com/spreadsheets/d/1k-GXwnmJGLtp_IUNCkPI-B4IT5u-qDBEEH7KwJPLBuA/export?gid=0&format=csv'],
                                       stdout=logfile,
                                       stderr=logfile
                                       )

            with portalocker.Lock(pos_sheet1):
                process_sheet2 = Popen(['wget', '-O', pos_sheet2,
                                        'https://docs.google.com/spreadsheets/d/1k-GXwnmJGLtp_IUNCkPI-B4IT5u-qDBEEH7KwJPLBuA/export?gid=1143251734&format=csv'],
                                       stdout=logfile,
                                       stderr=logfile
                                       )

        process_sheet1.communicate()
        process_sheet2.communicate()

        end = time.time()
        await message.edit(embed=Embed(
            description=f"Update successfully finished in {(end-start):.2f}s"
        ),  mention_author=False)

        if re.search("-log", ctx.message.content):
            await ctx.message.reply(
                file=File(f"data/update_{request_id}.log"),
                mention_author=False)

        os.remove(f"data/update_{request_id}.log")


def setup(client):
    client.add_cog(Settings(client))
