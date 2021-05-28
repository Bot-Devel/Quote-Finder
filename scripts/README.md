# Scripts

The scripts found in the `scripts/` directory are used to process the `data/` files. <br/>
If you are going to add support for a new fanfiction, use these scripts to process the `.txt` file. If the fanfiction is part of a series, merge them into a single `.txt` file to avoid having to maintain multiple files.

## fetchEbook.sh

This script uses [FanFicFare](https://github.com/JimmXinu/FanFicFare) to update/download the necessary epub files for the fanfiction. Then uses [Calibre](https://github.com/kovidgoyal/calibre)'s ebook-convert to convert the epub to a txt with markdown formatting. And then finally runs the `fixFormatMD.py` to remove all unnecessary formatting from the markdown txt file.

### Note

- The script uses `conda activate fanfic` to activate the conda python environment. If using `virtualenv` or others as the environment manager, replace the `conda activate fanfic` with the respective activate command.

- The directory names can be changed as necessary when running the script locally.
- If you want to run the `fetchEbook.sh` without any changes to the directory paths, create an `ebook processing/` sub-directory in the root directory of the repository and create `ebook processing/Downloaded/` & `ebook processing/Processed/` sub-directories inside the `ebook processing/` parent directory.

## fixFormatMD.py

A simple command-line script which takes the markdown txt file as the input, removes unnecessary formatting as needed and outputs the cleaned markdown file.

Run the script at the root directory of the repository.

### Note

- `ebook processing/` is included in the `.gitignore` file.

## excelToJson.py

A script which converts the `data/dictionary/POS Dictionary.xlsx` file to `data/dictionary/POS Dictionary.json` file.

## crontab & timestamp.sh

### crontab

The crontab is used to automate the `fetchEbook.sh` script by scheduling the system to run the script using a Cron job.

### timestamp.sh

This script is used along with the Cron job to log the time in the `cron.log` file.
