from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import datetime

def drawResults(event, standings):
  img = Image.new('RGBA', (1280, 720), color = (255, 255, 255, 255))
  results_template = Image.open('./results_template.png', 'r').convert("RGBA")
  player_bg = Image.open('./results_player.png', 'r').convert("RGBA")

  bannerUrl = next((i["url"] for i in event["images"] if i["type"] == "banner"), None)
  
  if bannerUrl == None:
    event["images"][-1]["url"]
  
  if bannerUrl == None:
    bannerUrl = "https://raw.githubusercontent.com/joaorb64/SmashTwitterBot/master/media_generic.png"

  response = requests.get(bannerUrl)
  
  banner = Image.open(BytesIO(response.content)).convert("RGBA")
  banner_w, banner_h = banner.size

  goal_w = 1280
  goal_h = 360
  goal_proportion = goal_w/goal_h
  banner_proportion = banner_w/banner_h

  if banner_proportion < goal_proportion:
    banner = banner.resize((goal_w, int(goal_w/banner_w*banner_h)), Image.ANTIALIAS)
    banner_w, banner_h = banner.size
    banner = banner.crop((0, (banner_h-goal_h)/2, goal_w, goal_h+(banner_h-goal_h)/2))
  else:
    banner = banner.resize((int(goal_h/banner_h*banner_w), goal_h), Image.ANTIALIAS)
  
  banner_w, banner_h = banner.size
  
  img.paste(banner, (int(goal_w/2-banner_w/2), 48))

  img.alpha_composite(results_template)

  fnt_top = ImageFont.truetype('./smash_font.ttf', 42)
  d = ImageDraw.Draw(img, "RGBA")

  title_text_top = event["tournament"]
  
  if event["tournament_multievent"]:
    title_text_top += " - "+event["name"]

  w, h = d.textsize(title_text_top, font=fnt_top)
  d.text((640-w/2,0), title_text_top, font=fnt_top, fill=(255, 255, 255), align="center")

  if standings.get("multiphase"):
    phase_text = standings.get("phase").get("name")
    w, h = d.textsize(phase_text, font=fnt_top)

    d.rectangle(((640-w/2-16, 48), (640+w/2+16, 48+h+6)), fill=(0, 0, 0))
    d.text((640-w/2,48), phase_text, font=fnt_top, fill=(255, 255, 255), align="center")

  fnt = ImageFont.truetype('./smash_font.ttf', 32)

  title_text_bottom = ("Online" if event.get("isOnline") else "Offline") + " - "
  title_text_bottom += str(standings.get("standings").get("pageInfo").get("total")) + " participantes"

  if event["city"]:
    title_text_bottom += " - "+event["city"]

  data_time = datetime.datetime.fromtimestamp(event["startAt"])
  data = data_time.strftime("%d/%m/%y")

  title_text_bottom += " - " + data

  w, h = d.textsize(title_text_bottom, font=fnt)
  d.text((640-w/2,408), title_text_bottom, font=fnt, fill=(255, 255, 255), align="center")

  pos_y = 455
  pos_x = 40

  fnt_results = ImageFont.truetype('./smash_font.ttf', 32)

  for i, entrant in enumerate(standings["standings"]["nodes"][0:8]):
    img.paste(player_bg, (pos_x, pos_y))

    entry_text = str(entrant["placement"]) + ". " + entrant["entrant"]["name"]
    w, h = d.textsize(entry_text, font=fnt_results)
    d.text((pos_x+18,pos_y+6), entry_text, font=fnt_results, fill=(255, 255, 255), align="left")

    if entrant.get("char_usage"):
      chars_width = 42 * len(entrant.get("char_usage")) - 42
      for j, char in enumerate(entrant.get("char_usage").items()):
        response = requests.get(char[1]["icon"])
        icon = Image.open(BytesIO(response.content)).convert("RGBA")
        icon = icon.resize((42, 42), Image.ANTIALIAS)
        img.alpha_composite(icon, (pos_x+540-chars_width+42*j, pos_y+4))

    pos_y += 56

    if(i == 3):
      pos_y = 455
      pos_x = 655
  
  fnt_footer = ImageFont.truetype('./smash_font.ttf', 24)
  d.text((20, 686), "Gerado por @smash_bot_br usando dados do smash.gg", font=fnt_footer, fill=(255, 255, 255), align="center")

  img.save('media.png')

