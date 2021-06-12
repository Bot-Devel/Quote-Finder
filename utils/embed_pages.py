import discord
import re

import utils.chapter_processing as chapter_processing
from utils.finder import dict_index, quote_find, pos_dict


def index_page(page=0):
    """ Call get_dict_index() & divide_chunks() and return
    the embed & limit
    """

    des = dict_index()
    # Divide the index list into chunks so that there are 10 in each page
    res = list(divide_chunks(des, 10))
    limit = len(res)

    if page < limit:
        embed_msg = discord.Embed(title='POS Dictionary Index',
                                  url="https://docs.google.com/spreadsheets/d/1k-GXwnmJGLtp_IUNCkPI-B4IT5u-qDBEEH7KwJPLBuA/edit?usp=sharing",
                                  description='\n'.join(res[page]),
                                  colour=discord.Colour(0x272b28))
    else:
        embed_msg = discord.Embed(
            description="No more index data!",
            colour=discord.Colour(0x272b28))
    return embed_msg, limit


def dict_page(arg, page, use_keywords):
    title, description, quote_found_ctr, page_limit = pos_dict(
        arg, page, use_keywords)

    if quote_found_ctr == 1:
        chapter_url = "https://docs.google.com/spreadsheets/d/1k-GXwnmJGLtp_IUNCkPI-B4IT5u-qDBEEH7KwJPLBuA/edit?usp=sharing"

    elif quote_found_ctr == 0:
        title = ""
        chapter_url = ""
        description = "Dictionary data not found!"

    elif quote_found_ctr == 2:
        title = ""
        chapter_url = ""
        description = "No more dictionary data found!"

    embed_msg = discord.Embed(title=''.join(title),
                              url=chapter_url,
                              description=description,
                              colour=discord.Colour(0x272b28))

    return embed_msg, page_limit


def divide_chunks(list1, n):
    """ Divide the index list into 'n' equal chunks
    """
    for i in range(0, len(list1), n):
        yield list1[i:i + n]
