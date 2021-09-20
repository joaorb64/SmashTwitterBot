from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import datetime
import os

def drawResults(event, standings, account):
  img = Image.new('RGBA', (1280, 720), color = (255, 255, 255, 255))
  results_template = Image.open('./results_template.png', 'r').convert("RGBA")
  player_bg = Image.open('./results_player.png', 'r').convert("RGBA")

  bannerUrl = None
  banner = None

  if event.get("images", None) is not None:
    bannerUrl = next((i["url"] for i in event["images"] if i["type"] == "banner"), None)
  
    if bannerUrl == None:
      event["images"][-1]["url"]
    
  if bannerUrl != None:
    response = requests.get(bannerUrl)
    banner = Image.open(BytesIO(response.content)).convert("RGBA")
  else:
    banner = Image.open("banner/"+account["game"]+".png").convert("RGBA")

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
  
  if len(title_text_top) > 80:
    title_text_top = title_text_top[:80]+"…"

  w, h = d.textsize(title_text_top, font=fnt_top)
  d.text((640-w/2,0), title_text_top, font=fnt_top, fill=(255, 255, 255), align="center")

  if standings.get("multiphase"):
    phase_text = standings.get("phase").get("name")
    w, h = d.textsize(phase_text, font=fnt_top)

    d.rectangle(((640-w/2-16, 48), (640+w/2+16, 48+h+6)), fill=(45, 45, 45))
    d.text((640-w/2,48), phase_text, font=fnt_top, fill=(255, 255, 255), align="center")

  fnt = ImageFont.truetype('./smash_font.ttf', 32)

  # Location if applies
  location = ""
  if event.get("tournament_venueName") or event.get("tournament_venueAddress"):
    if event.get("tournament_venueName"):
      location += event.get("tournament_venueName")+", "
    
    if event.get("tournament_venueAddress"):
      splitted = event.get("tournament_venueAddress").split(",")
      if len(splitted) >= 3:
        location += splitted[-3]+", "+splitted[-2]

  title_text_bottom = ("Online" if event.get("isOnline") else location) + " - "
  title_text_bottom += str(standings.get("standings").get("pageInfo").get("total")) + " " + account["text-results-participants"]

  data_time = datetime.datetime.fromtimestamp(event["startAt"])
  data = data_time.strftime(account["text-results-timeformat"])

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

    # Cut out giantic names
    if w > 400:
      while w > 400:
        entry_text = entry_text[0:-1]
        w, h = d.textsize(entry_text+"…", font=fnt_results)
      entry_text += "…"

    d.text((pos_x+18,pos_y+6), entry_text, font=fnt_results, fill=(43, 43, 43), align="left")

    load_local_portraits = False
    if os.path.exists("./portraits/"+account["game"]):
      load_local_portraits = True

    if entrant.get("char_usage"):
      chars_width = 42 * min(len(entrant.get("char_usage")), 4) - 42
      for j, char in enumerate(entrant.get("char_usage").items()):
        icon = None

        try:
          if not load_local_portraits:
            response = requests.get(char[1]["icon"])
            icon = Image.open(BytesIO(response.content)).convert("RGBA")
          else:
            icon = Image.open("./portraits/"+account["game"]+"/"+char[1]["name"]+".png").convert("RGBA")
            
          icon = icon.resize((42, 42), Image.ANTIALIAS)
          img.alpha_composite(icon, (pos_x+540-chars_width+42*j, pos_y+4))
        except Exception as e:
          print("No character icon?")
          print(e)

        if j==2 and len(entrant.get("char_usage")) > 4:
          d.text((pos_x+540,pos_y+6), "+"+str(len(entrant.get("char_usage"))-3), font=fnt_results, fill=(43, 43, 43), align="left")
          break
    
    if entrant.get("dq"):
      d.text((pos_x+540,pos_y+6), "DQ", font=fnt_results, fill=(43, 43, 43), align="left")

    pos_y += 56

    if(i == 3):
      pos_y = 455
      pos_x = 655
  
  fnt_footer = ImageFont.truetype('./smash_font.ttf', 24)
  d.text((20, 686), account["text-results-generated-by-before"]+" @"+account["handle"]+" "+account["text-results-generated-by-after"], font=fnt_footer, fill=(255, 255, 255), align="center")

  img.save('media.png')

