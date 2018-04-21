import json
import logging
import os
import sys

import discord
import regex as re
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
        # also, i'm doing this ugly getattr thing because sometimes iterating over dir directly works and sometimes it doesn't, but using dir
        #  to get the names of things as strings then using getattr does. computers are weird
        for item in [getattr(self, key) for key in map(str, dir(self))]:
            if callable(item) and item.__name__.startswith("_event_"):
                new_name = item.__name__.replace("_event_", "")
                setattr(self, new_name, self.event(item))
                self._logger.info("Remapping callable {} to event handler {}.".format(item.__name__, new_name))

        # compile regexes
        # this regex will match twitter status URLs, like this: https://twitter.com/JillKatze/status/981417200878804992
        # from there, we can extract the ids we need to interact with them through the twitter api
        # this will skip links that have their preview hidden with <angle brackets>
        self.twitter_id_regex = re.compile(r"(?<!\<)(?:https?:\/\/(?:[^\.\s]*\.)?twitter\.com\/[^\s]*\/status\/(\d+)[^\s]*)(?!\>)")

        # Tweets with certain East Asian character sets take up more visual space than other character sets and Discord truncates their previews sooner,
        #  from the perspective of string length. This regex will be used to guess if the heuristic for showing full tweets should lower its threshold.
        self.ea_chars_regex = re.compile(r"[\p{Block=CJK}\p{Block=Hangul}\p{Block=Hiragana}\p{Block=Katakana}]", re.UNICODE)

        self._logger.info("plsbot successfully initialized.")


    def run(self, *args, **kwargs):
        """Override of discord.Client.run.
        Loads tokens from config file to connect to Twitter and Discord, then starts the main event loop.
        """
        api_keys = self._settings.get("api_keys")
        assert api_keys, "api_keys entry not found in config.json. Please see documentation."

        # try to connect to twitter, but it's okay if we can't
        try:
            self._twitter = Twython(api_keys.get("twitter_app_key"), access_token=api_keys.get("twitter_access_token"))
            self._logger.info("plsbot sucessfully connected to Twitter.")
        except:
            self._logger.exception("Could not connect to Twitter. Check your Twitter keyes in config.json.")

        # make sure we have a proper token, then connect to discord and get the party started
        token = api_keys.get("discord_token")
        assert token and token != "replaceme", "Discord token was not set in config.json. Please see documentation."

        self._logger.info("plsbot connecting to Discord.")
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

        tweet_ids = self.twitter_id_regex.findall(message.content.lower())

        for tweet_id in tweet_ids:
            self._logger.debug("Saw a tweet with id {}".format(tweet_id))

            # if we couldn't connect to twitter, no point even trying anything  beyond here :3
            if self._twitter:
                tweet = None
                try:
                    tweet = self._twitter.show_status(id=tweet_id, tweet_mode="extended")
                except:
                    self._logger.exception("Unable to load tweet.")

                if tweet:
                    # Discord truncates tweets in its previews in a somewhat unpredictable way that doesn't match the way Twitter's API does it,
                    #  which appears to be based on visual space and not character count. This heurestically guesses if the tweet may have been
                    #  truncated within its actual text

                    # Remove any trailing t.co links
                    tweet_words = tweet["full_text"].split(" ")
                    while "https://t.co" in tweet_words[-1]:
                        tweet_words = tweet_words[:-1]
                    tweet_trailing_links_stripped = " ".join(tweet_words)

                    # count how many EA characters are in the string
                    ea_char_count = len(self.ea_chars_regex.findall(tweet_trailing_links_stripped))

                    # If the majority of chars in the tweet are EA, use a smaller threshold.
                    # These thresholds are based on some pretty arbitrary guesswork.
                    if float(ea_char_count)/len(tweet_trailing_links_stripped) > 0.5:
                        length_threshold = 95
                    else:
                        length_threshold = 230

                    if len(tweet_trailing_links_stripped) > length_threshold:
                        await self.send_message(message.channel, "Full tweet:\n```{}```".format(tweet["full_text"]))
                        self._logger.debug("Sent untruncated version of tweet {}.".format(tweet_id))

                    # since discord will preview the first image from a tweet, grab any images beyond the first one and link them so they get previews
                    if tweet.get("extended_entities") and tweet["extended_entities"].get("media"):
                        media_ids = [item["media_url_https"] for item in tweet["extended_entities"]["media"][1:] if item["type"] == "photo"]
                        if media_ids:
                            await self.send_message(message.channel, "Additional images from tweet: {}".format(" ".join(media_ids)))
                            self._logger.debug("Sent extra image links for tweet {}.".format(tweet_id))


if __name__ == "__main__":
    pls = Pls()
    try:
        pls.run()
    except:
        logging.getLogger('discord').exception("Uncaught exception in run(). Exiting.")
        exit()
