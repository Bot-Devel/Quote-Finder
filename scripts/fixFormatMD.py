import re
import sys
import argparse

parser = argparse.ArgumentParser(
    description="A simple command-line script which takes a markdown txt file as the input, removes unnecessary formatting as needed and outputs the cleaned markdown file.")
parser.add_argument("-i", "--input", help="Input markdown txt file")
parser.add_argument("-o", "--output", help="Output markdown txt file")
args = parser.parse_args()


if args.input and args.output:
    with open(args.input, "r") as file_input:
        md_book = file_input.read()

        # Test if the occurences of ### is equal to the number of chapters+1(The 1st line)
        print("Number of occurences of ### (Should be number of chapters+1): ",
              len(re.findall(r'### ', md_book)))

        print("Removing extra paragraphs and white spaces from both the two files")
        # \n+ is used to capture the whitespaces
        md_book_rws = re.sub(r'(?:\n+(\*+ *))?\n+',
                             r'\n\n', md_book, flags=re.M)

        print("Removing *** from the files")
        md_book_rstar = re.sub(r'\n+ *\* *\* *\* *\n+', r'\n\n',
                               md_book_rws, flags=re.M)

        print("Removing \*\*\* from the files")
        md_book_rstar1 = re.sub(r'\n+^\\\*\\\*\\\*$\n+', r'\n\n',
                                md_book_rstar, flags=re.M)

        print("Removing \*\*\*\* from the files")
        md_book_rstar2 = re.sub(r'\n+^\\\*\\\*\\\*\\\*$\n+', r'\n\n',
                                md_book_rstar1, flags=re.M)

        print("Removing ### from the files")
        md_book_rstar3 = re.sub(r'### ', r'',
                                md_book_rstar2, flags=re.M)

    with open(args.output, "w") as file_output:
        print(f"Writing to {args.output}")
        file_output.write(md_book_rstar3)
else:
    parser.print_help()
    sys.exit(0)
