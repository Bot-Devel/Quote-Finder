
def chapter_processing(chap1):
    """Process the chapter heading and return chapter title and chapter url """

    # list containing the chapter header i.e 139. HB&TRG 1: In Which Plans Are Made
    chapter_heading_list = list(chap1)
    chapter_number = []

    for i in range(0, len(chapter_heading_list)):
        if '&' == chapter_heading_list[i]:
            loc_of_and = i  # location of "&" in the chapter heading list
            loc_of_and += 4  # incrementing 4 will put the index at the chapter number of the chapter i.e. "1" in  139. HB&TRG 1: In Which Plans Are Made
            break  # Sometimes there are two or more &s, without break, the index is overwritten

    chapter_template = ['C', 'h', 'a', 'p', 't', 'e', 'r', ' ']
    book_name = []  # Contains the global chapter number and the book name i.e. 134. HP&DEM |
    chapter_title = []  # complete chapter title of the chapter where the quote was found i.e 134. HP&DEM | Chapter 50: The King of Rats

    for i in range(loc_of_and, len(chapter_heading_list)):
        # Appending the chapter number and name i.e. Chapter 50: The King of Rats
        chapter_template.append(chapter_heading_list[i])

    for i in range(0, loc_of_and):
        # Appending the global chapter number and book name i.e 134. HP&DEM
        book_name.append(chapter_heading_list[i])

    book_name.append(" | ")
    # concatenating the book name and chapter name lists
    chapter_title = book_name+chapter_template

    for i in range(0, len(chapter_heading_list)):
        if '.' == chapter_heading_list[i]:
            loc_of_dot = i  # location of . in the chapter heading

    for i in range(0, loc_of_dot):
        chapter_number.append(chapter_heading_list[i])

    # converting the list to string
    chapter_number = ''.join(chapter_number)
    # removed non-numeric characters like *
    chapter_number = filter(str.isdigit, chapter_number)
    # converting the filter object to string
    chapter_number = ''.join(chapter_number)

    url = "\nhttps://www.fanfiction.net/s/11191235/" + \
        chapter_number
    return chapter_title, url


def get_raw_string(type_of_search, string_to_search):
    """Process the given string and return the regex as a raw string"""

    string_processing = []
    first_word = []
    rest_of_the_word = []

    for i in range(0, len(string_to_search)):
        if " " in string_to_search[i]:
            # locate the whitespace in the list containing the string
            loc_of_space = i
            break
        else:
            loc_of_space = None

    if loc_of_space is not None:  # if whitespace is there, that means there are more than two words. Seperate the string into two parts
        for i in range(0, loc_of_space):
            first_word.append(string_to_search[i])
        for i in range(loc_of_space, len(string_to_search)):
            rest_of_the_word.append(string_to_search[i])
        first_word = ''.join(map(str, first_word))
        rest_of_the_word = ''.join(map(str, rest_of_the_word))

    else:  # if whitespace is not there, its a single word so no seperation of word needed
        first_word = ''.join(map(str, string_to_search))

    if type_of_search == 1:  # searching for pos quotes
        if string_to_search[1] == "\"":
            # If the string starts with " , a different regex is needed.
            # string[1] is being used in if statement because 1st element is a "
            if loc_of_space is not None:
                string_processing = [r'^[']
                string_processing.append(first_word.lower())
                string_processing.append(r']+')
                string_processing.append(rest_of_the_word.lower())
                string_processing.append(r"\W")  # to capture comma
                # converting the list to string
                raw = ''.join(map(str, string_processing))
            else:  # if its a single word string
                string_processing = ['']
                string_processing.append(first_word.lower())
                raw = ''.join(map(str, string_processing))
        else:
            # converting the list to string
            string_to_search = ''.join(map(str, string_to_search))
            string_processing = [r'\b']
            string_processing.append(string_to_search.lower())
            string_processing.append(r"\W")
            raw = ''.join(map(str, string_processing))

    elif type_of_search == 2:  # searching for pos dictionary
        string_to_search = ''.join(map(str, string_to_search))
        string_processing = [r'\b']
        string_processing.append(string_to_search.lower())
        string_processing.append(r"\b")
        raw = ''.join(map(str, string_processing))

    return raw
