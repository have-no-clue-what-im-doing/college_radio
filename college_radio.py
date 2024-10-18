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


def GetSpotifyDetails(token, song_title):
    url = f'https://api.spotify.com/v1/search?q={song_title}&type=track&limit=1'
    headers = {
       f'Authorization': f'Bearer {token}',
    }
    r = requests.get(url, headers=headers)
    response = r.json()
    popularity = response['tracks']['items'][0]['popularity']
    duration = round((response['tracks']['items'][0]['duration_ms']) / 1000)
    spotify_details = {
        'popularity': popularity,
        'duration': duration
    }
    print(duration)
    print(spotify_details)
    return spotify_details
   

if not os.path.exists(output_folder):
    os.makedirs(output_folder)


def CheckDuplicateSong(table, song):
    
    try:
        conn = sqlite3.connect('college_radio.db', timeout=10)
        c = conn.cursor()
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS test (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                epoch INTEGER,
                entry_date TEXT,
                college TEXT,
                artist TEXT,
                title TEXT,
                album TEXT,
                genre TEXT,
                release_date INTEGER,
                popularity INTEGER,
                duration INTEGER,
                album_art TEXT
            )
            '''
        )
        c.close()
        conn.close()
    except Exception as e:
        print(f'error: {e}')
    finally:
        conn = sqlite3.connect('college_radio.db', timeout=10)
        c = conn.cursor()
        query_last_song = f'SELECT title FROM {table} ORDER BY id DESC LIMIT 1'
        c.execute(query_last_song)
        data = c.fetchall()
        if data:
            title = data[0][0]
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
    try:
        cursor.execute(
                '''
                INSERT INTO test (epoch, entry_date, college, artist, title, album, genre, release_date, popularity, duration, album_art) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    song_entry_dict['popularity'],
                    song_entry_dict['duration'],
                    song_entry_dict['album_art']
                )
            )
        conn.commit()
    except Exception as e:
        print(f"Failed to write to table: {e}")
    finally:
        conn.close()



def RemoveFile(audio_file):
    os.remove(audio_file)



def IdentifySong(audio_file, college_name):
    try:
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True)
        json_song_response = json.loads(song_response.stdout)
        epoch = round(time.time())
        local_timezone = timezone(timedelta(hours=-4))
        entry_date = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')
        college = college_name
        artist = json_song_response['track']['subtitle']
        title = json_song_response['track']['title']      
        album = json_song_response['track']['sections'][0]['metadata'][0]['text']
        release_date = json_song_response['track']['sections'][0]['metadata'][2]['text']
        genre = json_song_response['track']['genres']['primary']
        get_song_search = json_song_response['track']['hub']['providers'][0]['actions'][0]['uri'].split(":", 2)[-1]
        client_id = '0df099f908434dabb0fbc671bdca2e9b' #I rotate keys eventually and use a .env file eventually :)
        client_secret = '74dce11de46c41689bb330ecb3b169b6' #DON'T GIVE AF RN!!!!
        spotify_details = GetSpotifyDetails(GetToken(client_id, client_secret), get_song_search)
        popularity = spotify_details['popularity']
        duration = spotify_details['duration']
        album_art = json_song_response['track']['images']['coverart']
        song_entry_dict = {
            'epoch': epoch,
            'entry_date': entry_date,
            'college': college,
            'artist': artist,
            'title': title, 
            'album': album,
            'release_date': release_date,
            'genre': genre,
            'popularity': popularity,
            'duration': duration,
            'album_art': album_art
        }
        CheckDuplicateSong('test', song_entry_dict)
    except Exception as e:
        print(f"Failed to identify song {e}")
    finally:
        RemoveFile(audio_file)


def StreamTime(college_name, radio_stream):
    while True: 
        try:
            r = requests.get(radio_stream, stream=True)
            audio_id = college_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_path = os.path.join(output_folder, f'{audio_id}.mp3')
            start_time = time.time()
            
            with open(file_path, 'wb') as f:
                for block in r.iter_content(1024):
                    f.write(block)
                    current_time = time.time()
                    if (current_time - start_time) >= 60: 
                        break
            
            IdentifySong(file_path, college_name)
        
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)  
        finally:
            r.close()  


StreamTime('ohio_state', college_dict['ohio_state'])
            
        
    