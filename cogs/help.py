import discord
from discord.ext.commands import command, Cog


class Help(Cog):
    def __init__(self, client):
        self.client = client

    @command()
    async def help(self, ctx):
        """ Command to show the info about the different bot commands
        """

        # live
        bl_channel = ['809014777531727892', '809016986515537950']
        pos_channel = ['752196383066554538', '752193632383008770']

        # local
        # bl_channel = ['809003182306361386']
        # pos_channel = ['794281211127267330']

        if ctx.message.author == self.client.user:
            return  # None

        if str(ctx.channel.id) in pos_channel:
            await ctx.trigger_typing()
            des = "To find quotes from the POS fanfiction, use the command-\n" + \
                "`qf QUOTE`\nFor eg- `qf Voldemort is back`\n\n" + \
                "To search using keywords, use the command-\n`qfk word1 word2`\n " +\
                "For eg- `qfk sentinel knowledge`\n\nTo use the POS Dictionary, " +\
                "use the command - `qd string`\nFor eg - `qd potter prophecy`" + \
                "\n\nIndex number from the POS Dictionary Index can also be used for " +\
                "dictionary searching.\nFor Eg- `qd 7`" +\
                "\n\nTo look at the POS Dictionary Index, use the command - `qindex`"

            embed1 = discord.Embed(title='Help Menu',
                                   description=des,
                                   colour=discord.Colour(0x272b28))

        if str(ctx.channel.id) in bl_channel:
            await ctx.trigger_typing()
            des = "To find quotes from the BL fanfiction, use the command-\n`qf QUOTE`" + \
                '\n'+"For eg- `qf Arcturus didn't seem`\n\nTo search using keywords, use the " +\
                "command- `qfk word1 word2 word3`\nFor eg- `qfk arcturus seem`"

            embed1 = discord.Embed(title='Help Menu',
                                   description=des,
                                   colour=discord.Colour(0x272b28))

        embed1.set_footer(
            text="The search keywords will be underlined for better readability")
        await ctx.send(embed=embed1)


def setup(client):
    client.add_cog(Help(client))
