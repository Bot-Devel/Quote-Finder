from utils.string_processing import get_raw_string
import re
import json


def search_string(book1, book2, string_to_search):
    """Search for the given string in the file and return all the lines of the
    book as a list and list of all the line numbers containing the string"""
    line_number = 0
    mylines = []  # contains all the lines of the book as a list
    index = []  # list of all the line numbers containing the string
    string_to_process = string_to_search.replace(
        '"', r'\"')  # replacing with escape character
    string_to_process = string_to_process.replace('?', r'\?')
    string_to_process = list(string_to_process)
    raw_string = get_raw_string(string_to_process)
    # Open the file in read only mode
    with open(book1, 'r') as read_obj1:
        for line in read_obj1:
            # For each line, check if line contains the string
            line_number += 1
            if re.search(raw_string, line.lower()) is not None:
                # if string found, append the line number
                index.append(line_number)
    if len(index) == 0:  # if string was found, index list wont be empty
        quote_found_ctr = 0  # quote found counter to know if the quote was found during the query
    else:
        quote_found_ctr = 1
    with open(book2, 'r') as read_obj1:
        # Read all lines in the file one by one
        for line in read_obj1:
            # Append each line of the book to the mylines list
            line_number += 1
            mylines.append(line)
    return mylines, index, quote_found_ctr


def search_dict(book1, string_to_search):
    """Search for the given string in the json file and return the title and description"""
    string_to_process = string_to_search.replace(
        '"', r'\"')  # replacing with escape character
    string_to_process = string_to_process.replace('?', r'\?')
    string_to_process = list(string_to_process)
    raw_string = get_raw_string(string_to_process)
    quote_found_ctr = 0
    with open(book1, 'r') as read_obj1:
        data = json.load(read_obj1)
        for i in data['dictionary']:
            if re.search(raw_string, i['title'].lower()) is not None:
                title = i['title']
                description = i['description']
                quote_found_ctr = 1
    if quote_found_ctr == 0:
        title = ''
        description = 'Quote not found!'
    return title, description, quote_found_ctr
