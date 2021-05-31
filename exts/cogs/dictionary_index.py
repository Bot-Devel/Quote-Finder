from discord.ext.commands import command, Cog

from utils.embed_pages import index_page
from exts import config

pos_channel_cooldown = [x.strip() for x in (config.get(
    'cooldown channels', 'pos_channel')).split(",")]

pos_channel_whitelist = [x.strip() for x in (config.get(
    'whitelist channels', 'pos_channel')).split(",")]


class DictionaryIndex(Cog):
    def __init__(self, client):
        self.client = client

    @command(name='index', pass_context=True)
    async def show_dict_index(self, ctx):
        """ Command to show the dictionary index by parsing the dictionary excel sheet
        """
        if ctx.message.author == self.client.user:
            return  # None

        if str(ctx.channel.id) in pos_channel_cooldown+pos_channel_whitelist:
            try:
                await ctx.trigger_typing()
                embed_pg, page_limit = index_page(0)

                try:
                    message = await ctx.message.reply(
                        embed=embed_pg, mention_author=False)

                except Exception:
                    message = await ctx.message.channel.send(
                        embed=embed_pg)

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
                        embed_pg, page_limit = index_page(page)
                        await message.edit(embed=embed_pg)
                    elif str(reaction) == '◀':
                        if page > 0:
                            page -= 1
                            embed_pg, page_limit = index_page(page)
                            await message.edit(embed=embed_pg)
                    elif str(reaction) == '▶':
                        if page < page_limit:
                            page += 1
                            embed_pg, page_limit = index_page(page)
                            await message.edit(embed=embed_pg)
                    elif str(reaction) == '⏭':
                        page = page_limit-1
                        embed_pg, page_limit = index_page(page)
                        await message.edit(embed=embed_pg)

                    await message.remove_reaction(reaction, user)

            finally:
                await message.clear_reactions()


def setup(client):
    client.add_cog(DictionaryIndex(client))
