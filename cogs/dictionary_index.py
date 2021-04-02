from discord.ext.commands import command, Cog

from utils.embed_pages import index_page


class DictionaryIndex(Cog):
    def __init__(self, client):
        self.client = client

    @command(name='index', pass_context=True)
    async def show_dict_index(self, ctx):
        """ Command to show the dictionary index by parsing the dictionary excel sheet
        """
        if ctx.message.author == self.client.user:
            return  # None

        # live
        pos_channel = ['752196383066554538', '752193632383008770']

        # local
        # pos_channel = ['794281211127267330']

        if str(ctx.channel.id) in pos_channel:
            try:
                await ctx.trigger_typing()
                # 0 parameter is used in index_page(0) to ensure that the 1st page is sent first
                embed_pg, page_limit = index_page(0)
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

                    await message.remove_reaction(reaction, user)

            finally:
                await message.clear_reactions()


def setup(client):
    client.add_cog(DictionaryIndex(client))
