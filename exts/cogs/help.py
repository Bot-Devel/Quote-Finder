import discord
from discord.ext.commands import command, Cog


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
                              description="To use **keyword searching**, add a `k` at the end of `qf` or `qd` command.\n__Example:__\n1)`qfk The Sentinel hissed`\n2)`qdk potter prophecy`",
                              colour=discord.Colour(0x272b28))

        embed.add_field(
            name="Book Search:",
            value="`qf [quote]` \
            \n __Example:__\n`qf no regrets`",
            inline=False
        )

        embed.add_field(
            name="Dictionary Search (PoS only):",
            value="`qd [dictionary term]` or `qd [index number]`\
            \n __Example:__\n1)`qd potter prophecy`\n2)`qd 26`",
            inline=False
        )

        embed.add_field(
            name="Dictionary Index (PoS only):",
            value="`qindex`",
            inline=False
        )

        embed.set_footer(
            text="The search keywords will be underlined for better readability.")
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Help(client))
