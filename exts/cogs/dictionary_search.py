import re
from discord.ext.commands import command, Cog, cooldown
from discord.ext.commands.cooldowns import BucketType

from adapters.dictionary import Dictionary
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
        """ Command to search and find the dictionary term """
        use_keywords = False
        if ctx.message.author == self.client.user:
            return

        if str(ctx.channel.id) in pos_channel_whitelist:
            ctx.command.reset_cooldown(ctx)

        if str(ctx.channel.id) in pos_channel_cooldown+pos_channel_whitelist:
            try:
                await ctx.trigger_typing()
                dictionary = Dictionary(0, use_keywords)
                dictionary.dictionary_page(arg)

                if re.search(
                        "^dictionary term not found!",
                        dictionary.embed_msg.description.lower()):

                    ctx.command.reset_cooldown(ctx)

                try:
                    message = await ctx.message.reply(
                        embed=dictionary.embed_msg, mention_author=False)

                except Exception:
                    message = await ctx.message.channel.send(
                        embed=dictionary.embed_msg)

                await message.add_reaction('⏮')
                await message.add_reaction('◀')
                await message.add_reaction('▶')
                await message.add_reaction('⏭')

                def check(reaction, user):
                    return user.id == ctx.author.id

                page = 0
                reaction = None
                while True:
                    reaction, user = await self.client.wait_for(
                        'reaction_add', timeout=30.0, check=check)

                    if str(reaction) == '⏮':
                        page = 0
                        dictionary = Dictionary(page, use_keywords)
                        dictionary.dictionary_page(arg)
                        await message.edit(embed=dictionary.embed_msg)

                    elif str(reaction) == '◀':
                        if page > 0:
                            page -= 1
                            dictionary = Dictionary(page, use_keywords)
                            dictionary.dictionary_page(arg)
                            await message.edit(embed=dictionary.embed_msg)

                    elif str(reaction) == '▶':
                        if page < dictionary.page_limit:
                            page += 1
                            dictionary = Dictionary(page, use_keywords)
                            dictionary.dictionary_page(arg)
                            await message.edit(embed=dictionary.embed_msg)

                    elif str(reaction) == '⏭':
                        page = dictionary.page_limit-1
                        dictionary = Dictionary(page, use_keywords)
                        dictionary.dictionary_page(arg)
                        await message.edit(embed=dictionary.embed_msg)

                    await message.remove_reaction(reaction, user)

            finally:
                try:
                    await message.clear_reactions()
                except UnboundLocalError:
                    pass
        else:
            ctx.command.reset_cooldown(ctx)

    @cooldown(1, 15, BucketType.user)
    @command(name='dk', pass_context=True)
    async def search_dictionary_keys(self, ctx, *, arg):
        """ Command to search and find the dictionary term using keywords """
        use_keywords = True
        if ctx.message.author == self.client.user:
            return

        if str(ctx.channel.id) in pos_channel_cooldown+pos_channel_whitelist:
            try:
                await ctx.trigger_typing()
                dictionary = Dictionary(0, use_keywords)
                dictionary.dictionary_page(arg)

                if re.search(
                        "^dictionary term not found!",
                        dictionary.embed_msg.description.lower()):

                    ctx.command.reset_cooldown(ctx)

                try:
                    message = await ctx.message.reply(
                        embed=dictionary.embed_msg, mention_author=False)

                except Exception:
                    message = await ctx.message.channel.send(
                        embed=dictionary.embed_msg)

                await message.add_reaction('⏮')
                await message.add_reaction('◀')
                await message.add_reaction('▶')
                await message.add_reaction('⏭')

                def check(reaction, user):
                    return user.id == ctx.author.id

                page = 0
                reaction = None
                while True:
                    reaction, user = await self.client.wait_for(
                        'reaction_add', timeout=30.0, check=check)

                    if str(reaction) == '⏮':
                        page = 0
                        dictionary = Dictionary(page, use_keywords)
                        dictionary.dictionary_page(arg)
                        await message.edit(embed=dictionary.embed_msg)

                    elif str(reaction) == '◀':
                        if page > 0:
                            page -= 1
                            dictionary = Dictionary(page, use_keywords)
                            dictionary.dictionary_page(arg)
                            await message.edit(embed=dictionary.embed_msg)

                    elif str(reaction) == '▶':
                        if page < dictionary.page_limit:
                            page += 1
                            dictionary = Dictionary(page, use_keywords)
                            dictionary.dictionary_page(arg)
                            await message.edit(embed=dictionary.embed_msg)

                    elif str(reaction) == '⏭':
                        page = dictionary.page_limit-1
                        dictionary = Dictionary(page, use_keywords)
                        dictionary.dictionary_page(arg)
                        await message.edit(embed=dictionary.embed_msg)

                    await message.remove_reaction(reaction, user)

            finally:
                try:
                    await message.clear_reactions()
                except UnboundLocalError:
                    pass
        else:
            ctx.command.reset_cooldown(ctx)


def setup(client):
    client.add_cog(DictionarySearch(client))
