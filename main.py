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

f = open('ultimate.json')
characters_json = json.load(f)

# Deletar eventos passados, se nao standings, mensagem de inicio de torneio
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
                    player {
                      id
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
    for entrant in data["standings"]["nodes"]:
      r = requests.post(
        'https://api.smash.gg/gql/alpha',
        headers={
          'Authorization': 'Bearer'+SMASHGG_KEY,
        },
        json={
          'query': '''
            query PlayerSetsInEvent($eventId: ID!) {
              event(id: $eventId) {
                sets(
                  page: 1,
                  perPage: 200,
                  filters: {entrantIds: ''' + str(entrant["entrant"]["id"]) + '''},
                ) {
                  nodes {
                    games {
                      selections {
                        entrant {
                          id
                        }
                        selectionValue
                      }
                    }
                  }
                }
              }
            },
          ''',
          'variables': {
            "eventId": events_json[evento]["id"]
          },
        }
      )
      resp = json.loads(r.text)
      char_data = resp["data"]["event"]["sets"]["nodes"]

      char_usage = {}

      for game in char_data:
        if game.get("games"):
          for selection in game.get("games"):
            for selection_entry in selection.get("selections"):
              if selection_entry["entrant"]["id"] == entrant["entrant"]["id"]:
                if selection_entry["selectionValue"] not in char_usage.keys():
                  char_usage[selection_entry["selectionValue"]] = 1
                else:
                  char_usage[selection_entry["selectionValue"]] += 1
      
      char_usage = {k: v for k, v in sorted(char_usage.items(), key=lambda item: item[1], reverse=True)}

      char_usage_named = {}

      for char in char_usage.items():
        char_in_json = next((c for c in characters_json["character"] if c["id"] == char[0]), None)

        if char_in_json:
          char_usage_named[char_in_json["name"]] = char[1]

      entrant["char_usage"] = char_usage_named

    post = "🏆[Resultados]"
    post += "[Online]" if events_json[evento].get("isOnline") else "[Offline]"
    post += " " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"] + "\n"
    post += events_json[evento].get("url")+"\n"
    
    for entrant in data["standings"]["nodes"]:
      post += str(entrant["placement"]) + " " + entrant["entrant"]["name"]

      if entrant.get("char_usage"):
        post += (" (")
        first = True
        for char in entrant.get("char_usage").items():
          if not first: post+=", "
          post+= char[0]
          first = False
        post += ")"

      twitter = entrant.get("entrant").get("participants")[0].get("user").get("authorizations")
      if twitter:
        post += " @" + str(twitter[0].get("externalUsername"))
      post += "\n"

    status = twitter_API.update_status("\n".join(post.splitlines()[0:5])+"\n(1/2)")
    time.sleep(10)
    twitter_API.update_status("@smash_bot_br\n"+"\n".join(post.splitlines()[5:10])+"\n(2/2)", in_reply_to_status_id=status.id)

    events_json.pop(evento)
  
  if data["state"] == 'ACTIVE' and events_json[evento]["state"] != 'ACTIVE':
    post = ""
    post+= "Iniciado o torneio " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"] + "!\n"
    
    if events_json[evento].get("streams"):
      if events_json[evento].get("streams")[0].get("streamName"):
        post+= "Acompanhe o stream em: \n"+"".join(["https://twitch.tv/"+stream.get("streamName")+" \n" for stream in events_json[evento].get("streams")])

    post+= "Acompanhe a bracket em: "+events_json[evento].get("url")

    twitter_API.update_status(post)

    events_json[evento]["state"] = 'ACTIVE'


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
            timezone
            startAt
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
            streams {
              streamName
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
      event["streams"] = tournament["streams"]
      event["timezone"] = tournament["timezone"]
      event["tournament_startAt"] = tournament["startAt"]
      proximos_eventos.append(event)

for evento in proximos_eventos:
  if str(evento["id"]) not in events_json.keys():
    data_time = datetime.datetime.fromtimestamp(evento["startAt"])
    data = data_time.strftime("%d/%m/%Y %H:%M")

    torneio_type = "[Torneio Online]" if evento["isOnline"] == True else "[Torneio Offline]"

    twitter_API.update_status(
      torneio_type+" "+
      evento["tournament"]+" - "+evento["name"]+"\n"+
      "Início: "+data+" ("+evento["timezone"]+")"+"\n"+
      evento["url"]
    )
    time.sleep(1)

    events_json[evento["id"]] = evento

with open('events.json', 'w') as outfile:
  json.dump(events_json, outfile, indent=4)

#pprint.pprint(list(filter(filterTournaments, data)))

#twitter_API.update_status('Hello world!')