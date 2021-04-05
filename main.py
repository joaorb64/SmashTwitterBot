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

f = open('accounts.json')
accounts = json.load(f)

if os.path.exists("auth.json"):
  f = open('auth.json')
  auth_json = json.load(f)
  SMASHGG_KEY = auth_json["SMASHGG_KEY"]

for account in accounts:
  CONSUMER_KEY = auth_json[account]["CONSUMER_KEY"]
  CONSUMER_SECRET = auth_json[account]["CONSUMER_SECRET"]
  ACCESS_KEY = auth_json[account]["ACCESS_KEY"]
  ACCESS_SECRET = auth_json[account]["ACCESS_SECRET"]

  auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
  auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

  twitter_API = tweepy.API(auth, parser=tweepy.parsers.JSONParser())

  try:
    f = open('events_'+account+'.json')
    events_json = json.load(f)
  except:
    events_json = {}

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
        "cCode": accounts[account]["country"],
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
      print(account+" - novo evento: "+ evento["name"] + " - " + evento["tournament"])

      data_time = datetime.datetime.fromtimestamp(evento["startAt"], tz=pytz.timezone(accounts[account]["timezone"]))
      data = data_time.strftime(accounts[account]["timeFormat"])

      data_registration_time = datetime.datetime.fromtimestamp(evento["tournament_registrationClosesAt"], tz=pytz.timezone(accounts[account]["timezone"]))
      data_registration = data_registration_time.strftime(accounts[account]["timeFormat"])

      torneio_type = accounts[account]["text-online-tournament"] if evento["isOnline"] == True else accounts[account]["text-offline-tournament"]

      torneio_name = evento["tournament"]
      
      if evento["tournament_multievent"]:
        torneio_name += " - " + evento["name"]

      tweet_id = twitter_API.update_status(
        torneio_type + " "+
        torneio_name +" \n"+
        accounts[account]["text-tournament-start"]+": "+data+" ("+accounts[account]["timezone"]+")"+"\n"+
        accounts[account]["text-tournament-registration-ends"]+": "+data_registration+" ("+accounts[account]["timezone"]+")"+"\n"+
        evento["url"]
      )
      time.sleep(1)

      events_json[evento["id"]] = evento
      events_json[evento["id"]]["tweet_id"] = tweet_id["id"]

  with open('events_'+account+'.json', 'w') as outfile:
    json.dump(events_json, outfile, indent=4)