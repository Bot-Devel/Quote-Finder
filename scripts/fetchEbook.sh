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
pyenv activate ff-yt-dl

cd 'ebook processing/Downloaded'
echo "Updating the epub files using fanficfare"
fanficfare -up https://www.fanfiction.net/s/11191235/1/Harry-Potter-and-the-Prince-of-Slytherin
# fanficfare -up https://www.fanfiction.net/s/12125300/1/Black-Luminary
# fanficfare -up https://www.fanfiction.net/s/3766574/1/Prince-of-the-Dark-Kingdom
echo "Downloaded the epub from fanficfare"

echo "Converting the epub files to markdown txt files"
ebook-convert 'Harry Potter and the Prince of Slytherin-ffnet_11191235.epub' 'Harry Potter and the Prince of Slytherin_md.txt' --txt-output-formatting markdown
# ebook-convert 'Black Luminary-ffnet_12125300.epub' 'Black Luminary_md.txt' --txt-output-formatting markdown
# ebook-convert 'Prince of the Dark Kingdom-ffnet_3766574.epub' 'Prince of the Dark Kingdom_md.txt' --txt-output-formatting markdown
echo "Conversion using calibre completed"

cd ../..

echo "Cleaning the markdown files"
python scripts/fixFormatMD.py -i "ebook processing/Downloaded/Harry Potter and the Prince of Slytherin_md.txt" -o "ebook processing/Processed/Harry Potter and the Prince of Slytherin_md.txt"
# python scripts/fixFormatMD.py -i "ebook processing/Downloaded/Black Luminary_md.txt" -o "ebook processing/Processed/Black Luminary_md.txt"
# python scripts/fixFormatMD.py -i "ebook processing/Downloaded/Prince of the Dark Kingdom_md.txt" -o "ebook processing/Processed/Prince of the Dark Kingdom_md.txt"

# Copy the processed files to data/books/
cp -r "ebook processing/Processed/." "../Quote-Finder-Data/books"
echo "Cron job completed"

