import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from utils import quote_find, chapter_processing
client = commands.Bot(command_prefix='q.')
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


@client.command(pass_context=True)
async def f(ctx, *, arg):
    if ctx.message.author == client.user:
        return  # None
    msg = list(arg.upper())
    channel = ['752196383066554538', '752193632383008770']
    whitelist = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U',
                 'V', 'W', 'X', 'Y', 'Z', 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, '!', '?', ' ', '.', ';', ',', '"', "'", '…', '*', '-', ':']
    if str(ctx.channel.id) in channel:
        quote_found_ctr = 0  # quote found counter to know if the quote was found during the query
        if all(elem in whitelist for elem in msg):  # if msg in whitelist
            chapter_desription, chapter_heading, quote_found_ctr = quote_find(
                arg)
            if quote_found_ctr == 1:  # to fix the  UnboundLocalError: local variable 'loc_of_and' referenced before assignment error
                chapter_title, chapter_url = chapter_processing(
                    chapter_heading)
        if quote_found_ctr == 1:
            embed1 = discord.Embed(title=''.join(chapter_title),
                                   url=chapter_url,
                                   description=chapter_desription,
                                   colour=discord.Colour(0x272b28))
            await ctx.send(embed=embed1)
        else:
            embed2 = discord.Embed(
                description="Quote not found!",
                colour=discord.Colour(0x272b28))
            await ctx.send(embed=embed2)


@client.command(pass_context=True)
async def fhelp(ctx):
    if ctx.message.author == client.user:
        return  # None
    des = "To use the bot, use the command- `q.f QUOTE`"+'\n'+"For eg- `q.f Voldemort is back`"+'\n\n' + \
        "Github Repo- https://github.com/Roguedev1/Quote-Finder" + \
        '\n'+"Contact the developer for any queries- @RogueOne"
    embed1 = discord.Embed(title='Info',
                           description=des,
                           colour=discord.Colour(0x272b28))
    await ctx.send(embed=embed1)
client.run(TOKEN)
