def get_raw_string(type_of_search, string_to_process, book):
    """Process the given string and return the regex as a raw string"""
    string_processing = []

    if type_of_search == 1:  # searching for book quotes

        if string_to_process[1] == "\"":
            # string[1] because 1st two elements are \ & " respectively
            string_processing = [r'^[\"]+']

            # pop the 1st two elements out since they are \ & " respectively
            string_to_process = string_to_process[2:]
            string_processing.append(string_to_process.lower())

            raw = ''.join(map(str, string_processing))

        elif string_to_process[0] == "\'":
            # string[0] because 1st element is '

            string_processing = [r'^[\']+']

            # pop the 1st elements out since its '
            string_to_process = string_to_process[1:]
            string_processing.append(string_to_process.lower())

            raw = ''.join(map(str, string_processing))

        else:

            string_processing = [r'\b']
            string_processing.append(string_to_process.lower())
            string_processing.append(r"\W")
            raw = ''.join(map(str, string_processing))

    elif type_of_search == 2:  # searching for pos dictionary

        string_processing = [r'\b']
        string_processing.append(string_to_process.lower())
        # Using \b to exclude . after a word
        string_processing.append(r"\b")
        raw = ''.join(map(str, string_processing))

    return raw


def get_book(book):

    if book == 1:  # prince of slytherin
        book_pt = "data/books/Harry Potter and the Prince of Slytherin/Harry Potter and the Prince of Slytherin_pt.txt"
        book_md = "data/books/Harry Potter and the Prince of Slytherin/Harry Potter and the Prince of Slytherin_md.txt"

    elif book == 2:  # black luminary
        book_pt = "data/books/Black Luminary/Black Luminary_pt.txt"
        book_md = "data/books/Black Luminary/Black Luminary_md.txt"

    return book_pt, book_md
