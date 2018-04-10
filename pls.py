import json
import logging
import os
import re
import sys

import discord
from twython import Twython


class Pls(discord.Client):
    """pls, a Discord bot.

    pls rember that wen u feel scare or frigten never forget ttimes wen u feeled happy

    wen day is dark alway rember happy day
    """
    def __init__(self):
        """Creates a new instance of pls and loads settings from config.json.
        Does not connect to Discord until run() is called.
        """
        super().__init__()

        # find the location of this file so we can always store logs next to it
        self._pls_dir = os.path.dirname(os.path.realpath(__file__))

        # piggyback on discord.py's logs for now
        self._logger = logging.getLogger('discord')

        # log everything to pls.log
        self._logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(filename=os.path.join(self._pls_dir, "pls.log"), encoding="utf-8", mode="w")
        file_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        self._logger.addHandler(file_handler)

        # log less noisy info to stdout
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
        console_handler.setLevel(logging.INFO)
        self._logger.addHandler(console_handler)

        # load config file, bail if it can't be loaded
        config_path = os.path.join(self._pls_dir, "config.json")
        try:
            with open(config_path) as f:
                self._settings = json.load(f)
        except Exception as e:
            self._logger.exception("Could not load config.json from {}.".format(config_path))
            raise e

        # we'll try to connect to twitter later but let's predefine the attribute for now
        self._twitter = None

        # apply discord.client.event decorator to any callable attributes whose names start with "_event_", storing them with that prefix stripped.
        # there might be a less ugly way to do this but this is my workaround for not having a "self" to refer to in decorators
        #   and i'll die before i define a global client variable like in all the discord.py examples :3
        for item in dir(self):
            if callable(item) and item.__name__.startswith("_event_"):
                setattr(self, item.__name__.replace("_event_", ""), self.event(item))


    def run(self, *args, **kwargs):
        """Override of discord.Client.run.
        Loads tokens from config file to connect to Twitter and Discord, then starts the main event loop.
        """
        api_keys = self._settings.get("api_keys")
        assert api_keys, "api_keys entry not found in config.json. Please see documentation."

        # try to connect to twitter, but it's okay if we can't
        try:
            self._twitter = Twython(api_keys.get("twitter_app_key"), access_token=api_keys.get("twitter_access_token"))
        except:
            self._logger.exception("Could not connect to Twitter. Check your Twitter keyes in config.json.")

        # make sure we have a proper token, then connect to discord and get the party started
        token = api_keys.get("discord_token")
        assert token and token != "replaceme", "Discord token was not set in config.json. Please see documentation."

        super().run(token)


    async def _event_on_ready(self):
        """on_ready event handler. Simply logs the successful connection.
        """
        self._logger.info("Logged in as {0.name} ({0.id})".format(self.user))


    async def _event_on_message(self, message):
        """on_message event handler. For now, only contains code for processing twitter links for the sake of
        printing full versions of truncated tweets and inserting links to additional images so they get previews
        inside of Discord. Eventually, this will need to be better modularized.
        """

        # if we couldn't connect to twitter, no point even trying anything :3
        if self._twitter:
            # this regex will match twitter status URLs, like this: https://twitter.com/JillKatze/status/981417200878804992
            # from there, we can extract the ids we need to interact with them through the twitter api
            # this will skip links that have their preview hidden with <angle brackets>
            twitter_regex = re.compile(r"(?<!\<)(?:https?:\/\/(?:[^\.\s]*\.)?twitter\.com\/[^\s]*\/status\/(\d+)[^\s]*)(?!\>)")
            tweet_ids = twitter_regex.findall(message.content.lower())

            for tweet_id in tweet_ids:
                self._logger.debug("Saw a tweet with id {}".format(tweet_id))

                tweet = None
                try:
                    tweet = self._twitter.show_status(id=tweet_id)
                except:
                    self._logger.exception("Unable to load tweet.")

                if tweet:
                    # tweets are sometimes truncated, which means we need to request it again to get the full version
                    # TODO: make this smart enough to skip sending when the only difference between truncated and untruncated is a t.co link at the end
                    if tweet["truncated"]:
                        try:
                            tweet_ext = self._twitter.show_status(id=tweet_id, tweet_mode="extended")
                            await self.send_message(message.channel, "Untruncated tweet:\n```{}```".format(tweet_ext["full_text"]))
                            self._logger.debug("Sent untruncated version of tweet {}.".format(tweet_id))
                        except:
                            self._logger.exception("Unable to fetch extended version of truncated tweet.")

                    # since discord will preview the first image from a tweet, grab any images beyond the first one and link them so they get previews
                    if tweet.get("extended_entities") and tweet["extended_entities"].get("media"):
                        media_ids = [item["media_url_https"] for item in tweet["extended_entities"]["media"][1:] if item["type"] == "photo"]
                        if media_ids:
                            await self.send_message(message.channel, "Additional images from tweet: {}".format(" ".join(media_ids)))
                            self._logger.debug("Sent extra image links for tweet {}.".format(tweet_id))


if __name__ == "__main__":
    pls = Pls()
    pls.run()
