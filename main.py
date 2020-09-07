import tweepy
import time
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
        query evento($eventId: ID!) {
          event(id: $eventId) {
            state
            startAt
            phaseGroups {
              id
              phase {
                name
                state
              }
              progressionsOut {
                id
              }
              state
            }
            tournament {
              startAt
              registrationClosesAt
              streams {
                streamName
              }
              images{
                id
                url
                type
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

  if not resp.get("data"):
    print(">>Erro: ")
    print(resp)
    continue

  data = resp["data"]["event"]

  events_json[evento]["images"] = data["tournament"]["images"].copy()
  events_json[evento]["streams"] = data["tournament"]["streams"].copy()
  events_json[evento]["tournament_startAt"] = data["tournament"]["startAt"]
  events_json[evento]["startAt"] = data["startAt"]
  events_json[evento]["tournament_registrationClosesAt"] = data["tournament"]["registrationClosesAt"]

  # Evento finalizado
  if data["state"] == 'COMPLETED':
    print("Evento finalizado - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])

    r = requests.post(
      'https://api.smash.gg/gql/alpha',
      headers={
        'Authorization': 'Bearer'+SMASHGG_KEY,
      },
      json={
        'query': '''
          query EventStandings($eventId: ID!, $page: Int!, $perPage: Int!) {
            event(id: $eventId) {
              standings(query: {
                perPage: $perPage,
                page: $page
              }){
                pageInfo {
                  total
                }
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
              phaseGroups {
                id
                phase {
                  name
                }
                progressionsOut {
                  id
                }
                standings(query: {
                  perPage: $perPage,
                  page: $page
                }){
                  pageInfo {
                    total
                  }
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
            }
          },
        ''',
        'variables': {
          "eventId": events_json[evento]["id"],
          "page": 1,
          "perPage": 16
        },
      }
    )
    resp = json.loads(r.text)
    data_phase = resp["data"]["event"]

    phase_groups = data_phase["phaseGroups"]
    events_json[evento]["phaseGroups"] = phase_groups

    if "postedPhaseResultIds" not in events_json[evento].keys():
      events_json[evento]["postedPhaseResultIds"] = []

    valid_phases = []

    for phase in events_json[evento]["phaseGroups"]:
      if (phase["progressionsOut"] == None) and (phase["id"] not in events_json[evento]["postedPhaseResultIds"]):
        valid_phases.append(phase)

    for phase in valid_phases:
      if len(valid_phases) > 1:
        phase["multiphase"] = True
      else:
        phase["standings"] = data_phase["standings"]

      for entrant in phase["standings"]["nodes"]:
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
        char_data = resp.get("data")

        if char_data:
          char_data = char_data.get("event").get("sets").get("nodes")

          if char_data == None:
            entrant["invalid"] = True
        else:
          entrant["invalid"] = True
          char_data = {}

        char_usage = {}

        if char_data is not None:
          for game in char_data:
            if game.get("games"):
              for selection in game.get("games"):
                if selection.get("selections"):
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
            char_usage_named[char_in_json["name"]] = {}
            char_usage_named[char_in_json["name"]]["usage"] = char[1]
            char_usage_named[char_in_json["name"]]["icon"] = char_in_json.get("images")[1].get("url")

        entrant["char_usage"] = char_usage_named

      post = "🏆 [Resultados]"
      post += " [Online]" if events_json[evento].get("isOnline") else " [Offline]"
      post += "\n\n" + events_json[evento]["tournament"]

      if events_json[evento]["tournament_multievent"]:
        post += " - " + events_json[evento]["name"]
      
      if phase.get("multiphase"):
        post += " ("+phase.get("phase").get("name")+")"

      post += "\n\n"
      
      post2 = post

      valid_entrants = []
      for entrant in phase["standings"]["nodes"]:
        if "invalid" not in entrant.keys():
          valid_entrants.append(entrant)
      phase["standings"]["nodes"] = valid_entrants
      
      counter = 0
      for entrant in phase["standings"]["nodes"]:
        placement = entrant["placement"]
        placement = str(placement)

        placement_text = ""

        placement_text += placement + " "

        twitter = entrant.get("entrant")
        if twitter: twitter = twitter.get("participants")
        if twitter: twitter = twitter[0].get("user")
        if twitter: twitter = twitter.get("authorizations")

        if twitter:
          placement_text += "@" + str(twitter[0].get("externalUsername"))
        else:
          placement_text += entrant["entrant"]["name"]
        placement_text += "\n"

        if counter < 8:
          post += placement_text
        else:
          post2 += placement_text

        counter += 1
      
      drawResults.drawResults(events_json[evento], phase)

      if phase.get("standings").get("pageInfo").get("total") >= 64:
        post+="\n(1/2)"
        post2+="\n(2/2)"
        filenames = ['media.png', 'media2.png']
        media_ids = []
        for filename in filenames:
          res = twitter_API.media_upload(filename)
          print(res)
          media_ids.append(res["media_id"])

        # Tweet with multiple images
        thread1 = twitter_API.update_status(media_ids=media_ids, status=post)
        time.sleep(5)
        twitter_API.update_status(status="@smash_bot_br\n"+post2, in_reply_to_status_id=thread1)
      else:
        twitter_API.update_with_media("./media.png", status=post)
      
      events_json[evento]["postedPhaseResultIds"].append(phase["id"])

      update_events_file()
      time.sleep(30)

    allPhasesPosted = True

    for phase in events_json[evento]["phaseGroups"]:
      if (phase["progressionsOut"] == None) and (phase["id"] not in events_json[evento]["postedPhaseResultIds"]):
        allPhasesPosted = False
        break

    if allPhasesPosted:
      events_json.pop(evento)
      continue
  
  # Evento iniciado
  if not "postedStarting" in events_json[evento].keys():
    if data["state"] == 'ACTIVE' and data["startAt"] <= time.time():
      print("Evento iniciado - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])

      post = ""
      post+= "Está começando o " + events_json[evento]["tournament"]

      if events_json[evento]["tournament_multievent"]:
        post += " - " + events_json[evento]["name"]
      
      post += "!\n"
      
      if events_json[evento].get("streams"):
        if events_json[evento].get("streams")[0].get("streamName"):
          post+= "Streams: \n"+"".join(["https://twitch.tv/"+stream.get("streamName")+" \n" for stream in events_json[evento].get("streams")])

      post+= "Bracket: "+events_json[evento].get("url")

      twitter_API.update_status(post)

      events_json[evento]["state"] = 'ACTIVE'
      events_json[evento]["postedStarting"] = True


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
            registrationClosesAt
            events {
              id
              name
              isOnline
              state
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
      event["tournament_registrationClosesAt"] = tournament_data["registrationClosesAt"]
      event["images"] = tournament_data["images"]
      event["tournament_multievent"] = False if smash_ultimate_tournaments <= 1 else True
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
