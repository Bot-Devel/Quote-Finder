import re

from discord.ext.commands import command, Cog, cooldown
from discord.ext.commands.cooldowns import BucketType

from adapters.book import Book
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

        reset_flag = False
        book_number, channel, reset_flag = check_channel(
            ctx.channel.id, reset_flag)

        if reset_flag:
            ctx.command.reset_cooldown(ctx)

        if str(ctx.channel.id) in channel:
            try:
                await ctx.trigger_typing()

                book = Book(arg, book_number, 0, use_keywords)
                book.book_page()

                if re.search(
                    "^quote not found!".lower(),
                        book.embed_msg.description.lower()) is not None:
                    ctx.command.reset_cooldown(ctx)

                try:
                    message = await ctx.message.reply(
                        embed=book.embed_msg, mention_author=False)

                except Exception:
                    message = await ctx.message.channel.send(
                        embed=book.embed_msg)

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
                        book = Book(arg, book_number, page, use_keywords)
                        book.book_page()
                        await message.edit(embed=book.embed_msg)

                    elif str(reaction) == '◀':
                        if page > 0:

                            page -= 1
                            book = Book(arg, book_number, page, use_keywords)
                            book.book_page()
                            await message.edit(embed=book.embed_msg)

                    elif str(reaction) == '▶':
                        if page < book.page_limit:

                            page += 1
                            book = Book(arg, book_number, page, use_keywords)
                            book.book_page()
                            await message.edit(embed=book.embed_msg)

                    elif str(reaction) == '⏭':

                        page = book.page_limit-1
                        book = Book(arg, book_number, page, use_keywords)
                        book.book_page()
                        await message.edit(embed=book.embed_msg)

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

        reset_flag = False
        book_number, channel, reset_flag = check_channel(
            ctx.channel.id, reset_flag)

        if reset_flag:
            ctx.command.reset_cooldown(ctx)

        if str(ctx.channel.id) in channel:
            try:
                await ctx.trigger_typing()
                book = Book(arg, book_number, 0, use_keywords)
                book.book_page()

                if re.search(
                        "^quote not found!".lower(), book.embed_msg.description.lower()) is not None:
                    ctx.command.reset_cooldown(ctx)

                try:
                    message = await ctx.message.reply(
                        embed=book.embed_msg, mention_author=False)

                except Exception:
                    message = await ctx.message.channel.send(
                        embed=book.embed_msg)

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
                        book = Book(arg, book_number, page, use_keywords)
                        book.book_page()
                        await message.edit(embed=book.embed_msg)

                    elif str(reaction) == '◀':
                        if page > 0:

                            page -= 1
                            book = Book(arg, book_number, page, use_keywords)
                            book.book_page()
                            await message.edit(embed=book.embed_msg)

                    elif str(reaction) == '▶':
                        if page < book.page_limit:

                            page += 1
                            book = Book(arg, book_number, page, use_keywords)
                            book.book_page()
                            await message.edit(embed=book.embed_msg)

                    elif str(reaction) == '⏭':

                        page = book.page_limit-1
                        book = Book(arg, book_number, page, use_keywords)
                        book.book_page()
                        await message.edit(embed=book.embed_msg)

                    await message.remove_reaction(reaction, user)

            finally:
                try:
                    await message.clear_reactions()

                except UnboundLocalError:
                    pass

        else:
            ctx.command.reset_cooldown(ctx)


def setup(client):
    client.add_cog(BookSearch(client))
