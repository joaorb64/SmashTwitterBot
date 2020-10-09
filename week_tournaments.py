import tweepy
import time
import datetime
import requests
import json
import pprint
import datetime
import os
import drawResults
import pytz
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

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

weekdays = {
    0: "SEG",
    1: "TER",
    2: "QUA",
    3: "QUI",
    4: "SEX",
    5: "SÁB",
    6: "DOM",
}

f = open('events.json')
events_json = json.load(f)

events_post = []

for evento in list(events_json):
    if time.time() + datetime.timedelta(days=7).total_seconds() > events_json[evento]["startAt"] and events_json[evento]["state"] != 'ACTIVE' and events_json[evento]["state"] != 'COMPLETE':
        events_post.append(events_json[evento])

def sortByDate(evento):
    return int(evento["startAt"])

events_post.sort(key=sortByDate)

img = Image.new('RGBA', (1024, 64 + (96+4)*len(events_post)), color = (0, 0, 0, 255))
y = 64

fnt = ImageFont.truetype('./smash_font.ttf', 42)
fnt_big = ImageFont.truetype('./smash_font.ttf', 24)
fnt_small = ImageFont.truetype('./smash_font.ttf', 18)

icon_calendar = Image.open("./icons/calendar.png")
icon_marker = Image.open("./icons/marker.png")
icon_registration = Image.open("./icons/registration.png")
icon_wifi = Image.open("./icons/wifi.png")

d = ImageDraw.Draw(img, "RGBA")

d.text((20, 6), "Eventos da semana", font=fnt, fill=(255, 255, 255), align="center")

last_date = ""

for evento in events_post:
    # Dia
    data_time = datetime.datetime.fromtimestamp(evento["startAt"], tz=pytz.timezone("America/Sao_Paulo"))
    day = data_time.strftime("%d/%m")

    if last_date != day:
        d.rectangle((2, y, 4+96, y+96), (55, 55, 55, 255))

        weekday = weekdays[data_time.weekday()]
        w, h = d.textsize(weekday, font=fnt_big)
        d.text(((4+96)/2.0 - w/2.0, y+16), weekday, font=fnt_big, fill=(255, 255, 255), align="center")

        w, h = d.textsize(day, font=fnt_big)
        d.text(((4+96)/2.0 - w/2.0, y+48), day, font=fnt_big, fill=(255, 255, 255), align="center")

        last_date = day

    # Torneio
    d.rectangle((104, y, 1020, y+96), (55, 55, 55, 255))

    bannerUrl = next((i["url"] for i in evento["images"] if i["type"] == "banner"), None)
  
    if bannerUrl == None:
        evento["images"][-1]["url"]
  
    if bannerUrl == None:
        bannerUrl = "https://raw.githubusercontent.com/joaorb64/SmashTwitterBot/master/media_generic.png"

    response = requests.get(bannerUrl)
    
    banner = Image.open(BytesIO(response.content)).convert("RGBA")
    banner_w, banner_h = banner.size

    goal_w = 256
    goal_h = 96
    goal_proportion = goal_w/goal_h
    banner_proportion = banner_w/banner_h

    if banner_proportion < goal_proportion:
        banner = banner.resize((256, int(256/banner_w*banner_h)), Image.ANTIALIAS)
        banner_w, banner_h = banner.size
        banner = banner.crop((0, (banner_h-96)/2, 256, 96+(banner_h-96)/2))
    else:
        banner = banner.resize((int(96/banner_h*banner_w), 96), Image.ANTIALIAS)
    
    banner = banner.crop((0,0,256,96))
  
    banner_w, banner_h = banner.size
    
    img.paste(banner, (104+int(256/2-banner_w/2), y))
    
    post = ""
    
    post += evento["tournament"]

    if evento["tournament_multievent"]:
        post += " - " + evento["name"]

    d.text((104+256+8, y+2), post, font=fnt_big, fill=(255, 255, 255), align="center")

    location = ""

    if evento["isOnline"]:
        location = "Online"
        img.alpha_composite(icon_wifi, (104+256+8, y+2+30))
    else:
        location = evento["tournament_venueName"] + " - "
        location += ",".join(evento["tournament_venueAddress"].split(",")[0:3])
        img.alpha_composite(icon_marker, (104+256+8, y+2+30))

    d.text((104+256+24+8, y+2+30), location, font=fnt_small, fill=(255, 255, 255), align="center")

    data_time = datetime.datetime.fromtimestamp(evento["startAt"], tz=pytz.timezone("America/Sao_Paulo"))
    data = data_time.strftime("%d/%m %H:%M")

    data_registration_time = datetime.datetime.fromtimestamp(evento["tournament_registrationClosesAt"], tz=pytz.timezone("America/Sao_Paulo"))
    data_registration = data_registration_time.strftime("%d/%m %H:%M")

    img.alpha_composite(icon_calendar, (104+256+8, y+2+52))
    d.text((104+256+24+8, y+2+52), "Inicia "+data, font=fnt_small, fill=(255, 255, 255), align="center")

    img.alpha_composite(icon_registration, (104+256+8, y+2+74))
    d.text((104+256+24+8, y+2+74), "Inscrições até "+data_registration, font=fnt_small, fill=(255, 255, 255), align="center")

    y+=96+4

img.save('media.png')

twitter_API.update_with_media("./media.png", status="Eventos da semana\nConfira os eventos em https://www.powerrankings.com.br/#/nexttournaments/")