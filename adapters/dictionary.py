import re

from discord import Embed, Colour

from utils.processing import get_dictionary_data, divide_chunks


class Dictionary:
    def __init__(self,  page_number=0, use_keywords=False):
        self.page_number = page_number
        self.use_keywords = use_keywords

    def dictionary_page(self, query):

        self.data = get_dictionary_data()
        self.search_dictionary(query)

        # # embed.description: Must be 2048 or fewer in length
        if len(list(self.description)) > 2048:
            self.description = self.description[:2020] + "..."

        self.description += f"\n\nPage {str(self.page_number+1)} of {str(self.page_limit)}"

        if self.term_found_ctr == 1:
            self.chapter_url = "https://docs.google.com/spreadsheets/d/1k-GXwnmJGLtp_IUNCkPI-B4IT5u-qDBEEH7KwJPLBuA/edit?usp=sharing"

            self.embed_msg = Embed(title=''.join(self.title),
                                   url=self.chapter_url,
                                   description=self.description,
                                   colour=Colour(0x272b28))

        elif self.term_found_ctr == 0:

            self.embed_msg = Embed(
                description="Dictionary term not found!",
                colour=Colour(0x272b28))

        elif self.term_found_ctr == 2:

            self.embed_msg = Embed(
                description="No more dictionary data found!",
                colour=Colour(0x272b28))

    def dictionary_index_page(self):
        """ Call get_dict_index() & divide_chunks() and return
        the embed & page_limit
        """

        self.term_found_ctr = False
        self.get_dictionary_index()
        # Divide the index list into chunks so that there are 10 in each page
        self.dict_chunk = list(divide_chunks(self.dict_index, 10))
        self.page_limit = len(self.dict_chunk)

        if self.page_number < self.page_limit:
            try:
                self.term_found_ctr = True
                self.description = '\n'.join(
                    self.dict_chunk[self.page_number])
                self.description += f"\n\nPage {str(self.page_number+1)} of {str(self.page_limit)}"

                self.embed_msg = Embed(title='POS Dictionary Index',
                                       url="https://docs.google.com/spreadsheets/d/1k-GXwnmJGLtp_IUNCkPI-B4IT5u-qDBEEH7KwJPLBuA/edit?usp=sharing",
                                       description=self.description,
                                       colour=Colour(0x272b28))

            except IndexError:
                # if the page number crosses the len(page_limit)
                self.term_found_ctr = False

        if self.term_found_ctr is False:
            self.embed_msg = Embed(
                description="No more index data!",
                colour=Colour(0x272b28))

    def get_dictionary_index(self):
        """ Read the json file and append the title values to the index
        and return index
        """

        self.data = get_dictionary_data()
        self.dict_index = []

        for i in self.data['dictionary']:
            self.dict_index.append(i['title'])

    def search_dictionary(self, query):
        """Search for the given string in the json
           file and return the title and description
        """

        string_to_process = query.replace(
            '"', r'\"')  # replacing with escape character
        string_to_process = string_to_process.replace('?', r'\?')

        if self.use_keywords is True:
            strings = string_to_process.split()
            self.match_pattern = r"^"
            for string in strings:
                self.match_pattern += r"(?=.*\b"+string+r"\b)"
            self.match_pattern += r".*$"

        elif self.use_keywords is False:
            self.get_match_pattern(query)

        self.term_found_ctr = 0
        self.title = []
        self.description = []

        for i in self.data['dictionary']:

            if re.search(self.match_pattern, i['title'], re.IGNORECASE):
                self.title.append(i['title'])
                self.description.append(i['description'])
                self.term_found_ctr = 1

        self.page_limit = len(self.title)

        if self.term_found_ctr == 1:
            try:
                self.title = self.title[self.page_number]
                self.description = self.description[self.page_number]

            except IndexError:
                self.term_found_ctr = 2
                self.quote_found = None
                self.page_limit = 1
                return

        if self.term_found_ctr == 0:
            self.title.append('')
            self.description.append('Dictionary term not found!')

    def get_match_pattern(self, query):
        """Process the given string and return the regex as a raw string"""
        string_processing = []

        string_processing = [r'\b']
        string_processing.append(query.lower())
        # Using \b to exclude . after a word
        string_processing.append(r"\b")
        self.match_pattern = ''.join(map(str, string_processing))