def drawResults8x9(event, standings, account, page=1):
  img = Image.new('RGBA', (640, 720), color = (255, 255, 255, 255))
  results_template = Image.open('./results_template8x9.png', 'r').convert("RGBA")
  player_bg = Image.open('./results_player.png', 'r').convert("RGBA")
  player_bg = player_bg.crop((0, 0, 590, 48))

  bannerUrl = None
  banner = None

  if event.get("images", None) is not None:
    bannerUrl = next((i["url"] for i in event["images"] if i["type"] == "banner"), None)
  
    if bannerUrl == None:
      event["images"][-1]["url"]
    
  if bannerUrl != None:
    response = requests.get(bannerUrl)
    banner = Image.open(BytesIO(response.content)).convert("RGBA")
  else:
    banner = Image.open("banner/"+account["game"]+".png").convert("RGBA")
  
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

    d.rectangle(((320-w/2-16, 48), (320+w/2+16, 48+h+6)), fill=(43, 43, 43))
    d.text((320-w/2,48), phase_text, font=fnt_top, fill=(255, 255, 255), align="center")

  fnt = ImageFont.truetype('./smash_font.ttf', 22)

  # Location if applies
  location = ""
  if event.get("tournament_venueName") or event.get("tournament_venueAddress"):
    if event.get("tournament_venueName"):
      location += event.get("tournament_venueName")+", "
    
    if event.get("tournament_venueAddress"):
      splitted = event.get("tournament_venueAddress").split(",")
      if len(splitted) >= 3:
        location += splitted[-3]+", "+splitted[-2]

  title_text_bottom = ("Online" if event.get("isOnline") else location) + " - "
  title_text_bottom += str(standings.get("standings").get("pageInfo").get("total")) + " " + account["text-results-participants"]

  data_time = datetime.datetime.fromtimestamp(event["startAt"])
  data = data_time.strftime(account["text-results-timeformat"])

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

    # Cut out giantic names
    if w > 400:
      while w > 400:
        entry_text = entry_text[0:-1]
        w, h = d.textsize(entry_text+"…", font=fnt_results)
      entry_text += "…"

    d.text((pos_x+18,pos_y+8), entry_text, font=fnt_results, fill=(43, 43, 43), align="left")

    load_local_portraits = False
    if os.path.exists("./portraits/"+account["game"]):
      load_local_portraits = True

    if entrant.get("char_usage"):
      chars_width = 42 * min(len(entrant.get("char_usage")), 4) - 42
      for j, char in enumerate(entrant.get("char_usage").items()):
        icon = None

        try:
          if not load_local_portraits:
            response = requests.get(char[1]["icon"])
            icon = Image.open(BytesIO(response.content)).convert("RGBA")
          else:
            icon = Image.open("./portraits/"+account["game"]+"/"+char[1]["name"]+".png").convert("RGBA")

          icon = icon.resize((42, 42), Image.ANTIALIAS)
          img.alpha_composite(icon, (pos_x+540-chars_width+42*j, pos_y+4))
        except Exception as e:
          print("No character icon?")
          print(e)

        if j==2 and len(entrant.get("char_usage")) > 4:
          d.text((pos_x+540+6,pos_y+12), "+"+str(len(entrant.get("char_usage"))-3), font=fnt_results, fill=(43, 43, 43), align="left")
          break
    
    if entrant.get("dq"):
      d.text((pos_x+540+6,pos_y+12), "DQ", font=fnt_results, fill=(43, 43, 43), align="left")

    pos_y += 52
  
  fnt_footer = ImageFont.truetype('./smash_font.ttf', 20)
  d.text((10, 691), account["text-results-generated-by-before"]+" @"+account["handle"]+" "+account["text-results-generated-by-after"], font=fnt_footer, fill=(255, 255, 255), align="center")

  d.text((640-40, 690), str(page)+"/2", font=fnt, fill=(255, 255, 255), align="center")

  img.save('media.png' if page==1 else 'media2.png')

  if page == 1:
    drawResults8x9(event, standings, account, page=2)
