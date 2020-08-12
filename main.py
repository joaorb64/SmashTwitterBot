import tweepy
import time
import requests
import json
import pprint
import datetime
import os

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

twitter_API = tweepy.API(auth)

f = open('events.json')
events_json = json.load(f)

# Deletar eventos passados, se nao standings
for evento in list(events_json):
  r = requests.post(
    'https://api.smash.gg/gql/alpha',
    headers={
      'Authorization': 'Bearer'+SMASHGG_KEY,
    },
    json={
      'query': '''
        query EventStandings($eventId: ID!, $page: Int!, $perPage: Int!) {
          event(id: $eventId) {
            state
            standings(query: {
              perPage: $perPage,
              page: $page
            }){
              nodes {
                placement
                entrant {
                  id
                  name
                  participants{
                    user{
                      authorizations(types: [TWITTER]) {
                        externalUsername
                      }
                    }
                  }
                }
              }
            }
          }
        },
      ''',
      'variables': {
        "eventId": events_json[evento]["id"],
        "page": 1,
        "perPage": 8
      },
    }
  )
  resp = json.loads(r.text)
  data = resp["data"]["event"]
  time.sleep(1)

  if data["state"] == 'COMPLETED':
    post = "[Resultados]"
    post += "[Online]" if events_json[evento].get("isOnline") else "[Offline]"
    post += " " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"] + "\n"
    
    for entrant in data["standings"]["nodes"]:
      post += str(entrant["placement"]) + " " + entrant["entrant"]["name"]
      twitter = entrant.get("entrant").get("participants")[0].get("user").get("authorizations")#[0].get("externalUsername")
      if twitter:
        post += " @" + str(twitter[0].get("externalUsername"))
      post += "\n"

    twitter_API.update_status(post)

    events_json.pop(evento)


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
          }
        }) {
          nodes {
            id
            name
            url
            city
            events {
              id
              name
              isOnline
              state
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
      "perPage": 50
    },
  }
)

resp = json.loads(r.text)
data = resp["data"]["tournaments"]["nodes"]

proximos_eventos = []

for tournament in data:
  for event in tournament["events"]:
    # Smash Ultimate
    if event["videogame"]["id"] != 1386:
      continue

    if event["startAt"] > time.time():
      event["tournament"] = tournament["name"]
      event["tournament_id"] = tournament["id"]
      event["city"] = tournament["city"]
      event["url"] = "https://smash.gg"+tournament["url"]
      proximos_eventos.append(event)

for evento in proximos_eventos:
  if str(evento["id"]) not in events_json.keys():
    data_time = datetime.datetime.fromtimestamp(evento["startAt"]) - datetime.timedelta(hours=1)
    data = data_time.strftime("%d/%m/%Y %H:%M (GMT-3)")

    torneio_type = "[Torneio Online]" if evento["isOnline"] == True else "[Torneio Offline]"

    twitter_API.update_status(
      torneio_type+" "+
      evento["tournament"]+" - "+evento["name"]+"\n"+
      "Início: "+data+"\n"+
      evento["url"]
    )
    time.sleep(1)

    events_json[evento["id"]] = evento

with open('events.json', 'w') as outfile:
  json.dump(events_json, outfile, indent=4)

#pprint.pprint(list(filter(filterTournaments, data)))

#twitter_API.update_status('Hello world!')