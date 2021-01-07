import time
import datetime
import dateutil.parser
import requests
import json
import pprint
import datetime
import os
import pytz
import urllib
from moviepy.editor import *
from PIL import Image, ImageDraw, ImageFont

os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"

if os.path.exists("auth.json"):
  f = open('auth.json')
  auth_json = json.load(f)

  CONSUMER_KEY = auth_json["CONSUMER_KEY"]
  CONSUMER_SECRET = auth_json["CONSUMER_SECRET"]
  ACCESS_KEY = auth_json["ACCESS_KEY"]
  ACCESS_SECRET = auth_json["ACCESS_SECRET"]
  SMASHGG_KEY = auth_json["SMASHGG_KEY"]
else:
  CONSUMER_KEY = os.environ.get("CONSUMER_KEY")
  CONSUMER_SECRET = os.environ.get("CONSUMER_SECRET")
  ACCESS_KEY = os.environ.get("ACCESS_KEY")
  ACCESS_SECRET = os.environ.get("ACCESS_SECRET")
  SMASHGG_KEY = os.environ.get("SMASHGG_KEY")

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

twitter_API = tweepy.API(auth, parser=tweepy.parsers.JSONParser())

clips = requests.get("https://raw.githubusercontent.com/joaorb64/tournament_api/sudamerica/out/twitchclips.json").json()

def DownloadClips():
    myClips = []

    brClips = clips.get("pt-br", [])

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
        mp4_url = thumb_url.split("-preview",1)[0] + ".mp4"
        output_path = "clips/"+ str(i) + ".mp4"

        def dl_progress(count, block_size, total_size):
            percent = int(count * block_size * 100 / total_size)
            print("Downloading clip "+str(i)+"...%d%%" % percent, end="\r")
            if percent == 100:
                print("")

        # create the basepath directory
        if not os.path.exists("clips"):
            os.makedirs("clips")

        try:
            urllib.request.urlretrieve(mp4_url, output_path, reporthook=dl_progress)
        except:
            print("An exception occurred")
        
        img = Image.new('RGBA', (1280, 720), color = (214, 214, 214, 255))
        d = ImageDraw.Draw(img, "RGBA")

        fnt_big = ImageFont.truetype('./smash_font.ttf', 40)
        fnt = ImageFont.truetype('./smash_font.ttf', 26)

        # topo
        d.rectangle((0, 0, 1280, 50), (49, 49, 49, 255))
        
        w, h = d.textsize(clip["title"], font=fnt_big)
        d.text((640-w/2,5), clip["title"], font=fnt_big, fill=(255, 255, 255), align="center")

        # rodape
        d.rectangle((0, 720-64, 1280, 720), (49, 49, 49, 255))

        # canal
        d.text((32,720-64), "Canal: "+clip["broadcaster_name"], font=fnt, fill=(255, 255, 255))

        # clippado por
        d.text((32,720-32), "Clip: "+clip["creator_name"], font=fnt, fill=(255, 255, 255))

        # view_count
        view_count = str(clip["view_count"]) + " views"
        w, h = d.textsize(view_count, font=fnt)
        d.text((1280-32-w,720-64), view_count, font=fnt, fill=(255, 255, 255))

        # bot
        bot_text = "Vídeo gerado por @smash_bot_br"
        w, h = d.textsize(bot_text, font=fnt)
        d.text((1280-32-w,720-32), "Vídeo gerado por @smash_bot_br", font=fnt, fill=(255, 255, 255))

        img.save("clips/overlay.png")
        
        edit_clip = VideoFileClip("clips/"+str(i)+".mp4")
        edit_clip = edit_clip.resize(height=720-51-64)
        edit_clip = edit_clip.set_position(("center", 51))

        overlay = ImageClip("clips/overlay.png", transparent=True, duration=edit_clip.duration)
        overlay.set_position((0, 0))

        video = CompositeVideoClip([overlay, edit_clip])
        video.write_videofile("clips/"+str(i)+"_edited.mp4", preset='ultrafast', codec='libx264', audio_codec="aac", threads=4)
    
    final = concatenate_videoclips([VideoFileClip("clips/"+str(i)+"_edited.mp4") for i, clip in enumerate(myClips)])
    final.write_videofile("clips/final.mp4", preset='ultrafast', codec='libx264', audio_codec="aac", threads=4)

DownloadClips()
twitter_API.update_with_media("./clips/final.mp4", status="🎞️ [Top 5 clips da semana]\nConfira todos os clips no PowerRankings: https://powerrankings.gg/clips/pt-br")