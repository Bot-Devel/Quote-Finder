import re

from discord import Embed, Colour

import utils.chapter_processing as chapter_processing
from utils.chapter_processing import get_chapter_head_tag
from utils.processing import get_book


class Book:
    def __init__(self, query, book_number, page_number=0, use_keywords=False):
        self.query = query
        self.book = book_number
        self.page_number = page_number
        self.use_keywords = use_keywords

    def book_page(self):
        """ Call quote_find() and process the chapter_title & chapter_url
            and get the embed and page_limit
        """
        self.quote_processing()

        if self.quote_found_ctr == 1:

            self.chapter_title, self.chapter_url = chapter_processing \
                .get_chapter_title_url(
                    self.book, self.chapter_heading)

            self.page_footer = "Page " + \
                str(self.page_number+1)+' of '+str(self.page_limit)

            # underline search phrase
            if self.use_keywords is True:
                for i in self.query.split():

                    match = re.findall(
                        i, self.chapter_description, re.IGNORECASE)

                    for word in match:
                        self.chapter_description = re.sub(
                            fr"\b{word}\b", f"__{word}__",
                            self.chapter_description)

            elif self.use_keywords is False:
                arg1 = r"\b\*{0,}?"
                arg1 += r"\*{0,}? ".join(self.query.split())
                arg1 += r"\*{0,}?\b"

                match = re.findall(
                    arg1.strip(), self.chapter_description, re.IGNORECASE)

                for word in match:
                    self.chapter_description = re.sub(
                        fr"\b{word}\b", f"__{word}__",
                        self.chapter_description)

            # embed.description: Must be 2048 or fewer in length
            if len(list(self.chapter_description)) > 2048:
                self.chapter_description = self.chapter_description[:2020] + "..."
            else:
                pass

        if self.quote_found_ctr == 1:

            self.embed_msg = Embed(title=''.join(self.chapter_title),
                                   url=self.chapter_url,
                                   description=self.chapter_description,
                                   colour=Colour(0x272b28))
            self.embed_msg.set_footer(text=self.page_footer)

        elif self.quote_found_ctr == 0:

            self.embed_msg = Embed(
                description="Quote not found!",
                colour=Colour(0x272b28))

        elif self.quote_found_ctr == 2:

            self.embed_msg = Embed(
                description="No more quotes found!",
                colour=Colour(0x272b28))

    def quote_processing(self):
        """
        Process the quote by calling search_query() and get
        both the line containing the quote as well as the
        next line, chapter heading of the chapter where
        the quote was found and quote found counter
        """

        self.book_md = get_book(self.book)
        self.search_query()

        try:
            if self.quote_found_ctr == 0:  # if no string found in the file
                return

            self.first_line = self.book_lines[
                self.line_number_index[self.page_number]].rstrip()

            # +2 for the next line
            self.next_line = self.book_lines[
                self.line_number_index[self.page_number]+2].rstrip()

            if len(self.line_number_index) > self.page_number:
                self.quote_found = self.line_number_index[self.page_number]

            else:
                self.quote_found = self.line_number_index[len(
                    self.line_number_index)]

            self.quote_found_ctr = 1

            self.book_tag, self.chapter_heading = get_chapter_head_tag(
                self.book, self.quote_found, self.book_lines)

            self.chapter_description = self.first_line+"\n\n" + \
                self.next_line  # final output string
            self.page_limit = len(self.line_number_index)

            # chapter_heading[0] contains the chapter heading of the
            # chapter where the quote was found
            self.chapter_heading = self.chapter_heading[0]

        except IndexError:
            # if the page number crosses the len(line_number_index)
            self.quote_found_ctr = 2
            self.quote_found = None
            self.page_limit = 1

    def search_query(self):
        """Search the query string in the file and get all the lines of the
        book as a list and list of all the line numbers containing the string
        """

        line_number = 0
        self.book_lines = []  # contains all the lines of the book as a list
        self.line_number_index1 = []  # list of all the line numbers containing the string
        string_to_process = self.query.replace(
            '"', r'\"')  # replacing with escape character
        string_to_process = string_to_process.replace('?', r'\?')

        if self.use_keywords is True:
            strings = string_to_process.split()
            self.match_pattern = r"^"
            for string in strings:
                self.match_pattern += r"(?=.*\b"+string+r"\b)"
            self.match_pattern += r".*$"

        elif self.use_keywords is False:
            self.get_match_pattern()

        with open(self.book_md, 'r') as read_obj1:
            for line in read_obj1:

                line_number += 1

                # removing markdown
                line_sub1 = re.sub(r'\*', '', line, flags=re.M)
                line_sub2 = re.sub(r'\\', '', line_sub1, flags=re.M)

                # For each line, check if line contains the string
                if re.search(self.match_pattern, line_sub2, re.IGNORECASE):
                    # if string found, append the line number
                    self.line_number_index1.append(line_number)

                self.book_lines.append(line)

        # if string was found, index list wont be empty
        if len(self.line_number_index1) == 0:
            self.quote_found_ctr = 0
        else:
            self.quote_found_ctr = 1

        # Subtracting 1 because of mismatch of line number
        # during line appending to book_lines list
        self.line_number_index = [x - 1 for x in self.line_number_index1]

    def get_match_pattern(self):
        """
        Process the query string and get the regex match pattern
        """
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
