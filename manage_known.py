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

def update_events_file(account):
  with open('events_'+account+'.json', 'w') as outfile:
    json.dump(events_json, outfile, indent=4)

if os.path.exists("auth.json"):
  f = open('auth.json')
  auth_json = json.load(f)

  SMASHGG_KEY = auth_json["SMASHGG_KEY"]

for account in accounts:
  try:
    print(account)

    CONSUMER_KEY = auth_json[account]["CONSUMER_KEY"]
    CONSUMER_SECRET = auth_json[account]["CONSUMER_SECRET"]
    ACCESS_KEY = auth_json[account]["ACCESS_KEY"]
    ACCESS_SECRET = auth_json[account]["ACCESS_SECRET"]

    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

    twitter_API = tweepy.API(auth, parser=tweepy.parsers.JSONParser())

    f = open('events_'+account+'.json')
    events_json = json.load(f)

    f = requests.get("https://api.smash.gg/characters?videogameId="+accounts[account]["videogameid"])
    characters_json = json.loads(f.text)["entities"]

    # Deletar eventos passados, se nao standings, mensagem de inicio de torneio
    for evento in list(events_json):
      print(account+" - checking event: ["+str(evento)+"] "+events_json[evento].get("tournament", "")+" - "+events_json[evento].get("name", ""))
      r = requests.post(
        'https://api.smash.gg/gql/alpha',
        headers={
          'Authorization': 'Bearer'+SMASHGG_KEY,
        },
        json={
          'query': '''
            query evento($eventId: ID!) {
              event(id: $eventId) {
                name
                state
                startAt
                numEntrants
                isOnline
                slug
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
                  name
                  startAt
                  endAt
                  registrationClosesAt
                  venueName
                  venueAddress
                  addrState
                  city
                  streams {
                    streamName
                  }
                  images{
                    id
                    url
                    type
                  }
                  events{
                    videogame {
                      id
                    }
                  }
                }
              }
            },
          ''',
          'variables': {
            "eventId": str(evento)
          },
        }
      )
      if r.text == None:
        print("ERRO: ")
        print(r)
        continue

      resp = json.loads(r.text)
      time.sleep(1)

      if not resp.get("data"):
        print(">>Erro: ")
        print(resp)
        continue

      data = resp["data"]["event"]

      if data == None:
        print("Evento sumiu...?")
        continue

      smash_ultimate_tournaments = 0

      for event in data["tournament"]["events"]:
        if event["videogame"]["id"] == int(accounts[account]["videogameid"]):
          smash_ultimate_tournaments += 1

      events_json[evento]["id"] = int(evento)
      events_json[evento]["name"] = data["name"]
      events_json[evento]["tournament"] = data["tournament"]["name"]
      events_json[evento]["images"] = data["tournament"]["images"]
      events_json[evento]["tournament_multievent"] = False if smash_ultimate_tournaments <= 1 else True
      events_json[evento]["tournament_venueName"] = data["tournament"]["venueName"]
      events_json[evento]["tournament_venueAddress"] = data["tournament"]["venueAddress"]
      events_json[evento]["tournament_addrState"] = data["tournament"]["addrState"]
      events_json[evento]["tournament_startAt"] = data["tournament"]["startAt"]
      events_json[evento]["tournament_endAt"] = data["tournament"]["endAt"]
      events_json[evento]["city"] = data["tournament"]["city"]
      events_json[evento]["url"] = "https://smash.gg/"+data["slug"]
      events_json[evento]["startAt"] = data["startAt"]
      events_json[evento]["isOnline"] = data["isOnline"]
      events_json[evento]["numEntrants"] = data["numEntrants"]

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

          # Dont post results where the winner has placement #2
          # or there are 2 #1 placings.
          # I think it's a bug when there's a bracket reset
          if len(phase["standings"]["nodes"]) > 0 and \
          (str(phase["standings"]["nodes"][0]["placement"]) == "2" or str(phase["standings"]["nodes"][1]["placement"]) == "1"):
            continue

          cancel = False

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
                          displayScore
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
            time.sleep(10)
            char_data = resp.get("data")

            if char_data:
              char_data = char_data.get("event").get("sets").get("nodes")

              if char_data == None:
                entrant["invalid"] = True
            else:
              print("Error fetching character data? -- cancel")
              cancel = True
              break
              entrant["invalid"] = True
              char_data = {}

            char_usage = {}

            if char_data is not None:
              dq = True

              # DQ - commented out because of bugs
              # for _set in char_data:
              #   if _set.get("displayScore", None) is not None:
              #     displayScore = _set.get("displayScore").split(" ")
              #     if displayScore[0] != "-1" and displayScore[-1] != "-1":
              #       dq = False
              
              # if dq:
              #  entrant["dq"] = True

              # Char usage
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
                char_usage_named[char_in_json["name"]]["name"] = char_in_json["name"]
                char_usage_named[char_in_json["name"]]["usage"] = char[1]
                char_usage_named[char_in_json["name"]]["icon"] = char_in_json.get("images")[1].get("url")

            entrant["char_usage"] = char_usage_named
          
          if cancel:
            continue

          post = "🏆 ["+accounts[account]["text-results"]+"]"
          post += "["
          post += accounts[account]["text-online"] if events_json[evento].get("isOnline") else " "+accounts[account]["text-offline"]
          post += "]"
          post += "\n\n"

          nome = events_json[evento]["tournament"]

          if events_json[evento]["tournament_multievent"]:
            nome += " - " + events_json[evento]["name"]
            if len(nome) > 80:
              nome = nome[:80]+"…"
          
          if phase.get("multiphase"):
            nome += " ("+phase.get("phase").get("name")+")"
          
          post += nome

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
          
          post += "\nBracket: "+events_json[evento]["url"]
          
          if phase.get("standings").get("pageInfo").get("total") < 64:
            drawResults.drawResults(events_json[evento], phase, accounts[account])
            twitter_API.update_status_with_media(filename="./media.png", status=post)
          else:
            drawResults.drawResults8x9(events_json[evento], phase, accounts[account])
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
            twitter_API.update_status(status="@"+accounts[account]["handle"]+"\n"+post2, in_reply_to_status_id=thread1["id"])
          
          events_json[evento]["postedPhaseResultIds"].append(phase["id"])

          update_events_file(account)
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
      if not "postedStarting" and data["state"] == 'ACTIVE':
        print("Evento iniciado - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])

        post = ""
        post+= accounts[account]["text-tournament-starting-before"]
        
        nome = events_json[evento]["tournament"]

        if events_json[evento]["tournament_multievent"]:
          nome += " - " + events_json[evento]["name"]
        
        if len(nome) > 80:
          nome = nome[:80]+"…"
        
        post += nome + accounts[account]["text-tournament-starting-after"] + "\n"
        
        if events_json[evento].get("streams"):
          if events_json[evento].get("streams")[0].get("streamName"):
            post+= "Streams: \n"+"".join(["https://twitch.tv/"+stream.get("streamName")+" \n" for stream in events_json[evento].get("streams")[0:7]])

        post+= "Bracket: "+events_json[evento].get("url")

        print(post)
        print(len(post))

        twitter_API.update_status(post)

        events_json[evento]["state"] = 'ACTIVE'
        events_json[evento]["postedStarting"] = True
      
      # Menos de 1h para finalizar inscricoes
      if not "postedRegistrationClosing" in events_json[evento].keys() and "tweet_id" in events_json[evento].keys():
        if events_json[evento]["state"] != 'ACTIVE' and events_json[evento]["tournament_registrationClosesAt"] <= time.time() + datetime.timedelta(hours=1).total_seconds():
          print("Menos de 1h para fechar inscrições - " + events_json[evento]["tournament"] + " - " + events_json[evento]["name"])

          post = accounts[account]["text-tournament-registration-ending"]+"\n"
          post += accounts[account]["text-tournament-registered-players-before"] + \
            str(events_json[evento]["numEntrants"]) + \
            accounts[account]["text-tournament-registered-players-after"]

          twitter_API.update_status(status="@"+accounts[account]["handle"]+"\n"+post, in_reply_to_status_id=events_json[evento]["tweet_id"])

          events_json[evento]["postedRegistrationClosing"] = True
  
    with open('events_'+account+'.json', 'w') as outfile:
      json.dump(events_json, outfile, indent=4)
      
  except Exception as e:
    print(e)