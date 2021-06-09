<h1 align="center">Quote Finder</h1>

[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/) <br/>
This is a discord bot written in Python which searches a text file using RegEx to find a quote and output the line containing the quote as well as the next line in an embed message.<br/>
The bot currenly supports searching feature for the following fanfiction-
<br/>

- **Harry Potter and the Prince of Slytherin by The Sinister Man**
- **Black Luminary by YakAge**
- **Harry Potter and the Ashes of Chaos By ACI100**

<br/>

The bot's command prefix is `q` <br/>

# Bot Usage

Use `qf [quote]` to search quotes in the book and use `qhelp` to view the help menu.<br/>The quote is not case-sensitive so either uppercase, lowercase or combination of both can be used to search for the quote.<br/>The following is an example on how the bot works in realtime-

![](https://raw.githubusercontent.com/arzkar/Quote-Finder-Bot/main/images/bot_output.gif)

# Development

## Python

- Install Python >=3.8.5
- Create a python virtual environment in which you will be installing all the dependencies and activate it before installing the dependencies.
- Install the dependencies using `pip install -r requirements.txt`

## Git

- Create a new directory called `Quote Finder` in you system. You will be forking and cloning the [Quote-Finder](https://github.com/Bot-Devel/Quote-Finder) & [Quote-Finder-Data](https://github.com/Bot-Devel/Quote-Finder-Data) repository.

- [Quote-Finder](https://github.com/Bot-Devel/Quote-Finder) contains the source code for the bot.

- [Quote-Finder-Data](https://github.com/Bot-Devel/Quote-Finder-Data) contains the data files and is added as a submodule to the [Quote-Finder](https://github.com/Bot-Devel/Quote-Finder) repositories.

### Forking & Cloning the Quote-Finder Repository

- Fork the [Quote-Finder](https://github.com/Bot-Devel/Quote-Finder) repository and clone the fork in the `Quote Finder` directory using `git clone --recurse-submodules <URL>` since the repository contains a submodule.

- Create a new branch for your development. Do not add new features to the `main` branch.

### Forking & Cloning the Quote-Finder-Data Repository

- Since all the data files are stored in a separate Github repository called [Quote-Finder-Data](https://github.com/Bot-Devel/Quote-Finder-Data), you will need fork & clone it in the `Quote Finder` directory to add or updates data files.

- Add or update any files you need to and then push to your fork. Then make a PR to the [Upstream](https://github.com/Bot-Devel/Quote-Finder-Data)

### Updating the "data" submodule

- You will need to pull the submodule once your changes are merged in the [Quote-Finder-Data](https://github.com/Bot-Devel/Quote-Finder-Data) repository.

- In your `Quote-Finder` directory, you can simply `cd data/` and `git pull`, as you normally do for repositories since the submodule is also a git repository.

- Alternatively, you can also use `git submodule foreach git pull origin main` to pull the changes. This is the recommended way.

Note: This pulls from the Upstream [Quote-Finder-Data](https://github.com/Bot-Devel/Quote-Finder-Data) repository as configured in the `.gitmodules` file. During development, you can change the `url` of the submodule to your fork or you can directly update the files in your local `/data` directory.

## Discord

- Create a `.env` file which should contain the `DISCORD_TOKEN` for your testing bot as shown in the `.env.ex` file.

- Create a testing bot from the [Discord Developer Portal](https://discord.com/developers/applications) and copy the bot token to the `.env` file.

- Run the bot using `python main.py` in the root directory.

- To add support for other fanfictions, check the `scripts/` directory to know how to add the necessary data files.
