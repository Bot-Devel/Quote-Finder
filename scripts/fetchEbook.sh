#!/bin/bash
echo "Cron job started"

# Activate your virtualenv using
# your respective environment manager
if which pyenv > /dev/null; then
    eval "$(pyenv init --path)" # this only sets up the path stuff
    eval "$(pyenv init -)"      # this makes pyenv work in the shell
fi
if which pyenv-virtualenv-init > /dev/null; then
    eval "$(pyenv virtualenv-init - zsh)"
fi
pyenv activate fanfic-download

cd 'ebook processing/Downloaded'
echo "Updating the epub files using fanficfare"
fanficfare -up https://www.fanfiction.net/s/11191235/1/Harry-Potter-and-the-Prince-of-Slytherin
fanficfare -up https://www.fanfiction.net/s/12125300/1/Black-Luminary
echo "Downloaded the epub from fanficfare"

echo "Converting the epub files to markdown txt files"
ebook-convert 'Harry Potter and the Prince of Slytherin-ffnet_11191235.epub' 'Harry Potter and the Prince of Slytherin_md.txt' --txt-output-formatting markdown
ebook-convert 'Black Luminary-ffnet_12125300.epub' 'Black Luminary_md.txt' --txt-output-formatting markdown
echo "Conversion using calibre completed"

cd ../..

echo "Cleaning the markdown files"
python scripts/fixFormatMD.py -i "ebook processing/Downloaded/Harry Potter and the Prince of Slytherin_md.txt" -o "ebook processing/Processed/Harry Potter and the Prince of Slytherin_md.txt"
python scripts/fixFormatMD.py -i "ebook processing/Downloaded/Black Luminary_md.txt" -o "ebook processing/Processed/Black Luminary_md.txt"

# Copy the processed files to data/books/
# cp -r "ebook processing/Processed/." "data/books/"
echo "Cron job completed"