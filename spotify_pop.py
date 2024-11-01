import requests

def GetToken(client_id, client_secret):
    url = 'https://accounts.spotify.com/api/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = { 
        'grant_type': 'client_credentials',
        'client_id': f'{client_id}',
        'client_secret': f'{client_secret}'
    }
    r = requests.post(url, data=data, headers=headers)
    response = r.json()
    return response['access_token']


def GetSongID(token, song_title):
    url = f'https://api.spotify.com/v1/search?q={song_title}&type=track&limit=1'
    print(url)
    headers = {
       f'Authorization': f'Bearer {token}',
    }
   


    r = requests.get(url, headers=headers)
    response = r.json()
    print(response['tracks']['items'][0]['popularity'])

song_string = 'spotify:search:Trying%20Your%20Luck%20The%20Strokes'

GetSongID(GetToken('0df099f908434dabb0fbc671bdca2e9b', '74dce11de46c41689bb330ecb3b169b6'), song_string.split(":", 2)[-1])
