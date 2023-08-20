import time
import datetime
import dateutil.parser
from numpy.core.fromnumeric import trace
import requests
import json
import pprint
import datetime
import tweepy
import pytz
import urllib
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont
import traceback
import twitch

f = open('accounts.json')
accounts = json.load(f)

if os.path.exists("auth.json"):
    f = open('auth.json')
    auth_json = json.load(f)

    SMASHGG_KEY = auth_json["SMASHGG_KEY"]

MAX_DURATION_SECONDS = 2*60


def DownloadClips(account):
    try:
        clips = twitch.get_clips(account["twitch_game_name"])

        myClips = []

        brClips = clips.get("pt-br", [])

        whitelist = [
            '277200018',  # p7
        ]
        brClips += [c for c in clips.get("en", [])
                    if c["broadcaster_id"] in whitelist]

        blacklist = [
            '402617899',  # MariKyuutie
        ]
        brClips = [c for c in brClips if c["broadcaster_id"] not in blacklist]

        def sorting_key(x):
            return x["view_count"]

        brClips.sort(key=sorting_key, reverse=True)

        for clip in brClips:
            found = next((c for c in myClips if
                          c["broadcaster_id"] == clip["broadcaster_id"] and
                          abs(dateutil.parser.parse(c["created_at"]) - dateutil.parser.parse(clip["created_at"])).total_seconds()/60 < 5), None)

            if not found:
                myClips.append(clip)

            if len(myClips) >= 5:
                break

        for i, clip in enumerate(myClips):
            thumb_url = clip['thumbnail_url']
            mp4_url = thumb_url.split("-preview", 1)[0] + ".mp4"
            output_path = "clips/" + str(i) + ".mp4"

            def dl_progress(count, block_size, total_size):
                percent = int(count * block_size * 100 / total_size)
                print("Downloading clip "+str(i)+"...%d%%" % percent, end="\r")
                if percent == 100:
                    print("")

            # create the basepath directory
            if not os.path.exists("clips"):
                os.makedirs("clips")

            try:
                urllib.request.urlretrieve(
                    mp4_url, output_path, reporthook=dl_progress)
            except:
                print("An exception occurred")

            img = Image.new('RGBA', (1280, 720), color=(214, 214, 214, 255))
            d = ImageDraw.Draw(img, "RGBA")

            fnt_big = ImageFont.truetype('./smash_font.ttf', 40)
            fnt = ImageFont.truetype('./smash_font.ttf', 26)

            # topo
            d.rectangle((0, 0, 1280, 50), (49, 49, 49, 255))

            _, _, w, h = d.textbbox((0, 0), clip["title"], font=fnt_big)
            d.text((640-w/2, 5), clip["title"], font=fnt_big,
                   fill=(255, 255, 255), align="center")

            # rodape
            d.rectangle((0, 720-64, 1280, 720), (49, 49, 49, 255))

            # canal
            d.text((32, 720-64), "Canal: " +
                   clip["broadcaster_name"], font=fnt, fill=(255, 255, 255))

            # clippado por
            d.text((32, 720-32), "Clip: " +
                   clip["creator_name"], font=fnt, fill=(255, 255, 255))

            # view_count
            view_count = str(clip["view_count"]) + " views"
            _, _, w, h = d.textbbox((0, 0), view_count, font=fnt)
            d.text((1280-32-w, 720-64), view_count,
                   font=fnt, fill=(255, 255, 255))

            # bot
            bot_text = "Vídeo gerado por @"+account["handle"]
            _, _, w, h = d.textbbox((0, 0), bot_text, font=fnt)
            d.text((1280-32-w, 720-32), "Vídeo gerado por @" +
                   account["handle"], font=fnt, fill=(255, 255, 255))

            img.save("clips/overlay.png")

            edit_clip: VideoFileClip = VideoFileClip("clips/"+str(i)+".mp4")
            edit_clip = edit_clip.resize(height=720-51-64)
            edit_clip = edit_clip.set_position(("center", 51))

            maxClipDuration = MAX_DURATION_SECONDS / 5

            if edit_clip.duration > maxClipDuration:
                # calculate the duration to be removed from the start and end
                remove_duration = (edit_clip.duration - maxClipDuration) / 2

                # extract the subclip with the desired duration
                edit_clip = edit_clip.subclip(
                    remove_duration, edit_clip.duration - remove_duration)

            overlay = ImageClip("clips/overlay.png",
                                transparent=True, duration=edit_clip.duration)
            overlay.set_position((0, 0))

            video = CompositeVideoClip([overlay, edit_clip])
            video.write_videofile("clips/"+str(i)+"_edited.mp4", preset='ultrafast',
                                  codec='libx264', audio_codec="aac", threads=4)

        edited_clips = []

        for i, clip in enumerate(myClips):
            clipfile = VideoFileClip("clips/"+str(i)+"_edited.mp4")
            if i == 0:
                edited_clips.append(clipfile)
            else:
                edited_clips.append(clipfile.crossfadein(1))

        final = concatenate_videoclips(edited_clips)
        final.write_videofile("clips/final.mp4", preset='ultrafast',
                              codec='libx264', audio_codec="aac", threads=4)
    except:
        print(traceback.format_exc())


for account in accounts:
    print(account)

    if accounts[account].get("post-clips", None) == None:
        continue

    BEARER_KEY = auth_json[account]["BEARER"]
    CONSUMER_KEY = auth_json[account]["CONSUMER_KEY"]
    CONSUMER_SECRET = auth_json[account]["CONSUMER_SECRET"]
    ACCESS_KEY = auth_json[account]["ACCESS_KEY"]
    ACCESS_SECRET = auth_json[account]["ACCESS_SECRET"]

    twitter_API_v2 = tweepy.Client(
        bearer_token=BEARER_KEY,
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        access_token=ACCESS_KEY,
        access_token_secret=ACCESS_SECRET
    )

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

    twitter_API = tweepy.API(auth)
    twitter_API.debug = True

    DownloadClips(accounts[account])

    upload_result = twitter_API.media_upload(
        filename='clips/final.mp4', media_category="tweet_video")

    print(upload_result)

    twitter_API_v2.create_tweet(
        text="🎬 [Top 5 clips da semana]",
        media_ids=[upload_result.media_id])
