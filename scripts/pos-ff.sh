#!/bin/sh
echo "Cron job started"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate fanfic

cd '~/Personal/Git/Quote Finder/Files/Downloaded'
fanficfare -up https://www.fanfiction.net/s/11191235/1/Harry-Potter-and-the-Prince-of-Slytherin
fanficfare -up https://www.fanfiction.net/s/12125300/1/Black-Luminary

echo "Downloaded the fic from fanficfare"
ebook-convert 'Harry Potter and the Prince of Slytherin-ffnet_11191235.epub' 'Harry Potter and the Prince of Slytherin_pt.txt' --txt-output-formatting plain 
ebook-convert 'Harry Potter and the Prince of Slytherin-ffnet_11191235.epub' 'Harry Potter and the Prince of Slytherin_md.txt' --txt-output-formatting markdown

ebook-convert 'Black Luminary-ffnet_12125300.epub' 'Black Luminary_pt.txt' --txt-output-formatting plain 
ebook-convert 'Black Luminary-ffnet_12125300.epub' 'Black Luminary_md.txt' --txt-output-formatting markdown

echo "Conversion using calibre completed"
cd ..
python pos-regex.py
python bl-regex.py
echo "Cron job completed"