import re

md_input = open(
    "Downloaded/Black Luminary_md.txt", "r")

md_output = open(
    "Processed/Black Luminary_md.txt", "w")


md_book = md_input.read()

# Test if the occurences of ### is equal to the number of chapters+1(The 1st line)
test = re.findall(r'### ', md_book)
print("Number of occurences of ### (Should be number of chapters+1)-bl: ", len(test))

# Remove extra paragraphs and white spaces from both the two files
# \n+ is used to capture the whitespaces
md_book_rws = re.sub(r'(?:\n+(\*+ *))?\n+', r'\n\n', md_book, flags=re.M)

# Remove *** from the files
md_book_rstar = re.sub(r'\n+ *\* *\* *\* *\n+', r'\n\n',
                       md_book_rws, flags=re.M)

# Remove \*\*\* from the files
md_book_rstar1 = re.sub(r'\n+^\\\*\\\*\\\*$\n+', r'\n\n',
                        md_book_rstar, flags=re.M)

# Remove \*\*\*\* from the files
md_book_rstar2 = re.sub(r'\n+^\\\*\\\*\\\*\\\*$\n+', r'\n\n',
                        md_book_rstar1, flags=re.M)

# Remove ### from the files
md_book_rstar3 = re.sub(r'### ', r'',
                        md_book_rstar2, flags=re.M)

md_output.write(md_book_rstar3)
