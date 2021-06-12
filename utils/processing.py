import csv
import portalocker


def divide_chunks(index_list, n_chunks):
    """ Divide the index list into 'n' equal chunks
    """
    for i in range(0, len(index_list), n_chunks):
        yield index_list[i:i + n_chunks]


def get_book(book_number):

    if book_number == 1:  # prince of slytherin
        book_md = "data/books/Harry Potter and the Prince of Slytherin_md.txt"

    elif book_number == 2:  # black luminary
        book_md = "data/books/Black Luminary_md.txt"

    elif book_number == 3:  # AoC
        book_md = "data/books/Harry Potter and the Ashes of Chaos_md.txt"

    return book_md


def get_dictionary_data():
    sheet1 = "data/dictionary/POS Dictionary - Sheet1.csv"
    sheet2 = "data/dictionary/POS Dictionary - Sheet2.csv"

    data = {}
    data["dictionary"] = []

    with portalocker.Lock(sheet2):
        with open(sheet2) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")

            dictionary_terms1 = []
            for row in csv_reader:

                dictionary_terms1.append(row)

            dictionary_terms1.pop(0)

    with portalocker.Lock(sheet1):
        with open(sheet1) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")

            dictionary_terms2 = []
            for row in csv_reader:
                dictionary_terms2.append(row)

            dictionary_terms2.pop(0)

    page_count = 0
    for i in range(len(dictionary_terms1)):
        page_count += 1
        data["dictionary"].append(
            {
                "title": f"{str(page_count)}) {str(dictionary_terms1[i][0])}",
                "description": str(dictionary_terms1[i][1]),
            }
        )
    for j in range(len(dictionary_terms2)):

        page_count += 1
        data["dictionary"].append(
            {
                "title": f"{str(page_count)}) {str(dictionary_terms2[j][0])}",
                "description": str(dictionary_terms2[j][1]),
            }
        )

    return data
