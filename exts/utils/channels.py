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


def check_channel(channel_id, reset_flag):

    if str(channel_id) in pos_channel_cooldown+pos_channel_whitelist:

        book = 1
        channel = pos_channel_cooldown+pos_channel_whitelist

    elif str(channel_id) in bl_channel_cooldown+bl_channel_whitelist:

        book = 2
        channel = bl_channel_cooldown+bl_channel_whitelist
        
    elif str(channel_id) in aoc_channel_cooldown+aoc_channel_whitelist:

        book = 3
        channel = aoc_channel_cooldown+aoc_channel_whitelist

    else:
        reset_flag = True

    # reset cooldown if whitelist channel
    if str(channel_id) in pos_channel_whitelist+bl_channel_whitelist+aoc_channel_whitelist:
        reset_flag = True

    return book, channel, reset_flag
