import re

from discord import Embed, Colour

import utils.chapter_processing as chapter_processing
from utils.processing import get_book


class Book:
    def __init__(self, query, page_number, book, use_keywords):
        self.query = query
        self.book = book
        self.page_number = page_number
        self.use_keywords = use_keywords

    def book_page(self):
        """ Call quote_find() and process the chapter_title & chapter_url
            and return the embed and page_limit
        """
        self.chapter_heading, self.chapter_description, quote_found_ctr, self.page_limit = quote_find(
            self.query, self.page, self.book, self.use_keywords)

        if quote_found_ctr == 1:

            self.chapter_title, self.chapter_url = chapter_processing \
                .get_chapter_title_url(
                    self.book, self.chapter_heading)

        self.page_footer = "Page "+str(self.page+1)+' of '+str(self.page_limit)

        # underline search phrase
        if self.use_keywords is True:
            for i in self.query.split():

                match = re.findall(i, self.chapter_description, re.IGNORECASE)

                for word in match:
                    self.chapter_description = re.sub(
                        fr"\b{word}\b", f"__{word}__", self.chapter_description)

        elif self.use_keywords is False:
            arg1 = r"\b\*{0,}?"
            arg1 += r"\*{0,}? ".join(self.query.split())
            arg1 += r"\*{0,}?\b"

            match = re.findall(
                arg1.strip(), self.chapter_description, re.IGNORECASE)

            for word in match:
                self.chapter_description = re.sub(
                    fr"\b{word}\b", f"__{word}__", self.chapter_description)

        # To fix the embed.description: Must be 2048 or fewer in length error
        if len(list(self.chapter_description)) > 2048:
            self.chapter_description = self.chapter_description[:2020] + "..."
        else:
            pass

        if quote_found_ctr == 1:
            self.embed_msg = Embed(title=''.join(self.chapter_title),
                                   url=self.chapter_url,
                                   description=self.chapter_description,
                                   colour=Colour(0x272b28))
            self.embed_msg.set_footer(text=self.page_footer)

        elif quote_found_ctr == 0:
            self.embed_msg = Embed(
                description="Quote not found!",
                colour=Colour(0x272b28))

        elif quote_found_ctr == 2:
            self.embed_msg = Embed(
                description="No more quotes found!",
                colour=Colour(0x272b28))

    def quote_find(self):
        """Search and find the quote and return both the line containing the quote as well as
        the next line, chapter heading of the chapter where the quote was found
        and quote found counter
        """

        self.book_md = get_book(self.book)

        # book_lines: list of all the lines of the book
        # line_number_list1: list of line number where string is found
        book_lines, line_number_index1, quote_found_ctr = search_string(
            book_md, arg1, book, self.use_keywords)

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

    def search_string(self,):
        """Search for the given string in the file and return all the lines of the
        book as a list and list of all the line numbers containing the string"""

        line_number = 0
        book_lines = []  # contains all the lines of the book as a list
        line_number_index1 = []  # list of all the line numbers containing the string
        string_to_process = self.query.replace(
            '"', r'\"')  # replacing with escape character
        string_to_process = string_to_process.replace('?', r'\?')

        if self.use_keywords is True:
            strings = string_to_process.split()
            raw_string = r"^"
            for string in strings:
                raw_string += r"(?=.*\b"+string+r"\b)"
            raw_string += r".*$"

        elif self.use_keywords is False:
            type_of_search = 1  # searching for quotes
            get_match_pattern()

        with open(self.book_md, 'r') as read_obj1:
            for line in read_obj1:

                line_number += 1
                # remove markdown
                line1 = re.sub(r'\*', '', line, flags=re.M)
                line2 = re.sub(r'\\', '', line1, flags=re.M)

                # For each line, check if line contains the string
                if re.search(raw_string, line2, re.IGNORECASE) is not None:
                    # if string found, append the line number
                    line_number_index1.append(line_number)

                book_lines.append(line)

        if len(line_number_index1) == 0:  # if string was found, index list wont be empty
            # quote found counter to know if the quote was found during the query
            self.quote_found_ctr = 0
        else:
            self.quote_found_ctr = 1

    def get_match_pattern(self):
        """Process the given string and return the regex as a raw string"""
        string_processing = []
        self.match_pattern = f"\b{self.query[0]}\W"

        if self.query[1] == "\"":
            # string[1] because 1st two elements are \ & " respectively
            string_processing = [r'^[\"]+']

            # pop the 1st two elements out since they are \ & " respectively
            self.query = self.query[2:]
            string_processing.append(self.query.lower())

            self.match_pattern = ''.join(map(str, string_processing))

        elif self.query[0] == "\'":
            # string[0] because 1st element is '

            string_processing = [r'^[\']+']

            # pop the 1st elements out since its '
            self.query = self.query[1:]
            string_processing.append(self.query.lower())

            self.match_pattern = ''.join(map(str, string_processing))

        else:

            string_processing = [r'\b']
            string_processing.append(self.query.lower())
            string_processing.append(r"\W")
            self.match_pattern = ''.join(map(str, string_processing))
