from utils.processing import get_raw_string
import re
import json


def search_dict(data, string_to_search, page, use_keywords):
    """Search for the given string in the json file and return the title and description"""

    string_to_process = string_to_search.replace(
        '"', r'\"')  # replacing with escape character
    string_to_process = string_to_process.replace('?', r'\?')

    if use_keywords is True:
        strings = string_to_process.split()
        raw_string = r"^"
        for string in strings:
            raw_string += r"(?=.*\b"+string+r"\b)"
        raw_string += r".*$"

    elif use_keywords is False:
        type_of_search = 2  # searching for pos dictionary search
        raw_string = get_raw_string(type_of_search, string_to_process)

    quote_found_ctr = 0
    title = []
    description = []

    for i in data['dictionary']:

        if re.search(raw_string, i['title'], re.IGNORECASE):
            title.append(i['title'])
            description.append(i['description'])
            quote_found_ctr = 1

    page_limit = len(title)
    if quote_found_ctr == 1:
        try:
            return title[page], description[page], quote_found_ctr, page_limit
        except IndexError:
            quote_found_ctr = 2
            title.append('')
            description.append('No more dictionary data found!')
            return title, description, quote_found_ctr, page_limit

    if quote_found_ctr == 0:
        title.append('')
        description.append('Quote not found!')
        return title, description, quote_found_ctr, page_limit
