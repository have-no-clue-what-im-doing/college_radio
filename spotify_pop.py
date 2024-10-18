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

GetToken('0df099f908434dabb0fbc671bdca2e9b', '74dce11de46c41689bb330ecb3b169b6')
