import re


def pos_chapter_processing(chapter_heading):
    """
    Process the chapter heading and return
    chapter title & chapter url
    """

    # list containing the chapter header split each character
    chapter_heading_list = list(chapter_heading)
    chapter_number = []
    for i in range(0, len(chapter_heading_list)):
        if '&' == chapter_heading_list[i]:
            loc_of_and = i  # location of "&" in the chapter heading list
            # incrementing 4 will put the index at the chapter number
            # of the chapter i.e. "1" in  139. HB&TRG 1: In Which Plans Are Made
            loc_of_and += 4
            # Sometimes there are two or more &s,
            # without break, the index is overwritten
            break

    chapter_template = ['C', 'h', 'a', 'p', 't', 'e', 'r', ' ']
    book_name = []
    chapter_title = []

    try:
        for i in range(loc_of_and, len(chapter_heading_list)):
            # Appending the chapter number and name i.e. Chapter 50: The King of Rats
            chapter_template.append(chapter_heading_list[i])
        for i in range(0, loc_of_and):
            # Appending the global chapter number and book name i.e 134. HP&DEM
            book_name.append(chapter_heading_list[i])

    except UnboundLocalError:  # first page
        book_name.append("First Page")

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
    # removing non-numeric characters like *
    chapter_number = filter(str.isdigit, chapter_number)
    # converting the filter object to string
    chapter_number = ''.join(chapter_number)

    url = "https://www.fanfiction.net/s/11191235/" + \
        chapter_number

    return chapter_title, url


def default_chapter_processing(chapter_heading, base_url: str):
    """
    Process the default chapter heading and return
    chapter title & chapter url
    """

    # get the chapter number from the heading
    chapter_number = (re.search(r'^\d+\.', chapter_heading)).group(0)
    chapter_number = chapter_number.replace(".", "")
    url = base_url+chapter_number

    return chapter_heading, url


def get_chapter_head_tag(book_number, quote_found, book_lines):
    """
    Process the chapter heading and book tag and
    return book_tag & chapter_heading
    """

    chapter_heading = []  # line containg the chapter heading

    # book_tag is used to match the chapter title using regex
    if book_number == 1:  # prince of slytherin
        if quote_found < 51316:  # after line number 51316, "HB" starts
            book_tag = ". HP&"  # till chapter 138
        else:
            book_tag = ". HB&"  # from chapter 139

    elif book_number == 2:  # black luminary
        if quote_found < 8989:  # after line number 8989, "VoD" starts
            book_tag = ". HD"  # till chapter 25
        elif quote_found < 22301:
            book_tag = ". VoD"  # till chapter 49
        else:
            book_tag = ". ML"  # after chapter 49

    elif book_number == 3:  # AoC
        if quote_found < 316:  # prologue
            book_tag = ". Prologue"  # Just the first chapter
        elif quote_found < 9468:
            book_tag = ". TFA"  # Book 1
        else:
            book_tag = ". SS"  # Book 2

    elif book_number == 4:  # PoDK
        book_tag = r"(\d+\. Book|\d+\. HP Book|\d+\. Chapter)"

    for i in range(quote_found, 0, -1):
        if re.search(book_tag, book_lines[i], re.I):
            # append all the lines containing the chapter heading from
            # the last chapter to the chapter containing the quote_found
            chapter_heading.append(book_lines[i])

    if len(chapter_heading) == 0:
        # dummy chapter heading
        chapter_heading.append("0. First Page")

    return book_tag, chapter_heading


def get_chapter_title_url(book_number, chapter_heading):
    """
    Process the chapter title and url and
    return chapter_title, chapter_url
    """

    if book_number == 1:  # prince of slytherin
        chapter_title, chapter_url = pos_chapter_processing(
            chapter_heading)

    elif book_number == 2:  # black luminary
        chapter_title, chapter_url = default_chapter_processing(
            chapter_heading, "https://www.fanfiction.net/s/12125300/")

    elif book_number == 3:  # AoC
        chapter_title, chapter_url = default_chapter_processing(
            chapter_heading, "https://www.fanfiction.net/s/13507192/")

    elif book_number == 4:  # PoDK
        chapter_title, chapter_url = default_chapter_processing(
            chapter_heading, "https://www.fanfiction.net/s/3766574/")
        # return chapter_heading, "https://www.fanfiction.net/s/3766574/"

    return chapter_title, chapter_url
