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

d = ImageDraw.Draw(img, "RGBA")

d.text((20, 6), "Eventos da semana", font=fnt, fill=(255, 255, 255), align="center")

for evento in events_post:
    # Dia
    d.rectangle((2, y, 4+96, y+96), (55, 55, 55, 255))
    
    data_time = datetime.datetime.fromtimestamp(evento["startAt"], tz=pytz.timezone("America/Sao_Paulo"))

    weekday = weekdays[data_time.weekday()]
    w, h = d.textsize(weekday, font=fnt_big)
    d.text(((4+96)/2.0 - w/2.0, y+16), weekday, font=fnt_big, fill=(255, 255, 255), align="center")

    day = data_time.strftime("%d/%m")
    w, h = d.textsize(day, font=fnt_big)
    d.text(((4+96)/2.0 - w/2.0, y+48), day, font=fnt_big, fill=(255, 255, 255), align="center")

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

    d.text((104+256+8, y+4), post, font=fnt_big, fill=(255, 255, 255), align="center")

    location = ""

    if evento["isOnline"]:
        location = "Online"

    d.text((104+256+8, y+4+32), location, font=fnt_small, fill=(255, 255, 255), align="center")

    data_time = datetime.datetime.fromtimestamp(evento["startAt"], tz=pytz.timezone("America/Sao_Paulo"))
    data = data_time.strftime("%d/%m/%Y %H:%M")

    data_registration_time = datetime.datetime.fromtimestamp(evento["tournament_registrationClosesAt"], tz=pytz.timezone("America/Sao_Paulo"))
    data_registration = data_registration_time.strftime("%d/%m/%Y %H:%M")

    d.text((104+256+8, y+4+56), data, font=fnt_small, fill=(255, 255, 255), align="center")
    
    y+=96+4
img.save('media.png')