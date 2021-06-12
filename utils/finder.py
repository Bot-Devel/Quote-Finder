import csv
import portalocker

from utils.search import search_string, search_dict
from utils.chapter_processing import get_chapter_head_tag


def dict_index():
    """ Read the json file and append the title values to the index
    and return index
    """

    data = get_dictionary_data()
    index = []

    for i in data['dictionary']:
        index.append(i['title'])

    return index


def pos_dict(arg, page, use_keywords):
    """ Call search_dict() and return title,
    description & quote_found_ctr
    """

    data = get_dictionary_data()

    title, description, quote_found_ctr, page_limit = search_dict(
        data, arg, page, use_keywords)

    # To fix the embed.description: Must be 2048 or fewer in length error
    if len(list(description)) > 2048:
        description = description[:2020] + "..."

    description += f"\n\nPage {str(page+1)} of {str(page_limit)}"

    return title, description, quote_found_ctr, page_limit


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
