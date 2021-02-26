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
            des = "To find quotes from the POS fanfiction, use the command- `qf QUOTE`"+'\n'+"For eg- `qf Voldemort is back`"+'\n\n' + \
                "To use the POS Dictionary, use the command- `qd string`"+'\n'+"For eg- `qd potter prophecy`"+'\n\n' + \
                "To look at the POS Dictionary Index, use the command- `qindex`"

            embed1 = discord.Embed(title='Help Menu',
                                   description=des,
                                   colour=discord.Colour(0x272b28))

        if str(ctx.channel.id) in bl_channel:
            des = "To find quotes from the BL fanfiction, use the command- `qf QUOTE`" + \
                '\n'+"For eg- `qf Arcturus didn't seem`"

            embed1 = discord.Embed(title='Help Menu',
                                   description=des,
                                   colour=discord.Colour(0x272b28))

        await ctx.send(embed=embed1)


def setup(client):
    client.add_cog(Help(client))
