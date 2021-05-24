import json

from utils.search import search_string, search_dict
from utils.processing import get_book
from utils.chapter_processing import get_chapter_head_tag


def quote_find(arg1, page_number, book, use_keywords):
    """Search and find the quote and return both the line containing the quote as well as
     the next line, chapter heading of the chapter where the quote was found
     and quote found counter 
     """

    book_pt, book_md = get_book(book)

    # book_lines=list of all the lines of the book and line_number=line number where string is found
    book_lines, line_number1, quote_found_ctr = search_string(
        book_pt, book_md, arg1, book, use_keywords)

    # Subtracting 1 from the line_number list because of mismatch of line number when all the lines were assigned to list book_lines
    line_number2 = [x - 1 for x in line_number1]
    result = []  # list contains the line where the quote was found and the next line

    try:
        if quote_found_ctr == 0:  # if no string found in the file
            return 'err', 'err', quote_found_ctr, len(line_number2)

        for i in range(1):
            result.append(book_lines[line_number2[page_number]].rstrip())
            # line at which the quote was found
            if len(line_number2) > page_number:
                quote_found = line_number2[page_number]
            else:
                quote_found = line_number2[len(line_number2)]
            quote_found_ctr = 1

    except IndexError:
        quote_found_ctr = 2  # if the page number croses the len(line_number2)
        return 'err', 'err', quote_found_ctr, len(line_number2)

    book_tag, chapter_heading = get_chapter_head_tag(
        book, quote_found, book_lines)

    quote_found += 2  # line number of the next line after the line where the quote was found
    next_line = book_lines[quote_found]  # Next line of the quote
    str1 = ""  # final output string

    for i in range(1):
        # Assigning the 1st value of the result list i.e. the line containing the quote
        str1 += result[0]
        str1 += "\n\n"  # Two nextlines to make it more clean
        str1 += next_line  # Concatinating both the line containing the quote and the next line

    # To fix the embed.description: Must be 2048 or fewer in length error
    if len(list(str1)) > 2048:
        description = str1[:2020] + "..."
    else:
        description = str1

    # chapter_heading[0] contains the chapter heading of the chapter where the quote was found
    return chapter_heading[0], description, quote_found_ctr, len(line_number2)


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


def pos_dict(arg, page, book, use_keywords):
    """ Call search_dict() and return title,
    description & quote_found_ctr
    """
    book_md = "data/dictionary/POS Dictionary.json"
    title, description, quote_found_ctr, page_limit = search_dict(
        book_md, arg, page, book, use_keywords)

    # To fix the embed.description: Must be 2048 or fewer in length error
    if len(list(description)) > 2048:
        description = description[:2020] + "..."

    description += '\n\n' + "Page: "+str(page+1)+'/'+str(page_limit)

    return title, description, quote_found_ctr, page_limit
