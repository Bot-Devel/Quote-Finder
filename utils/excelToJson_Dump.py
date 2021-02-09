import pandas as pd
import json


def get_dict_index():
    """ Read the Title column of the excel file and assign it
     to two index for each sheet and return the indices
    """
    file1 = "data/POS Dictionary.xlsx"
    # Read sheet2 first since that one contains all the word definitions
    df1 = pd.read_excel(file1, "Sheet2")
    df2 = pd.read_excel(file1, "Sheet1")

    df1.set_index('Title')
    df2.set_index('Title')

    df1.dropna()
    df2.dropna()

    index1 = df1['Title'].values[:]
    index2 = df2['Title'].values[:]

    index1 = index1[~pd.isnull(index1)]
    index2 = index2[~pd.isnull(index2)]

    return index1, index2


def ExcelToJson():
    """ Reads the excel sheet and then writes to the json file
    """

    file1 = "data/POS Dictionary.xlsx"
    data = {}
    data['dictionary'] = []
    index1, index2 = get_dict_index()

    df1 = pd.read_excel(file1,
                        "Sheet2",
                        index_col=0)
    df2 = pd.read_excel(file1,
                        "Sheet1",
                        index_col=0)

    for i in range(len(index1)):
        data['dictionary'].append({
            # str(i+1) is used since initially i=0
            'title': str(i+1)+") "+str(index1[i]),
            'description': str(df1.loc[index1[i]][0]),
        })

    for j in range(len(index2)):
        i += 1  # In the prev loop, i=14 and we did i+1 during appending but we need it to be 15 for the next loop
        data['dictionary'].append({
            'title': str(i+1)+") "+str(index2[j]),
            'description': str(df2.loc[index2[j]][0]),
        })

    with open('data/POS Dictionary.json', 'w') as outfile:
        json.dump(data, outfile)


ExcelToJson()
