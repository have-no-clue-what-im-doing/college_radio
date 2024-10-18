import requests
from datetime import datetime, timedelta, timezone
import time
import subprocess
import json
import sqlite3
import time
import os

college_dict = {
    'ohio': 'https://streamer.radio.co/s319507a6f/listen',
    'cincinnati': 'https://s4.radio.co/sa4dd72cde/listen',
    'oxford_miami': 'https://s2.radio.co/s20123bfa0/listen',
    'ohio_state': 'http://arouseosu.com:8800/stream'
}

output_folder = '../temp_music'


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


def GetSongPop(token, song_title):
    url = f'https://api.spotify.com/v1/search?q={song_title}&type=track&limit=1'
    print(url)
    headers = {
       f'Authorization': f'Bearer {token}',
    }
    r = requests.get(url, headers=headers)
    response = r.json()
    return response['tracks']['items'][0]['popularity']
   

if not os.path.exists(output_folder):
    os.makedirs(output_folder)


def CheckDuplicateSong(table, song):
    conn = sqlite3.connect('college_radio.db', timeout=10)
    c = conn.cursor()
    query_last_song = f'SELECT title FROM {table} ORDER BY id DESC LIMIT 1'
    c.execute(query_last_song)
    data = c.fetchall()
    print(data)
    if data:
        title = data[0][0]
        print(title)
        #print(title, song['title'])
        if title != song['title']:
            WriteToTable(song)
    else:
        WriteToTable(song)

    conn.commit()
    conn.close()
        
#this is ugly af but it works 🤪
def WriteToTable(song_entry_dict):
    conn = sqlite3.connect('college_radio.db', timeout=10)
    cursor = conn.cursor()
    cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS test (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch INTEGER
    entry_date TEXT
    college TEXT,
    artist TEXT,
    title TEXT,
    album TEXT,
    genre TEXT,
    release_date INTEGER,
    shazams INTEGER,
    album_art TEXT
    )
    '''
    )
    cursor.execute(
    '''
    INSERT INTO test (epoch, entry_date, college, artist, title, album, genre, release_date, shazams, album_art) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''',
    (
    song_entry_dict['epoch'], 
    song_entry_dict['entry_date'], 
    song_entry_dict['college'], 
    song_entry_dict['artist'],
    song_entry_dict['title'], 
    song_entry_dict['album'],
    song_entry_dict['genre'],
    song_entry_dict['release_date'],
    song_entry_dict['shazams'],
    song_entry_dict['album_art']
    )
    )
    conn.commit()
    conn.close()


def RemoveFile(audio_file):
    os.remove(audio_file)



def IdentifySong(audio_file):
    try:
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True)
        json_song_response = json.loads(song_response.stdout)
        epoch = round(time.time())
        local_timezone = timezone(timedelta(hours=-4))
        entry_date = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')
        college = 'Cincinnati'
        artist = json_song_response['track']['subtitle']
        title = json_song_response['track']['title']      
        album = json_song_response['track']['sections'][0]['metadata'][0]['text']
        release_date = json_song_response['track']['sections'][0]['metadata'][2]['text']
        genre = json_song_response['track']['genres']['primary']
        get_song_search = json_song_response['track']['hub']['providers'][0]['actions'][0]['uri'].split(":", 2)[-1]
        client_id = '0df099f908434dabb0fbc671bdca2e9b' #I rotate keys eventually and use a .env file eventually :)
        client_secret = '74dce11de46c41689bb330ecb3b169b6' #DON'T GIVE AF RN!!!!
        shazams = GetSongPop(GetToken(client_id, client_secret), get_song_search)
        album_art = 'path/to/art/'
        song_entry_dict = {
            'epoch': epoch,
            'entry_date': entry_date,
            'college': college,
            'artist': artist,
            'title': title, 
            'album': album,
            'release_date': release_date,
            'genre': genre,
            'shazams': shazams,
            'album_art': album_art
        }
        CheckDuplicateSong('test', song_entry_dict)
    except Exception as e:
        print(f"Failed to identify song {e}")
    finally:
        RemoveFile(audio_file)


def StreamTime():
    while True: 
        try:
            stream_url = 'https://s2.radio.co/s20123bfa0/listen'
            r = requests.get(stream_url, stream=True)
            audio_id = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_path = os.path.join(output_folder, f'{audio_id}.mp3')
            start_time = time.time()
            
            with open(file_path, 'wb') as f:
                for block in r.iter_content(1024):
                    f.write(block)
                    current_time = time.time()
                    if (current_time - start_time) >= 60: 
                        break
            
            IdentifySong(file_path)
        
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)  
        finally:
            r.close()  

                
#test git push

StreamTime()
            
        
    