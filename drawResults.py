from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import datetime

def drawResults(event, standings):

  img = Image.new('RGBA', (512, 570), color = (255, 255, 255))

  response = requests.get(next(i["url"] for i in event["images"] if i["type"] == "banner"))
  banner = Image.open(BytesIO(response.content)).convert("RGBA")
  banner_w, banner_h = banner.size
  banner = banner.resize((512, int(512/banner_w*banner_h)), Image.ANTIALIAS)
  banner_w, banner_h = banner.size
  banner = banner.crop((0, (banner_h-260)/2, 512, 240-(banner_h-260)/2))
  
  img.alpha_composite(banner, (int(512/2-banner_w/2), 0))

  fnt = ImageFont.truetype('./smash_font.ttf', 16)
  d = ImageDraw.Draw(img)
  title_text = event["tournament"] + "\n" + event["name"] + "\n"
  title_text += ("Online" if event.get("isOnline") else "Offline") + " - "

  title_text += str(standings.get("numEntrants")) + " participantes"

  if event["city"]:
    title_text += " - "+event["city"]

  data_time = datetime.datetime.fromtimestamp(event["startAt"])
  data = data_time.strftime("%d/%m/%Y")

  title_text += " - " + data

  w, h = d.textsize(title_text, font=fnt)
  d.text((256-w/2,220), title_text, font=fnt, fill=(0, 0, 0), align="center")

  pos_y = 286

  fnt_results = ImageFont.truetype('./smash_font.ttf', 24)

  for entrant in standings["standings"]["nodes"]:
    entry_text = str(entrant["placement"]) + ". " + entrant["entrant"]["name"]
    w, h = d.textsize(entry_text, font=fnt_results)
    d.text((20,pos_y), entry_text, font=fnt_results, fill=(0, 0, 0), align="left")

    if entrant.get("char_usage"):
        for char in entrant.get("char_usage").items():
          response = requests.get(char[1]["icon"])
          icon = Image.open(BytesIO(response.content)).convert("RGBA")
          icon = icon.resize((32, 32), Image.ANTIALIAS)
          img.alpha_composite(icon, (20+w+4, pos_y-4))
          w+=32

    pos_y += 32
  
  d.text((20,550), "Gerado por @smash_bot_br usando dados do smash.gg", font=fnt, fill=(0, 0, 0), align="center")

  img.save('media.png')