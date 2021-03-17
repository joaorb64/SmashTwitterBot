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

def update_events_file():
  with open('events.json', 'w') as outfile:
    json.dump(events_json, outfile, indent=4)

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

f = open('events.json')
events_json = json.load(f)

f = requests.get("https://api.smash.gg/characters?videogameId=1386")
characters_json = json.loads(f.text)["entities"]

r = requests.post(
  'https://api.smash.gg/gql/alpha',
  headers={
    'Authorization': 'Bearer'+SMASHGG_KEY,
  },
  json={
    'query': '''
      query TournamentsByCountry($cCode: String!, $perPage: Int!) {
        tournaments(query: {
          perPage: $perPage
          filter: {
            countryCode: $cCode
            videogameIds: [1386]
          }
        }) {
          nodes {
            id
            startAt
            events {
              id
              videogame {
                id
              }
              startAt
            }
          }
        }
      },
    ''',
    'variables': {
      "cCode": "BR",
      "perPage": 20
    },
  }
)

resp = json.loads(r.text)
data = resp["data"]["tournaments"]["nodes"]

proximos_eventos = []

for tournament in data:
  r = requests.post(
    'https://api.smash.gg/gql/alpha',
    headers={
      'Authorization': 'Bearer'+SMASHGG_KEY,
    },
    json={
      'query': '''
        query Tournament($tournamentId: ID!) {
          tournament(id: $tournamentId) {
            id
            name
            url
            city
            timezone
            startAt
            endAt
            registrationClosesAt
            venueName
            venueAddress
            addrState
            events {
              id
              name
              isOnline
              state
              numEntrants
              videogame {
                id
              }
              startAt
              phaseGroups {
                id
                phase {
                  id
                  name
                }
                progressionsOut {
                  id
                }
              }
            }
            streams {
              streamName
            }
            images{
              id
              url
              type
            }
          }
        },
      ''',
      'variables': {
        "tournamentId": tournament["id"]
      },
    }
  )
  resp = json.loads(r.text)
  tournament_data = resp["data"]["tournament"]

  smash_ultimate_tournaments = 0

  for event in tournament_data["events"]:
    if event["videogame"]["id"] == 1386:
      smash_ultimate_tournaments += 1

  for event in tournament_data["events"]:
    # Smash Ultimate
    if event["videogame"]["id"] != 1386:
      continue

    if event["startAt"] > time.time():
      event["tournament"] = tournament_data["name"]
      event["tournament_id"] = tournament_data["id"]
      event["city"] = tournament_data["city"]
      event["url"] = "https://smash.gg"+tournament_data["url"]
      event["streams"] = tournament_data["streams"]
      event["timezone"] = tournament_data["timezone"]
      event["tournament_startAt"] = tournament_data["startAt"]
      event["tournament_endAt"] = tournament_data["endAt"]
      event["tournament_registrationClosesAt"] = tournament_data["registrationClosesAt"]
      event["images"] = tournament_data["images"]
      event["tournament_multievent"] = False if smash_ultimate_tournaments <= 1 else True
      event["tournament_venueName"] = tournament_data["venueName"]
      event["tournament_venueAddress"] = tournament_data["venueAddress"]
      event["tournament_addrState"] = tournament_data["addrState"]
      
      proximos_eventos.append(event)

for evento in proximos_eventos:
  if str(evento["id"]) not in events_json.keys():
    print("Novo evento: "+ evento["name"] + " - " + evento["tournament"])

    data_time = datetime.datetime.fromtimestamp(evento["startAt"], tz=pytz.timezone("America/Sao_Paulo"))
    data = data_time.strftime("%d/%m/%Y %H:%M")

    data_registration_time = datetime.datetime.fromtimestamp(evento["tournament_registrationClosesAt"], tz=pytz.timezone("America/Sao_Paulo"))
    data_registration = data_registration_time.strftime("%d/%m/%Y %H:%M")

    torneio_type = "[Torneio Online]" if evento["isOnline"] == True else "[Torneio Offline]"

    torneio_name = evento["tournament"]
    
    if evento["tournament_multievent"]:
      torneio_name += " - " + evento["name"]

    tweet_id = twitter_API.update_status(
      torneio_type + " "+
      torneio_name +" \n"+
      "Início: "+data+" (GMT-3)"+"\n"+
      "Inscrições até: "+data_registration+" (GMT-3)"+"\n"+
      evento["url"]
    )
    time.sleep(1)

    events_json[evento["id"]] = evento
    events_json[evento["id"]]["tweet_id"] = tweet_id["id"]

with open('events.json', 'w') as outfile:
  json.dump(events_json, outfile, indent=4)