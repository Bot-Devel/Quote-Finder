import os
import re
import time
import portalocker
from subprocess import Popen

from discord import Embed, File
from discord.ext.commands import command, Cog

from exts import config

bot_devs = [x.strip() for x in (config.get(
    'users', 'bot_devs')).split(",")]


class Settings(Cog):
    def __init__(self, client):
        self.client = client

    @command()
    async def update(self, ctx):
        """ Command to fetch latest dictionary files from google 
            sheets
        """

        start = time.time()

        if ctx.message.author == self.client.user:
            return  # None

        if not str(ctx.message.author.id) in bot_devs:
            return await ctx.message.reply(
                embed=Embed(
                    description="You are not authorized to use this command."),
                mention_author=False
            )

        message = await ctx.message.reply(
            embed=Embed(description="Starting update!"),
            mention_author=False
        )

        pos_sheet1 = "data/dictionary/POS Dictionary - Sheet1.csv"
        pos_sheet2 = "data/dictionary/POS Dictionary - Sheet2.csv"

        with open("data/update.log", "wb") as logfile:
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

        if re.search("-log", ctx.message.content):
            await ctx.message.reply(
                file=File("data/update.log"),
                mention_author=False)

        end = time.time()
        await message.edit(embed=Embed(
            description=f"Update successfully finished in {(end-start):.2f}s"
        ),  mention_author=False)

        os.remove("data/update.log")


def setup(client):
    client.add_cog(Settings(client))
