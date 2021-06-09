import csv
sheet1 = "data/dictionary/POS Dictionary - Sheet1.csv"
sheet2 = "data/dictionary/POS Dictionary - Sheet2.csv"

data = {}
data["dictionary"] = []
# terms_count = 0
with open(sheet1) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=",")

    dictionary_terms1 = []
    for row in csv_reader:

        dictionary_terms1.append(row)

    dictionary_terms1.pop(0)

with open(sheet2) as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=",")

    dictionary_terms2 = []
    for row in csv_reader:
        dictionary_terms2.append(row)

    dictionary_terms2.pop(0)

for i in range(len(dictionary_terms1)):
    data["dictionary"].append({
        # str(i+1) is used since initially i=0
        "title": str(i+1)+") "+str(dictionary_terms1[i][0]),
        "description": str(dictionary_terms1[i][1]),
    })
for j in range(len(dictionary_terms2)):
    i += 1  # In the prev loop, i=14 and we did i+1 during appending but we need it to be 15 for the next loop
    data["dictionary"].append({
        "title": str(i+1)+") "+str(dictionary_terms2[j][0]),
        "description": str(dictionary_terms2[j][1]),
    })
    

print(data)
