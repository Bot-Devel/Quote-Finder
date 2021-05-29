<h1 align="center">Quote Finder</h1>

[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/) <br/>
This is a discord bot written in Python which searches a text file using RegEx to find a quote and output the line containing the quote as well as the next line in an embed message.<br/>
The bot currenly supports searching feature for the following fanfiction-
<br/>

- **Harry Potter and the Prince of Slytherin by The Sinister Man**
- **Black Luminary by YakAge**

<br/>

The bot's command prefix is `q` <br/>

# Bot Usage

Use `qf [quote]` to search quotes in the book and use `qhelp` to view the help menu.<br/>The quote is not case-sensitive so either uppercase, lowercase or combination of both can be used to search for the quote.<br/>The following is an example on how the bot works in realtime-

![](https://raw.githubusercontent.com/arzkar/Quote-Finder-Bot/main/images/bot_output.gif)

# Development

- Install Python >=3.8.5
- Create a python virtual environment in which you will be installing all the dependencies and activate it before installing the dependencies.
- Fork the repository and clone the fork in a directory and create a new branch for your development. Do not add new features to the `main` branch.
- Install the dependencies using `pip install -r requirements_dev.txt`
- Rename the `.env.ex` file to `.env` which should contain the `DISCORD_TOKEN` for your testing bot.
- Create a testing bot from the [Discord Developer Portal](https://discord.com/developers/applications) and copy the bot token to the `.env` file.
- Run the bot using `python main.py` in the root directory.
- To add support for other fanfictions, check the `scripts/` directory to know how to add the necessary `data/` files.
