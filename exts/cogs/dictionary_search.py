import re
from discord.ext.commands import command, Cog, cooldown
from discord.ext.commands.cooldowns import BucketType

from utils.embed_pages import dict_page
from exts import config

pos_channel_cooldown = [x.strip() for x in (config.get(
    'cooldown channels', 'pos_channel')).split(",")]

pos_channel_whitelist = [x.strip() for x in (config.get(
    'whitelist channels', 'pos_channel')).split(",")]


class DictionarySearch(Cog):
    def __init__(self, client):
        self.client = client

    @cooldown(1, 15, BucketType.user)
    @command(name='d', pass_context=True)
    async def search_dictionary(self, ctx, *, arg):
        """ Command to search and find the dictionary phrase from a json file
        """
        use_keywords = False
        if ctx.message.author == self.client.user:
            return  # None
        msg = list(arg.lower())

        with open("data/whitelist.txt", "r") as f:
            whitelist = f.read().split("\n")

        if str(ctx.channel.id) in pos_channel_whitelist:
            ctx.command.reset_cooldown(ctx)

        if str(ctx.channel.id) in pos_channel_cooldown+pos_channel_whitelist:
            if all(elem in whitelist for elem in msg):  # if msg in whitelist
                try:
                    await ctx.trigger_typing()
                    embed_pg, page_limit = dict_page(arg, 0, use_keywords)

                    if re.search(
                            "^dictionary data not found!", embed_pg.description.lower()) is not None:
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
                            embed_pg, page_limit = dict_page(
                                arg, page, use_keywords)
                            await message.edit(embed=embed_pg)
                        elif str(reaction) == '◀':
                            if page > 0:
                                page -= 1
                                embed_pg, page_limit = dict_page(
                                    arg, page, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '▶':
                            if page < page_limit:
                                page += 1
                                embed_pg, page_limit = dict_page(
                                    arg, page, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '⏭':
                            page = page_limit-1
                            embed_pg, page_limit = dict_page(
                                arg, page, use_keywords)
                            await message.edit(embed=embed_pg)

                        await message.remove_reaction(reaction, user)

                finally:
                    await message.clear_reactions()
        else:
            ctx.command.reset_cooldown(ctx)

    @cooldown(1, 15, BucketType.user)
    @command(name='dk', pass_context=True)
    async def search_dictionary_keys(self, ctx, *, arg):
        """ Command to search and find the dictionary phrase from a json file
        """
        use_keywords = True
        if ctx.message.author == self.client.user:
            return  # None
        msg = list(arg.lower())

        with open("data/whitelist.txt", "r") as f:
            whitelist = f.read().split("\n")

        if str(ctx.channel.id) in pos_channel_cooldown+pos_channel_whitelist:
            if all(elem in whitelist for elem in msg):  # if msg in whitelist
                try:
                    await ctx.trigger_typing()
                    embed_pg, page_limit = dict_page(arg, 0, use_keywords)

                    if re.search(
                            "^dictionary data not found!", embed_pg.description.lower()) is not None:
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
                            embed_pg, page_limit = dict_page(
                                arg, page, use_keywords)
                            await message.edit(embed=embed_pg)
                        elif str(reaction) == '◀':
                            if page > 0:
                                page -= 1
                                embed_pg, page_limit = dict_page(
                                    arg, page, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '▶':
                            if page < page_limit:
                                page += 1
                                embed_pg, page_limit = dict_page(
                                    arg, page, use_keywords)
                                await message.edit(embed=embed_pg)
                        elif str(reaction) == '⏭':
                            page = page_limit-1
                            embed_pg, page_limit = dict_page(
                                arg,  page, use_keywords)
                            await message.edit(embed=embed_pg)

                        await message.remove_reaction(reaction, user)

                finally:
                    await message.clear_reactions()
        else:
            ctx.command.reset_cooldown(ctx)


def setup(client):
    client.add_cog(DictionarySearch(client))
