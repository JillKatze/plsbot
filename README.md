# plsbot
![pls](https://cdn.discordapp.com/attachments/430951369105604611/433186262204022787/plsrember.png)
>pls rember that wen u feel scare or frigten never forget ttimes wen u feeled happy
>
>wen day is dark alway rember happy day

this is a discord bot that monitors for twitter links and previews any additional images that the discord preview embed might have left out.

# setup
pls requires python 3.5+. required modules can be installed with `pip install -r requirements.txt` from the root of the repository.

if you want to use the twitter features (currently literally all this bot has as of the initial version), go to https://apps.twitter.com and create a new app. run `python get_twitter_token.py` to generate an access token and fill in the appropriate lines in config.json.

for your discord token, go to http://discordapp.com/developers/applications/me and create a new app, then once you've created it, hit the button to convert it to a bot. after that, there will be a link lower on the page to reveal your token. add this token to config.json.

after that, just run `python pls.py` and she should be up and running. you'll need to invite her to channels using a link like this, of course replacing YOUR_BOT_CLIENT_ID_HERE with your bot's ID from the App Details section at the top of your app page on the discord developer portal: https://discordapp.com/oauth2/authorize?client_id=YOUR_BOT_CLIENT_ID_HERE&scope=bot&permissions=66186303

# other stuff
this is currently super basic and while i would like to keep working on it, who knows if i actually will. everything is provided as-is, use at your own risk, et cetera.