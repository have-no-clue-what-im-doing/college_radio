import requests
import json


proxies = {
    'http': 'http://meetyeetfeet-rotate:98yYZJaf9C5AdtK@p.webshare.io:80',
    'https': 'http://meetyeetfeet-rotate:98yYZJaf9C5AdtK@p.webshare.io:80'
}

r = requests.get("https://api.deezer.com/track/isrc:QZBW42403602", proxies=proxies, stream=True, verify=False, timeout=15)
json_song_response = json.loads(r.text)
deezer_id = json_song_response.get('id')
isrc = json_song_response.get('isrc')

rank = json_song_response.get('rank')
explicit = json_song_response.get('explicit_lyrics')
bpm = json_song_response.get('bpm')
gain = json_song_response.get('gain')
duration = json_song_response.get('duration')
print(deezer_id,isrc, duration, rank, explicit, bpm, gain)
print(f"duration: {duration}")
print(bpm)
