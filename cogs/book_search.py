import re
from discord.ext.commands import command, Cog, cooldown
from discord.ext.commands.cooldowns import BucketType

from utils.embed_pages import book_page


class BookSearch(Cog):
    def __init__(self, client):
        self.client = client

    @cooldown(1, 15, BucketType.user)
    @command(name='f', pass_context=True)
    async def search_book(self, ctx, *, arg):
        """ Command to search and find the quote from the txt file using regex
        """
        use_keywords = False
        if ctx.message.author == self.client.user:
            return  # None
        msg = list(arg.lower())

        # live
        bl_channel = ['809014777531727892', '809016986515537950']
        pos_channel = ['752196383066554538', '752193632383008770']

        # local
        # bl_channel = ['809003182306361386']
        # pos_channel = ['794281211127267330']

        whitelist = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'é',
                     'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '!', '?', ' ', '.', ';', ',', '"', "'", '…', '*', '-', ':']

        if str(ctx.channel.id) in pos_channel:
            book = 1
            channel = pos_channel

        elif str(ctx.channel.id) in bl_channel:
            channel = bl_channel
            book = 2
        else:
            ctx.command.reset_cooldown(ctx)

        if str(ctx.channel.id) in channel:
            if all(elem in whitelist for elem in msg):  # if msg in whitelist
                try:
                    await ctx.trigger_typing()
                    embed_pg, page_limit = book_page(
                        arg, book, 0, use_keywords)

                    if re.search(
                            "^quote not found!".lower(), embed_pg.description.lower()) is not None:
                        ctx.command.reset_cooldown(ctx)

                    message = await ctx.send(embed=embed_pg)

                    await message.add_reaction('⏮')
                    await message.add_reaction('◀')
                    await message.add_reaction('▶')
                    await message.add_reaction('⏭')

                    def check(reaction, user):
                        return user == ctx.author and reaction.message.id == message.id

                    i = 0
                    reaction = None
                    while True:
                        reaction, user = await self.client.wait_for('reaction_add', timeout=30.0, check=check)

                        if str(reaction) == '⏮':
                            i = 0
                            embed_pg, page_limit = book_page(
                                arg, book, i, use_keywords)
                            await message.edit(embed=embed_pg)
                        elif str(reaction) == '◀':
                            if i > 0:
                                i -= 1
                                embed_pg, page_limit = book_page(
                                    arg, book, i, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '▶':
                            if i < page_limit:
                                i += 1
                                embed_pg, page_limit = book_page(
                                    arg, book, i, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '⏭':
                            i = page_limit-1
                            embed_pg, page_limit = book_page(
                                arg, book, i, use_keywords)
                            await message.edit(embed=embed_pg)

                        await message.remove_reaction(reaction, user)

                finally:
                    await message.clear_reactions()
        else:
            ctx.command.reset_cooldown(ctx)

    @cooldown(1, 15, BucketType.user)
    @command(name='fk', pass_context=True)
    async def search_book_keys(self, ctx, *, arg):
        """ Command to search and find the quote from the txt file using regex
        """
        use_keywords = True
        if ctx.message.author == self.client.user:
            return  # None
        msg = list(arg.lower())

        # live
        bl_channel = ['809014777531727892', '809016986515537950']
        pos_channel = ['752196383066554538', '752193632383008770']

        # local
        # bl_channel = ['809003182306361386']
        # pos_channel = ['794281211127267330']

        whitelist = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'é',
                     'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '!', '?', ' ', '.', ';', ',', '"', "'", '…', '*', '-', ':']

        if str(ctx.channel.id) in pos_channel:
            book = 1
            channel = pos_channel

        elif str(ctx.channel.id) in bl_channel:
            channel = bl_channel
            book = 2
        else:
            ctx.command.reset_cooldown(ctx)

        if str(ctx.channel.id) in channel:
            if all(elem in whitelist for elem in msg):  # if msg in whitelist
                try:
                    await ctx.trigger_typing()
                    embed_pg, page_limit = book_page(
                        arg, book, 0, use_keywords)

                    if re.search(
                            "^quote not found!".lower(), embed_pg.description.lower()) is not None:
                        ctx.command.reset_cooldown(ctx)

                    message = await ctx.send(embed=embed_pg)

                    await message.add_reaction('⏮')
                    await message.add_reaction('◀')
                    await message.add_reaction('▶')
                    await message.add_reaction('⏭')

                    def check(reaction, user):
                        return user == ctx.author and reaction.message.id == message.id

                    i = 0
                    reaction = None
                    while True:
                        reaction, user = await self.client.wait_for('reaction_add', timeout=30.0, check=check)

                        if str(reaction) == '⏮':
                            i = 0
                            embed_pg, page_limit = book_page(
                                arg, book, i, use_keywords)
                            await message.edit(embed=embed_pg)
                        elif str(reaction) == '◀':
                            if i > 0:
                                i -= 1
                                embed_pg, page_limit = book_page(
                                    arg, book, i, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '▶':
                            if i < page_limit:
                                i += 1
                                embed_pg, page_limit = book_page(
                                    arg, book, i, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '⏭':
                            i = page_limit-1
                            embed_pg, page_limit = book_page(
                                arg, book, i, use_keywords)
                            await message.edit(embed=embed_pg)

                        await message.remove_reaction(reaction, user)

                finally:
                    await message.clear_reactions()
        else:
            ctx.command.reset_cooldown(ctx)


def setup(client):
    client.add_cog(BookSearch(client))
