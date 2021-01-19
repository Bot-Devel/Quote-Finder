import pandas as pd
import json
from utils import get_dict_index


def ExcelToJson():
    """ Reads the excel sheet and then writes to the json file
    """
    file1 = "data/POS Dictionary.xlsx"
    data = {}
    data['dictionary'] = []
    index = get_dict_index()
    df = pd.read_excel(file1,
                       sheet_name=0,
                       index_col=0)
    for i in range(len(index)):
        data['dictionary'].append({
            'title': index[i],
            'description': df.loc[index[i]][0],
        })
    with open('data/POS Dictionary.json', 'w') as outfile:
        json.dump(data, outfile)


ExcelToJson()
