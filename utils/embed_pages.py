import discord
import re

import utils.chapter_processing as chapter_processing
from utils.finder import get_dict_index, quote_find, pos_dict


def book_page(arg, book, page, use_keywords):
    """ Call quote_find() and process the chapter_title & chapter_url
        and return the embed and page_limit
    """

    chapter_heading, chapter_desription, quote_found_ctr, page_limit = quote_find(
        arg, page, book, use_keywords)

    if quote_found_ctr == 1:

        chapter_title, chapter_url = chapter_processing.get_chapter_title_url(
            book, chapter_heading)

    page_footer = "Page "+str(page+1)+' of '+str(page_limit)

    # underline search keywords
    for i in arg.split():

        # to ignore characters like I,., etc due to the volume.
        # TODO: Fix the re.sub issue to discard this workaround
        if len(i) > 1:

            match = re.findall(fr"\b{i}\b", chapter_desription, re.IGNORECASE)
            for word in match:

                # FIXME: Ignore * during re.sub to underline the whole phrase,
                #  rather than each word
                chapter_desription = re.sub(
                    fr"\b{word}\b", f"__{word}__", chapter_desription, re.IGNORECASE)

    # To fix the embed.description: Must be 2048 or fewer in length error
    if len(list(chapter_desription)) > 2048:
        chapter_desription = chapter_desription[:2020] + "..."
    else:
        pass

    if quote_found_ctr == 1:
        embed1 = discord.Embed(title=''.join(chapter_title),
                               url=chapter_url,
                               description=chapter_desription,
                               colour=discord.Colour(0x272b28))
        embed1.set_footer(text=page_footer)

    elif quote_found_ctr == 0:
        embed1 = discord.Embed(
            description="Quote not found!",
            colour=discord.Colour(0x272b28))

    elif quote_found_ctr == 2:
        embed1 = discord.Embed(
            description="No more quotes found!",
            colour=discord.Colour(0x272b28))

    return embed1, page_limit


def index_page(page=0):
    """ Call get_dict_index() & divide_chunks() and return
    the embed & limit
    """

    des = get_dict_index()
    # Divide the index list into chunks so that there are 10 in each page
    res = list(divide_chunks(des, 10))
    limit = len(res)

    if page < limit:
        embed1 = discord.Embed(title='POS Dictionary Index',
                               url="https://docs.google.com/spreadsheets/d/1k-GXwnmJGLtp_IUNCkPI-B4IT5u-qDBEEH7KwJPLBuA/edit?usp=sharing",
                               description='\n'.join(res[page]),
                               colour=discord.Colour(0x272b28))
    else:
        embed1 = discord.Embed(
            description="No more index data!",
            colour=discord.Colour(0x272b28))
    return embed1, limit


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

    embed1 = discord.Embed(title=''.join(title),
                           url=chapter_url,
                           description=description,
                           colour=discord.Colour(0x272b28))

    return embed1, page_limit


def divide_chunks(list1, n):
    """ Divide the index list into 'n' equal chunks
    """
    for i in range(0, len(list1), n):
        yield list1[i:i + n]
