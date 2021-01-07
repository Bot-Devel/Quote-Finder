import re

pt_input = open(
    "Downloaded/Harry Potter and the Prince of Slytherin_pt.txt", "r")
md_input = open(
    "Downloaded/Harry Potter and the Prince of Slytherin_md.txt", "r")
pt_output = open(
    "Processed/Harry Potter and the Prince of Slytherin_pt.txt", "w")
md_output = open(
    "Processed/Harry Potter and the Prince of Slytherin_md.txt", "w")

pt_book = pt_input.read()
md_book = md_input.read()

# Test if the occurences of ### is equal to the number of chapters+1(The 1st line)
test = re.findall(r'### ', md_book)
print("Number of occurences of ### (Should be number of chapters+1): ", len(test))

# Remove extra paragraphs and white spaces from both the two files
# \n+ is used to capture the whitespaces
pt_book_rws = re.sub(r'(?:\n+(\*+ *))?\n+', r'\n\n', pt_book, flags=re.M)
md_book_rws = re.sub(r'(?:\n+(\*+ *))?\n+', r'\n\n', md_book, flags=re.M)

# Remove *** from the files
pt_book_rstar = re.sub(r'\n+ *\* *\* *\* *\n+', r'\n\n',
                       pt_book_rws, flags=re.M)
md_book_rstar = re.sub(r'\n+ *\* *\* *\* *\n+', r'\n\n',
                       md_book_rws, flags=re.M)

# Remove \*\*\* from the files
pt_book_rstar1 = re.sub(r'\n+^\\\*\\\*\\\*$\n+', r'\n\n',
                        pt_book_rstar, flags=re.M)
md_book_rstar1 = re.sub(r'\n+^\\\*\\\*\\\*$\n+', r'\n\n',
                        md_book_rstar, flags=re.M)

# Remove \*\*\*\* from the files
pt_book_rstar2 = re.sub(r'\n+^\\\*\\\*\\\*\\\*$\n+', r'\n\n',
                        pt_book_rstar1, flags=re.M)
md_book_rstar2 = re.sub(r'\n+^\\\*\\\*\\\*\\\*$\n+', r'\n\n',
                        md_book_rstar1, flags=re.M)

# Remove ### from the files
pt_book_rstar3 = re.sub(r'### ', r'',
                        pt_book_rstar2, flags=re.M)
md_book_rstar3 = re.sub(r'### ', r'',
                        md_book_rstar2, flags=re.M)

pt_output.write(pt_book_rstar3)
md_output.write(md_book_rstar3)
