import json

from utils.search import search_string, search_dict
from utils.processing import get_book
from utils.chapter_processing import get_chapter_head_tag


def quote_find(arg1, page_number, book, use_keywords):
    """Search and find the quote and return both the line containing the quote as well as
     the next line, chapter heading of the chapter where the quote was found
     and quote found counter
     """

    book_md = get_book(book)

    # book_lines: list of all the lines of the book
    # line_number_list1: list of line number where string is found
    book_lines, line_number_index1, quote_found_ctr = search_string(
        book_md, arg1, book, use_keywords)

    # Subtracting 1 from the line_number list because of mismatch of
    # line number when all the lines were assigned to list book_lines
    line_number_index = [x - 1 for x in line_number_index1]

    try:
        if quote_found_ctr == 0:  # if no string found in the file
            return 'err', 'err', quote_found_ctr, len(line_number_index)

        first_line = book_lines[line_number_index[page_number]].rstrip()
        next_line = book_lines[line_number_index[page_number]+2].rstrip()

        if len(line_number_index) > page_number:
            quote_found = line_number_index[page_number]
        else:
            quote_found = line_number_index[len(line_number_index)]
        quote_found_ctr = 1

    except IndexError:
        # if the page number crosses the len(line_number_index)
        quote_found_ctr = 2
        return 'err', 'err', quote_found_ctr, len(line_number_index)

    book_tag, chapter_heading = get_chapter_head_tag(
        book, quote_found, book_lines)

    des = first_line+"\n\n" + next_line  # final output string

    # chapter_heading[0] contains the chapter heading of the chapter where the quote was found
    return chapter_heading[0], des, quote_found_ctr, len(line_number_index)


def get_dict_index():
    """ Read the json file and append the title values to the index
    and return index
    """
    file = "data/dictionary/POS Dictionary.json"
    index = []
    with open(file, 'r') as read_obj1:
        data = json.load(read_obj1)
        for i in data['dictionary']:
            index.append(i['title'])

    return index


def pos_dict(arg, page, use_keywords):
    """ Call search_dict() and return title,
    description & quote_found_ctr
    """
    pos_json = "data/dictionary/POS Dictionary.json"
    title, description, quote_found_ctr, page_limit = search_dict(
        pos_json, arg, page, use_keywords)

    # To fix the embed.description: Must be 2048 or fewer in length error
    if len(list(description)) > 2048:
        description = description[:2020] + "..."

    description += '\n\n' + "Page: "+str(page+1)+'/'+str(page_limit)

    return title, description, quote_found_ctr, page_limit
