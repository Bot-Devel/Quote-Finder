import re

from discord.ext.commands import command, Cog, cooldown
from discord.ext.commands.cooldowns import BucketType

from utils.embed_pages import book_page
from exts.utils.channels import check_channel


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

        with open("data/whitelist.txt", "r") as f:
            whitelist = f.read().split("\n")

        reset_flag = False
        book, channel, reset_flag = check_channel(ctx.channel.id, reset_flag)

        if reset_flag:
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

                    page = 0
                    reaction = None
                    while True:
                        reaction, user = await self.client.wait_for('reaction_add', timeout=30.0, check=check)

                        if str(reaction) == '⏮':
                            page = 0
                            embed_pg, page_limit = book_page(
                                arg, book, page, use_keywords)
                            await message.edit(embed=embed_pg)
                        elif str(reaction) == '◀':
                            if page > 0:
                                page -= 1
                                embed_pg, page_limit = book_page(
                                    arg, book, page, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '▶':
                            if page < page_limit:
                                page += 1
                                embed_pg, page_limit = book_page(
                                    arg, book, page, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '⏭':
                            page = page_limit-1
                            embed_pg, page_limit = book_page(
                                arg, book, page, use_keywords)
                            await message.edit(embed=embed_pg)

                        await message.remove_reaction(reaction, user)

                finally:
                    try:
                        await message.clear_reactions()
                    except UnboundLocalError:
                        pass
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

        with open("data/whitelist.txt", "r") as f:
            whitelist = f.read().split("\n")

        reset_flag = False
        book, channel, reset_flag = check_channel(ctx.channel.id, reset_flag)

        if reset_flag:
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

                    page = 0
                    reaction = None
                    while True:
                        reaction, user = await self.client.wait_for('reaction_add', timeout=30.0, check=check)

                        if str(reaction) == '⏮':
                            page = 0
                            embed_pg, page_limit = book_page(
                                arg, book, page, use_keywords)
                            await message.edit(embed=embed_pg)
                        elif str(reaction) == '◀':
                            if page > 0:
                                page -= 1
                                embed_pg, page_limit = book_page(
                                    arg, book, page, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '▶':
                            if page < page_limit:
                                page += 1
                                embed_pg, page_limit = book_page(
                                    arg, book, page, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '⏭':
                            page = page_limit-1
                            embed_pg, page_limit = book_page(
                                arg, book, page, use_keywords)
                            await message.edit(embed=embed_pg)

                        await message.remove_reaction(reaction, user)

                finally:
                    await message.clear_reactions()
        else:
            ctx.command.reset_cooldown(ctx)


def setup(client):
    client.add_cog(BookSearch(client))
