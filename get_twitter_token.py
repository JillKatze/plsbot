from twython import Twython

print("This utility will obtain an OAuth2 access token from Twitter given an app key and app secret.\nFor more info, see https://apps.twitter.com/\n")
app_key = input("Twitter app key: ")
app_secret = input("Twitter app secret: ")

twitter = Twython(app_key, app_secret, oauth_version=2)
access_token = twitter.obtain_access_token()

print("\nAccess token: {}".format(access_token))
print("\nIf the token looks correct, add it and your twitter app key to config.json to enable the Twitter API in pls.\n")