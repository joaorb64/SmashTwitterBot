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
import traceback

f = open('accounts.json')
accounts = json.load(f)

if os.path.exists("auth.json"):
    f = open('auth.json')
    auth_json = json.load(f)
    SMASHGG_KEY = auth_json["SMASHGG_KEY"]

f = open('update_time.json')
updateTime = json.load(f)["updateTime"]

for account in accounts:
    print(account)
    try:
        BEARER_KEY = auth_json[account]["BEARER"]
        CONSUMER_KEY = auth_json[account]["CONSUMER_KEY"]
        CONSUMER_SECRET = auth_json[account]["CONSUMER_SECRET"]
        ACCESS_KEY = auth_json[account]["ACCESS_KEY"]
        ACCESS_SECRET = auth_json[account]["ACCESS_SECRET"]

        twitter_API_v2 = tweepy.Client(
            bearer_token=BEARER_KEY,
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            access_token=ACCESS_KEY,
            access_token_secret=ACCESS_SECRET
        )

        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

        try:
            f = open('events_'+account+'.json')
            events_json = json.load(f)
        except:
            events_json = {}

        print("Get character list")
        f = requests.get(
            "https://api.start.gg/characters?videogameId="+accounts[account]["videogameid"])
        characters_json = json.loads(f.text)["entities"]

        print("Get tournaments in startgg")

        r = requests.post(
            "https://www.start.gg/api/-/gql",
            headers={
                "client-version": "20",
                'Content-Type': 'application/json'
            },
            json={
                'query': '''
							query TournamentsByCountry($cCode: String!, $perPage: Int!) {
            tournaments(query: {
              perPage: $perPage
              filter: {
                countryCode: $cCode
                videogameIds: ['''+accounts[account]["videogameid"]+''']
                upcoming: true,
                computedUpdatedAt: '''+str(int(updateTime-datetime.timedelta(hours=24).total_seconds()))+'''
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
          }
							''',
                'variables': {
                    "cCode": accounts[account]["country"],
                    "perPage": 100
                },
            }
        )

        resp = json.loads(r.text)
        time.sleep(1)
        data = resp["data"]["tournaments"]["nodes"]

        proximos_eventos = []

        print(f"Found {len(data)} tournaments")

        for tournament in data:
            r = requests.post(
                "https://www.start.gg/api/-/gql",
                headers={
                    "client-version": "20",
                    'Content-Type': 'application/json'
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
            time.sleep(1)

            if resp.get("data", {}).get("tournament", None) == None:
                print("Erro? - "+str(resp))
                continue

            tournament_data = resp["data"]["tournament"]

            smash_ultimate_tournaments = 0

            for event in tournament_data["events"]:
                if event["videogame"]["id"] == int(accounts[account]["videogameid"]):
                    smash_ultimate_tournaments += 1

            for event in tournament_data["events"]:
                # Smash Ultimate
                if event["videogame"]["id"] != int(accounts[account]["videogameid"]):
                    continue

                if event["startAt"] > time.time():
                    event["tournament"] = tournament_data["name"]
                    event["tournament_id"] = tournament_data["id"]
                    event["city"] = tournament_data["city"]
                    event["url"] = "https://start.gg"+tournament_data["url"]
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
                print(account+" - novo evento: " +
                      evento["name"] + " - " + evento["tournament"])

                data_time = datetime.datetime.fromtimestamp(
                    evento["startAt"], tz=pytz.timezone(accounts[account]["timezone"]))
                data = data_time.strftime(accounts[account]["timeFormat"])

                data_registration_time = datetime.datetime.fromtimestamp(min(
                    evento["tournament_registrationClosesAt"], evento["startAt"]), tz=pytz.timezone(accounts[account]["timezone"]))
                data_registration = data_registration_time.strftime(
                    accounts[account]["timeFormat"])

                torneio_type = accounts[account]["text-online-tournament"] if evento["isOnline"] == True else accounts[account]["text-offline-tournament"]

                torneio_name = evento["tournament"]

                if evento["tournament_multievent"]:
                    torneio_name += " - " + evento["name"]

                location = ""
                if not evento.get("isOnline") and \
                        (evento.get("tournament_venueName") or evento.get("tournament_venueAddress")):
                    location += "📍"

                    if evento.get("tournament_venueName"):
                        location += evento.get("tournament_venueName")+", "

                    if evento.get("tournament_venueAddress"):
                        splitted = evento.get(
                            "tournament_venueAddress").split(",")
                        if len(splitted) == 1:
                            location += splitted[0]
                        if len(splitted) == 2:
                            location += splitted[0]
                        if len(splitted) == 3:
                            location += splitted[1]
                        if len(splitted) == 4:
                            location += splitted[-3]+", "+splitted[-2]
                        if len(splitted) == 5:
                            location += splitted[-3]

                    location += "\n"

                tweet_id = twitter_API_v2.create_tweet(
                    text=torneio_type + " " +
                    torneio_name + "\n" +
                    location +
                    "📅 "+accounts[account]["text-tournament-start"]+": "+data+" ("+accounts[account]["timezone"]+")"+"\n" +
                    "✏️ "+accounts[account]["text-tournament-registration-ends"]+": "+data_registration+" ("+accounts[account]["timezone"]+")"+"\n" +
                    evento["url"]
                )
                time.sleep(1)

                events_json[evento["id"]] = evento
                events_json[evento["id"]]["tweet_id"] = tweet_id.data["id"]
    except Exception as e:
        print(traceback.format_exc())

    with open('events_'+account+'.json', 'w') as outfile:
        json.dump(events_json, outfile, indent=4)

with open('update_time.json', 'w') as outfile:
    json.dump({"updateTime": time.time()}, outfile, indent=4)
