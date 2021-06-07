import re
import sys
import argparse

parser = argparse.ArgumentParser(
    description="A simple command-line script which takes a markdown txt file as the input, removes unnecessary formatting as needed and outputs the cleaned markdown file.")
parser.add_argument("-i", "--input", help="Input markdown txt file")
parser.add_argument("-o", "--output", help="Output markdown txt file")
args = parser.parse_args()


def regex_sub(pattern, sub, book):
    return re.sub(pattern, sub, book, flags=re.M)


if args.input and args.output:
    with open(args.input, "r", errors='ignore') as file_input:
        md_book = file_input.read()

        # Test if the occurences of ### is equal to the number of chapters+1(The 1st line)
        print("Number of occurences of ###: ",
              len(re.findall(r'### ', md_book)))

        print("Removing # from the file")
        md_book_formatted = regex_sub(r'^# ', r'', md_book)

        print("Removing ## from the file")
        md_book_formatted = regex_sub(r'^## ', r'', md_book_formatted)

        print("Removing ### from the file")
        md_book_formatted = regex_sub(r'^### ', r'', md_book_formatted)

        print("Removing *** from the file")
        md_book_formatted = regex_sub(r'\n+ *\* *\* *\* *\n+', r'\n\n',
                                      md_book_formatted)

        print("Removing \*\*\* from the file")
        md_book_formatted = regex_sub(r'\n+^\\\*\\\*\\\*$\n+', r'\n\n',
                                      md_book_formatted)

        print("Removing \*\*\*\* from the file")
        md_book_formatted = regex_sub(r'\n+^\\\*\\\*\\\*\\\*$\n+', r'\n\n',
                                      md_book_formatted)

        print(r"Removing '^n\b' from the file")
        md_book_formatted = regex_sub(r'^n\b', r'', md_book_formatted)

        print("Removing invalid continuation bytes from the file")
        md_book_formatted = regex_sub(r'^\s', r'',
                                      md_book_formatted)

        print("Removing thematic breaks the file")
        md_book_formatted = regex_sub(r'^\* \* \*', r'',
                                      md_book_formatted)

        print("Removing extra paragraphs and white spaces from the file")
        # \n+ is used to capture the whitespaces
        md_book_formatted = regex_sub(r'(?:\n+(\*+ *))?\n+', r'\n\n',
                                      md_book_formatted)

        print("Removing space, tab or newline characters from the file")
        md_book_formatted = regex_sub(r'^\s+', r'\n',
                                      md_book_formatted)

    with open(args.output, "w") as file_output:
        print(f"Writing to {args.output}")
        file_output.write(md_book_formatted)
else:
    parser.print_help()
    sys.exit(0)
