import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from utils.embed_pages import embed_page, index_page, dict_page

from utils.bot_status import keep_alive
client = commands.Bot(command_prefix=['q.', 'Q.'])
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')


@client.command(pass_context=True)
async def f(ctx, *, arg):
    """ Command to search and find the quote from the txt file using regex
    """
    if ctx.message.author == client.user:
        return  # None
    msg = list(arg.lower())
    channel = ['752196383066554538', '752193632383008770']
    whitelist = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'é',
                 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '!', '?', ' ', '.', ';', ',', '"', "'", '…', '*', '-', ':']

    if str(ctx.channel.id) in channel:
        if all(elem in whitelist for elem in msg):  # if msg in whitelist
            embed_pg, page_limit = embed_page(arg)
            message = await ctx.send(embed=embed_pg)
            await message.add_reaction('⏮')
            await message.add_reaction('◀')
            await message.add_reaction('▶')
            await message.add_reaction('⏭')

            def check(reaction, user):
                return user == ctx.author

            i = 0
            reaction = None
            while True:
                if str(reaction) == '⏮':
                    i = 0
                    embed_pg, page_limit = embed_page(arg, i)
                    await message.edit(embed=embed_pg)
                elif str(reaction) == '◀':
                    if i > 0:
                        i -= 1
                        embed_pg, page_limit = embed_page(arg, i)
                        await message.edit(embed=embed_pg)
                elif str(reaction) == '▶':
                    if i < page_limit:
                        i += 1
                        embed_pg, page_limit = embed_page(arg, i)
                        await message.edit(embed=embed_pg)
                elif str(reaction) == '⏭':
                    i = page_limit-1
                    embed_pg, page_limit = embed_page(arg, i)
                    await message.edit(embed=embed_pg)
                reaction, user = await client.wait_for('reaction_add', timeout=30.0, check=check)
                await message.remove_reaction(reaction, user)

            await message.clear_reactions()


@client.command(pass_context=True)
async def d(ctx, *, arg):
    """ Command to search and find the dictionary phrase from a json file
    """
    if ctx.message.author == client.user:
        return  # None
    msg = list(arg.lower())
    channel = ['752196383066554538', '752193632383008770']
    whitelist = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'é',
                 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '!', '?', ' ', '.', ';', ',', '"', "'", '…', '*', '-', ':']
    if str(ctx.channel.id) in channel:
        if all(elem in whitelist for elem in msg):  # if msg in whitelist
            embed_pg, page_limit = dict_page(arg)
            message = await ctx.send(embed=embed_pg)
            await message.add_reaction('⏮')
            await message.add_reaction('◀')
            await message.add_reaction('▶')
            await message.add_reaction('⏭')

            def check(reaction, user):
                return user == ctx.author

            i = 0
            reaction = None
            while True:
                if str(reaction) == '⏮':
                    i = 0
                    embed_pg, page_limit = dict_page(arg, i)
                    await message.edit(embed=embed_pg)
                elif str(reaction) == '◀':
                    if i > 0:
                        i -= 1
                        embed_pg, page_limit = dict_page(arg, i)
                        await message.edit(embed=embed_pg)
                elif str(reaction) == '▶':
                    if i < page_limit:
                        i += 1
                        embed_pg, page_limit = dict_page(arg, i)
                        await message.edit(embed=embed_pg)
                elif str(reaction) == '⏭':
                    i = page_limit-1
                    embed_pg, page_limit = dict_page(arg, i)
                    await message.edit(embed=embed_pg)
                reaction, user = await client.wait_for('reaction_add', timeout=30.0, check=check)
                await message.remove_reaction(reaction, user)

            await message.clear_reactions()


@client.command(pass_context=True)
async def index(ctx):
    """ Command to show the dictionary index by parsing the dictionary excel sheet
    """
    if ctx.message.author == client.user:
        return  # None
    channel = ['752196383066554538', '752193632383008770']
    if str(ctx.channel.id) in channel:
        # 0 parameter is used in index_page(0) to ensure that the 1st page is sent first
        embed_pg, page_limit = index_page(0)
        message = await ctx.send(embed=embed_pg)
        await message.add_reaction('⏮')
        await message.add_reaction('◀')
        await message.add_reaction('▶')
        await message.add_reaction('⏭')

        def check(reaction, user):
            return user == ctx.author

        i = 0
        reaction = None
        while True:
            if str(reaction) == '⏮':
                i = 0
                embed_pg, page_limit = index_page(i)
                await message.edit(embed=embed_pg)
            elif str(reaction) == '◀':
                if i > 0:
                    i -= 1
                    embed_pg, page_limit = index_page(i)
                    await message.edit(embed=embed_pg)
            elif str(reaction) == '▶':
                if i < page_limit:
                    i += 1
                    embed_pg, page_limit = index_page(i)
                    await message.edit(embed=embed_pg)
            elif str(reaction) == '⏭':
                i = page_limit-1
                embed_pg, page_limit = index_page(i)
                await message.edit(embed=embed_pg)
            reaction, user = await client.wait_for('reaction_add', timeout=30.0, check=check)
            await message.remove_reaction(reaction, user)

        await message.clear_reactions()


@client.command(pass_context=True)
async def fhelp(ctx):
    """ Command to show the info about the different bot commands
    """
    channel = ['752196383066554538', '752193632383008770']
    if ctx.message.author == client.user:
        return  # None
    if str(ctx.channel.id) in channel:
        des = "To find quotes from the POS fic, use the command- `q.f QUOTE`"+'\n'+"For eg- `q.f Voldemort is back`"+'\n\n' + \
            "To use the POS Dictionary, use the command- `q.d string`"+'\n'+"For eg- `q.d potter prophecy`"+'\n\n'+"To look at the POS Dictionary Index, use the command- `q.index`" + '\n\n' + "Gitlab Repo- https://gitlab.com/Roguedev1/Quote-Finder/" + \
            '\n'+"Contact the developer for any queries- @RogueOne#2302"
        embed1 = discord.Embed(title='Info',
                               description=des,
                               colour=discord.Colour(0x272b28))
        await ctx.send(embed=embed1)
keep_alive()
client.run(TOKEN)
