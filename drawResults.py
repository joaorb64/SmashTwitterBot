from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import datetime

def drawResults(event, standings, page=1):
  is_top16 = standings.get("standings").get("pageInfo").get("total") >= 64

  img = Image.new('RGBA', (512, 512), color = (255, 255, 255, 255))

  response = requests.get(event["images"][-1]["url"])
  
  banner = Image.open(BytesIO(response.content)).convert("RGBA")
  banner_w, banner_h = banner.size

  goal_w = 512
  goal_h = 220
  goal_proportion = goal_w/goal_h
  banner_proportion = banner_w/banner_h

  if banner_proportion < goal_proportion:
    banner = banner.resize((512, int(512/banner_w*banner_h)), Image.ANTIALIAS)
    banner_w, banner_h = banner.size
    banner = banner.crop((0, (banner_h-220)/2, 512, 220+(banner_h-220)/2))
  else:
    banner = banner.resize((int(220/banner_h*banner_w), 220), Image.ANTIALIAS)
  
  banner_w, banner_h = banner.size
  
  img.paste(banner, (int(512/2-banner_w/2), 0))

  fnt = ImageFont.truetype('./smash_font.ttf', 16)
  d = ImageDraw.Draw(img, "RGBA")

  if standings.get("multiphase"):
    black_bg_top = Image.open("./black_bg_top.png")
  else:
    black_bg_top = Image.open("./black_bg_bottom.png")

  img.alpha_composite(black_bg_top, (0, 0))

  black_bg_bottom = Image.open("./black_bg_bottom.png")
  img.alpha_composite(black_bg_bottom, (0, 198))

  title_text_top = event["tournament"]
  
  if event["tournament_multievent"]:
    title_text_top += " - "+event["name"]
  
  if standings.get("multiphase"):
    title_text_top += "\n"+standings.get("phase").get("name")

  w, h = d.textsize(title_text_top, font=fnt)
  d.text((256-w/2,2), title_text_top, font=fnt, fill=(255, 255, 255), align="center")

  title_text_bottom = ("Online" if event.get("isOnline") else "Offline") + " - "
  title_text_bottom += str(standings.get("standings").get("pageInfo").get("total")) + " participantes"

  if event["city"]:
    title_text_bottom += " - "+event["city"]

  data_time = datetime.datetime.fromtimestamp(event["startAt"])
  data = data_time.strftime("%d/%m/%y")

  title_text_bottom += " - " + data

  w, h = d.textsize(title_text_bottom, font=fnt)
  d.text((256-w/2,200), title_text_bottom, font=fnt, fill=(255, 255, 255), align="center")

  pos_y = 230

  fnt_results = ImageFont.truetype('./smash_font.ttf', 24)

  for entrant in standings["standings"]["nodes"][((8*(page-1))+0):((8*(page-1))+8)]:
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
  
  d.rectangle((0, 490, 512, 512), (0,0,0))
  d.text((20, 493), "Gerado por @smash_bot_br usando dados do smash.gg", font=fnt, fill=(255, 255, 255), align="center")

  if is_top16:
    d.text((512-40, 493), str(page)+"/2", font=fnt, fill=(255, 255, 255), align="center")

  img.save('media.png' if page==1 else 'media2.png')

  if is_top16 and page == 1:
    drawResults(event, standings, page=2)