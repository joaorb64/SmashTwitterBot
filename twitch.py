import requests
import json
import datetime
import os
import sys
import time

if os.path.exists("auth.json"):
    f = open('auth.json')
    auth_json = json.load(f)
    TWITCH_CLIENT_ID = auth_json["TWITCH_CLIENT_ID"]
    TWITCH_CLIENT_SECRET = auth_json["TWITCH_CLIENT_SECRET"]
else:
    TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
    TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET")

r = requests.post('https://id.twitch.tv/oauth2/token?client_id='+TWITCH_CLIENT_ID +
                  '&client_secret='+TWITCH_CLIENT_SECRET+'&grant_type=client_credentials')
resp = json.loads(r.text)

token = resp.get("access_token", None)


def get_clips(twitch_game_name):
    r = requests.get(
        "https://api.twitch.tv/helix/games?name="+twitch_game_name,
        headers={
            'Authorization': 'Bearer '+token,
            'Client-Id': TWITCH_CLIENT_ID
        }
    )
    resp = json.loads(r.text)
    print(resp)

    gameId = resp["data"][0]["id"]

    clips = {}

    for j in range(7):
        print(str(j) + " days back")
        startTime = (datetime.datetime.utcnow() -
                     datetime.timedelta(days=(j+2))).isoformat("T") + "Z"
        endTime = (datetime.datetime.utcnow() -
                   datetime.timedelta(days=(j+1))).isoformat("T") + "Z"

        print(startTime)
        print(endTime)

        pagination = ""

        for i in range(10):
            r = requests.get(
                "https://api.twitch.tv/helix/clips?game_id=" +
                str(gameId)+"&started_at="+startTime+"&ended_at=" +
                endTime+"&first=100&after="+pagination,
                headers={
                    'Authorization': 'Bearer '+token,
                    'Client-Id': TWITCH_CLIENT_ID
                }
            )
            resp = json.loads(r.text)

            pagination = resp.get("pagination", {}).get("cursor", None)

            for c in resp.get("data", {}):
                if c["language"] not in clips:
                    clips[c["language"]] = []
                clips[c["language"]].append(c)

            print(i, end="\r")

            if pagination == None:
                break

    for lang in clips.keys():
        clips[lang].sort(key=lambda clip: clip["view_count"], reverse=True)

    return clips
