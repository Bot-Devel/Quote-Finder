import re
import discord


def search_string(book1, book2, string_to_search):
    """Search for the given string in the file and return all the lines of the
    book as a list and list of all the line numbers containing the string"""
    line_number = 0
    mylines = []  # contains all the lines of the book as a list
    index = []  # list of all the line numbers containing the string
    ar1 = [r'\b']
    ar1.append(string_to_search.lower())
    ar1.append(r"\W")
    ar2 = ''.join(map(str, ar1))
    ar2.join(ar1)
    raw = r"{}".format(ar2)
    # Open the file in read only mode
    with open(book1, 'r') as read_obj1:
        for line in read_obj1:
            # For each line, check if line contains the string
            line_number += 1
            if re.search(raw, line.lower()) is not None:
                # if string found, append the line number
                index.append(line_number)
    if len(index) == 0:  # =if string was found, index list wont be empty
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


def quote_find(arg1, page_number):
    """Find the quote and return both the line containing the quote as well as
     the next line, chapter heading of the chapter where the quote was found
     and quote found counter """
    file1 = "Text Files/Harry Potter and the Prince of Slytherin_pt.txt"
    file2 = "Text Files/Harry Potter and the Prince of Slytherin_md.txt"
    # book_lines=list of all the lines of the book and line_number=line number where string is found
    book_lines, line_number1, quote_found_ctr = search_string(
        file1, file2, arg1)
    # Subtracting 1 from the line_number list because of mismatch of line number when all the lines were assigned to list book_lines
    line_number2 = [x - 1 for x in line_number1]
    result = []  # list contains the line where the quote was found and the next line
    chapter_heading = []  # line containg the chapter heading
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
    if quote_found < 51316:  # after line number 51316, ". HB&" starts
        pos_book_tag = ". HP&"  # till chapter 138
    else:  # pos_book_tag is the identifier used to recognize the book name i.e. HP or HB
        pos_book_tag = ". HB&"  # from chapter 139
    for i in range(quote_found, 0, -1):
        if pos_book_tag in book_lines[i]:
            # append all the lines containing the chapter heading from the last chapter to the chapter containing the quote_found
            chapter_heading.append(book_lines[i])
    quote_found += 2  # line number of the next line after the line where the quote was found
    next_line = book_lines[quote_found]  # Next line of the quote
    str1 = ""  # final output string
    for i in range(1):
        # Assigning the 1st value of the result list i.e. the line containing the quote
        str1 += result[0]
        str1 += "\n\n"  # Two nextlines to make it more clean
        str1 += next_line  # Concatinating both the line containing the quote and the next line
    if len(chapter_heading) == 0:
        # dummy book+chap name
        chapter_heading.append("0. HP&POS 0: First Page")
    str1 = '%.2047s' % str1
    # chapter_heading[0] contains the chapter heading of the chapter where the quote was found
    return str1, chapter_heading[0], quote_found_ctr, len(line_number2)


def chapter_processing(chap1):
    """Process the chapter heading and return chapter title and chapter url """
    # list containing the chapter header i.e 139. HB&TRG 1: In Which Plans Are Made
    chapter_heading_list = list(chap1)
    chapter_number = []
    for i in range(0, len(chapter_heading_list)):
        if '&' == chapter_heading_list[i]:
            loc_of_and = i  # location of "&" in the chapter heading list
            loc_of_and += 4  # incrementing 4 will put the index at the chapter number of the chapter i.e. "1" in  139. HB&TRG 1: In Which Plans Are Made
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
        chapter_number+"/Harry-Potter-and-the-Prince-of-Slytherin"
    return chapter_title, url


def embed_page(arg, page=0):
    chapter_desription, chapter_heading, quote_found_ctr, page_limit = quote_find(
        arg, page)
    if quote_found_ctr == 1:  # to fix the  UnboundLocalError: local variable 'loc_of_and' referenced before assignment error
        chapter_title, chapter_url = chapter_processing(
            chapter_heading)
    chapter_desription = chapter_desription + \
        "\n"+"Page: "+str(page+1)+'/'+str(page_limit)
    if quote_found_ctr == 1:
        embed1 = discord.Embed(title=''.join(chapter_title),
                               url=chapter_url,
                               description=chapter_desription,
                               colour=discord.Colour(0x272b28))
        return embed1, page_limit
    elif quote_found_ctr == 0:
        embed1 = discord.Embed(
            description="Quote not found!",
            colour=discord.Colour(0x272b28))
        return embed1, page_limit
    elif quote_found_ctr == 2:
        embed1 = discord.Embed(
            description="No more quotes found. Please go back to the previous page",
            colour=discord.Colour(0x272b28))
        return embed1, page_limit