def drawResults8x9(event, standings, page=1):
  img = Image.new('RGBA', (640, 720), color = (255, 255, 255, 255))
  results_template = Image.open('./results_template8x9.png', 'r').convert("RGBA")
  player_bg = Image.open('./results_player.png', 'r').convert("RGBA")
  player_bg = player_bg.crop((0, 0, 590, 48))

  bannerUrl = next((i["url"] for i in event["images"] if i["type"] == "banner"), None)
  
  if bannerUrl == None:
    event["images"][-1]["url"]
  
  if bannerUrl == None:
    bannerUrl = "https://raw.githubusercontent.com/joaorb64/SmashTwitterBot/master/media_generic.png"

  response = requests.get(bannerUrl)
  
  banner = Image.open(BytesIO(response.content)).convert("RGBA")
  banner_w, banner_h = banner.size

  goal_w = 640
  goal_h = 180
  goal_proportion = goal_w/goal_h
  banner_proportion = banner_w/banner_h

  if banner_proportion < goal_proportion:
    banner = banner.resize((goal_w, int(goal_w/banner_w*banner_h)), Image.ANTIALIAS)
    banner_w, banner_h = banner.size
    banner = banner.crop((0, (banner_h-goal_h)/2, goal_w, goal_h+(banner_h-goal_h)/2))
  else:
    banner = banner.resize((int(goal_h/banner_h*banner_w), goal_h), Image.ANTIALIAS)
  
  banner_w, banner_h = banner.size
  
  img.paste(banner, (int(goal_w/2-banner_w/2), 48))

  img.alpha_composite(results_template)

  fnt_top = ImageFont.truetype('./smash_font.ttf', 24)
  d = ImageDraw.Draw(img, "RGBA")

  title_text_top = event["tournament"]
  
  if event["tournament_multievent"]:
    title_text_top += " - "+event["name"]

  w, h = d.textsize(title_text_top, font=fnt_top)
  d.text((320-w/2,8), title_text_top, font=fnt_top, fill=(255, 255, 255), align="center")

  if standings.get("multiphase"):
    phase_text = standings.get("phase").get("name")
    w, h = d.textsize(phase_text, font=fnt_top)

    d.rectangle(((320-w/2-16, 48), (320+w/2+16, 48+h+6)), fill=(0, 0, 0))
    d.text((320-w/2,48), phase_text, font=fnt_top, fill=(255, 255, 255), align="center")

  fnt = ImageFont.truetype('./smash_font.ttf', 22)

  title_text_bottom = ("Online" if event.get("isOnline") else "Offline") + " - "
  title_text_bottom += str(standings.get("standings").get("pageInfo").get("total")) + " participantes"

  if event["city"]:
    title_text_bottom += " - "+event["city"]

  data_time = datetime.datetime.fromtimestamp(event["startAt"])
  data = data_time.strftime("%d/%m/%y")

  title_text_bottom += " - " + data

  w, h = d.textsize(title_text_bottom, font=fnt)
  d.text((320-w/2,234), title_text_bottom, font=fnt, fill=(255, 255, 255), align="center")

  pos_y = 270
  pos_x = 25

  fnt_results = ImageFont.truetype('./smash_font.ttf', 24)

  for i, entrant in enumerate(standings["standings"]["nodes"][((8*(page-1))+0):((8*(page-1))+8)]):
    img.paste(player_bg, (pos_x, pos_y))

    entry_text = str(entrant["placement"]) + ". " + entrant["entrant"]["name"]
    w, h = d.textsize(entry_text, font=fnt_results)
    d.text((pos_x+18,pos_y+8), entry_text, font=fnt_results, fill=(255, 255, 255), align="left")

    if entrant.get("char_usage"):
      chars_width = 42 * len(entrant.get("char_usage")) - 42
      for j, char in enumerate(entrant.get("char_usage").items()):
        response = requests.get(char[1]["icon"])
        icon = Image.open(BytesIO(response.content)).convert("RGBA")
        icon = icon.resize((42, 42), Image.ANTIALIAS)
        img.alpha_composite(icon, (pos_x+540-chars_width+42*j, pos_y+3))

    pos_y += 52
  
  fnt_footer = ImageFont.truetype('./smash_font.ttf', 20)
  d.text((10, 691), "Gerado por @smash_bot_br usando dados do smash.gg", font=fnt_footer, fill=(255, 255, 255), align="center")

  d.text((640-40, 690), str(page)+"/2", font=fnt, fill=(255, 255, 255), align="center")

  img.save('media.png' if page==1 else 'media2.png')

  if page == 1:
    drawResults8x9(event, standings, page=2)