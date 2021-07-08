from exts import config

pos_channel_cooldown = [x.strip() for x in (config.get(
    'cooldown channels', 'pos_channel')).split(",")]

bl_channel_cooldown = [x.strip() for x in (config.get(
    'cooldown channels', 'bl_channel')).split(",")]

aoc_channel_cooldown = [x.strip() for x in (config.get(
    'cooldown channels', 'aoc_channel')).split(",")]

pos_channel_whitelist = [x.strip() for x in (config.get(
    'whitelist channels', 'pos_channel')).split(",")]

bl_channel_whitelist = [x.strip() for x in (config.get(
    'whitelist channels', 'bl_channel')).split(",")]

aoc_channel_whitelist = [x.strip() for x in (config.get(
    'whitelist channels', 'aoc_channel')).split(",")]

podk_channel_whitelist = [x.strip() for x in (config.get(
    'whitelist channels', 'podk_channel')).split(",")]


def check_channel(ctx):

    if str(ctx.channel.id) in pos_channel_cooldown+pos_channel_whitelist:
        book = 1
        channel = pos_channel_cooldown+pos_channel_whitelist

    elif str(ctx.channel.id) in bl_channel_cooldown+bl_channel_whitelist:
        book = 2
        channel = bl_channel_cooldown+bl_channel_whitelist

    elif str(ctx.channel.id) in aoc_channel_cooldown+aoc_channel_whitelist:
        book = 3
        channel = aoc_channel_cooldown+aoc_channel_whitelist

    elif str(ctx.channel.id) in podk_channel_whitelist:
        book = 4
        channel = podk_channel_whitelist

    else:
        book = None
        channel = None
        ctx.command.reset_cooldown(ctx)

    # reset cooldown if whitelist channel
    if str(ctx.channel.id) in pos_channel_whitelist + \
            bl_channel_whitelist + aoc_channel_whitelist +\
            podk_channel_whitelist:

        ctx.command.reset_cooldown(ctx)

    return book, channel
