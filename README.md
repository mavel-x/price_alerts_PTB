# Price alerts telegram bot
Get custom price alerts for any Yahoo ticker via telegram.

How to use:
1. Get a bot token from BotFather.
2. Create a file 'cred.json' and add your token to it as follows:
{"TOKEN": "(insert-token-here)"}
3. Add the absolute path to the directory where the files are stored on your server to the PATH variable in "database.py"
4. Set up "alerts.py" and "get\_top\_10.py" to run from crontab (every 1 or 5 min for "alerts" and every hour for "top_10").
5. Set up "main.py" to run as a service.
