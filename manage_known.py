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

# Deletar eventos passados, se nao standings, mensagem de inicio de torneio
for evento in list(events_json):
  print("Checking event: "+events_json[evento]["tournament"]+" - "+events_json[evento]["name"])
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
            numEntrants
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
              endAt
              registrationClosesAt
              venueName
              venueAddress
              addrState
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

  if data == None:
    print("Evento sumiu - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])
    events_json.pop(evento)
    continue

  events_json[evento]["images"] = data["tournament"].get("images", []).copy()

  if data["tournament"]["streams"] != None:
    events_json[evento]["streams"] = data["tournament"]["streams"].copy()

  events_json[evento]["tournament_startAt"] = data["tournament"]["startAt"]
  events_json[evento]["startAt"] = data["startAt"]
  events_json[evento]["numEntrants"] = data["numEntrants"]
  events_json[evento]["tournament_registrationClosesAt"] = data["tournament"]["registrationClosesAt"]

  events_json[evento]["tournament_endAt"] = data["tournament"]["endAt"]

  events_json[evento]["tournament_venueName"] = data["tournament"]["venueName"]
  events_json[evento]["tournament_venueAddress"] = data["tournament"]["venueAddress"]
  events_json[evento]["tournament_addrState"] = data["tournament"]["addrState"]

  # Evento que nunca foi finalizado (depois de 5 dias)
  if time.time() > events_json[evento]["tournament_endAt"] + datetime.timedelta(days=5).total_seconds() and data["state"] == 'ACTIVE':
    print("Evento abandonado - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])
    events_json.pop(evento)
    continue

  # Evento finalizado
  if data["state"] == 'COMPLETED' or data["state"] == 'ACTIVE':
    print("Evento ativo ou completo - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])

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
                state
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
      if phase["progressionsOut"] == None:
        valid_phases.append(phase)

    for phase in valid_phases:
      if len(valid_phases) > 1:
        phase["multiphase"] = True
      else:
        phase["standings"] = data_phase["standings"]
      
      # Ja postado ou nao finalizado
      if (phase["state"] != 3) or (phase["id"] in events_json[evento]["postedPhaseResultIds"]):
        continue

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
          dq = True
          for game in char_data:
            if game.get("games"):
              dq = False
              for selection in game.get("games"):
                if selection.get("selections"):
                  for selection_entry in selection.get("selections"):
                    if selection_entry["entrant"]["id"] == entrant["entrant"]["id"]:
                      if selection_entry["selectionValue"] not in char_usage.keys():
                        char_usage[selection_entry["selectionValue"]] = 1
                      else:
                        char_usage[selection_entry["selectionValue"]] += 1
          if dq:
            entrant["dq"] = True
        
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
      
      if phase.get("standings").get("pageInfo").get("total") < 64:
        drawResults.drawResults(events_json[evento], phase)
        twitter_API.update_with_media("./media.png", status=post)
      else:
        drawResults.drawResults8x9(events_json[evento], phase)
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
        twitter_API.update_status(status="@smash_bot_br\n"+post2, in_reply_to_status_id=thread1["id"])
      
      events_json[evento]["postedPhaseResultIds"].append(phase["id"])

      update_events_file()
      time.sleep(30)

    allPhasesPosted = True

    for phase in events_json[evento]["phaseGroups"]:
      if (phase["progressionsOut"] == None) and (phase["id"] not in events_json[evento]["postedPhaseResultIds"]):
        allPhasesPosted = False
        break

    if allPhasesPosted:
      print("Evento finalizado e postado - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])
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
  
  # Menos de 1h para finalizar inscricoes
  if not "postedRegistrationClosing" in events_json[evento].keys() and "tweet_id" in events_json[evento].keys():
    if events_json[evento]["state"] != 'ACTIVE' and events_json[evento]["tournament_registrationClosesAt"] <= time.time() + datetime.timedelta(hours=1).total_seconds():
      print("Menos de 1h para fechar inscrições - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])

      post = "Falta menos de 1h para o encerramento das inscrições!\n"
      post += "O evento já conta com " + str(events_json[evento]["numEntrants"]) + " inscritos."

      twitter_API.update_status(status="@smash_bot_br\n"+post, in_reply_to_status_id=events_json[evento]["tweet_id"])

      events_json[evento]["postedRegistrationClosing"] = True

with open('events.json', 'w') as outfile:
  json.dump(events_json, outfile, indent=4)