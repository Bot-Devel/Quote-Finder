import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from utils import embed_page
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
                # try:
                reaction, user = await client.wait_for('reaction_add', timeout=30.0, check=check)
                await message.remove_reaction(reaction, user)
                # except:
                #     break
            await message.clear_reactions()


@ client.command(pass_context=True)
async def fhelp(ctx):
    if ctx.message.author == client.user:
        return  # None
    des = "To use the bot, use the command- `q.f QUOTE`"+'\n'+"For eg- `q.f Voldemort is back`"+'\n\n' + \
        "Github Repo- https://github.com/Roguedev1/Quote-Finder" + \
        '\n'+"Contact the developer for any queries- @RogueOne#2302"
    embed1 = discord.Embed(title='Info',
                           description=des,
                           colour=discord.Colour(0x272b28))
    await ctx.send(embed=embed1)
client.run(TOKEN)
