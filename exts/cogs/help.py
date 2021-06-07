import discord
from discord.ext.commands import command, Cog
from exts import config

pos_channel_cooldown = [x.strip() for x in (config.get(
    'cooldown channels', 'pos_channel')).split(",")]

pos_channel_whitelist = [x.strip() for x in (config.get(
    'whitelist channels', 'pos_channel')).split(",")]


class Help(Cog):
    def __init__(self, client):
        self.client = client

    @command()
    async def help(self, ctx):
        """ Command to show the info about the different bot commands
        """

        if ctx.message.author == self.client.user:
            return  # None

        await ctx.trigger_typing()
        embed = discord.Embed(title='Help Menu',
                              #   description="",
                              colour=discord.Colour(0x272b28))

        embed.add_field(
            name="Quote navigation",
            value="`⏮ ◀ ▶ ⏭`" +
            "\nOften there are more than one search result so the page turning reactions, that are only visable to the requester for 30 seconds after, can be used to scroll through the results.",
            inline=False
        )

        embed.add_field(
            name="Book Search:",
            value="`qf [quote]`\n__Example:__\n`qf harry potter`\nTo use **keywords** to search the quote, use `qfk [QUOTE]`\n__Example:__\n`qfk harry slytherin`",
            inline=False
        )

        if str(ctx.channel.id) in \
                pos_channel_cooldown+pos_channel_whitelist:

            embed.add_field(
                name="Dictionary Search:",
                value="`qd [dictionary term]` or `qd [index number]`\
                \n __Example:__\n1)`qd potter prophecy`\n2)`qd 26`\nTo use **keywords** to search the dictionary, use `qdk [TERM]`\n__Example:__\n`qdk Warning Chimes`",
                inline=False
            )

            embed.add_field(
                name="Dictionary Index:",
                value="To view the all the dictionary terms available for search:\n`qindex`",
                inline=False
            )

        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Help(client))
