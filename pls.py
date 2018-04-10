import json
import logging
import os
import re
import sys

import discord
from twython import Twython

class Pls(discord.Client):
    def __init__(self):
        super().__init__()
        self._pls_dir = os.path.dirname(os.path.realpath(__file__))

        self._logger = logging.getLogger('discord')
        self._logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(filename=os.path.join(self._pls_dir, "pls.log"), encoding="utf-8", mode="w")
        file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        self._logger.addHandler(file_handler)
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        console_handler.setLevel(logging.INFO)
        self._logger.addHandler(console_handler)

        try:
            with open(os.path.join(self._pls_dir, "config.json")) as f:
                self._settings = json.load(f)
        except:
            self._logger.exception("Could not load config file. Exiting.")
            exit(1)

        try:
            api_keys = self._settings.get("api_keys")
            self._twitter = Twython(api_keys.get("twitter_app_key"), access_token=api_keys.get("twitter_access_token"))
        except:
            self._logger.exception("Could not connect to Twitter.")

        @self.event
        async def on_ready():
            self._logger.info("Logged in as {0.name} ({0.id})".format(self.user))

        @self.event
        async def on_message(message):
            twitter_regex = re.compile(r"(?<!\<)(?:https?:\/\/(?:[^\.\s]*\.)?twitter\.com\/[^\s]*\/status\/(\d+)[^\s]*)(?!\>)")
            tweet_ids = twitter_regex.findall(message.content.lower())

            for tweet_id in tweet_ids:
                self._logger.debug("Saw a tweet with id {}".format(tweet_id))

                try:
                    tweet = self._twitter.show_status(id=tweet_id)
                except:
                    self._logger.debug("Unable to load tweet.")

                if tweet:
                    if tweet["truncated"]:
                        try:
                            tweet_ext = self._twitter.show_status(id=tweet_id, tweet_mode="extended")
                            await self.send_message(message.channel, "Untruncated tweet:\n```{}```".format(tweet_ext["full_text"]))
                            self._logger.debug("Sent untruncated version of tweet {}.".format(tweet_id))
                        except:
                            self._logger.debug("Unable to fetch extended version of truncated tweet.")

                    if tweet.get("extended_entities") and tweet["extended_entities"].get("media"):
                        media_ids = [item["media_url_https"] for item in tweet["extended_entities"]["media"][1:] if item["type"] == "photo"]
                        if media_ids:
                            await self.send_message(message.channel, "Additional images from tweet: {}".format(" ".join(media_ids)))
                            self._logger.debug("Sent extra image links for tweet {}.".format(tweet_id))

    def run(self, *args, **kwargs):
        token = self._settings.get("api_keys").get("discord_token")
        if not token:
            raise ValueError("Discord token was not set in config.json. Please see documentation.")
        super().run(token)

if __name__ == "__main__":
    pls = Pls()
    pls.run()
