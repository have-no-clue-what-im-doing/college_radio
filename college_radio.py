import requests
from datetime import datetime, timedelta, timezone
import time
import subprocess
import json
import psycopg2
import sqlite3
import time
import os
from concurrent.futures import ThreadPoolExecutor
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


college_dict = {
    'ohio': 'https://streamer.radio.co/s319507a6f/listen',
    'cincinnati': 'https://s4.radio.co/sa4dd72cde/listen',
    'oxford_miami': 'https://s2.radio.co/s20123bfa0/listen',
    'ohio_state': 'http://arouseosu.com:8800/stream',
    'toledo': 'https://c23.radioboss.fm:8099/stream',
    'bowling_green_state': 'https://dvstream2.bgsu.edu/wfal',
    'wright_state': 'https://server.wwsu1069.org/stream',
    'akron': 'http://www.streamvortex.com:11300/stream?type=http&nocache=24694'




}

output_folder = '../temp_music'


def ConnectToDB():
    return psycopg2.connect(
        dbname="college_radio",  
        user="college_radio",    
        password="fatrandy123",  
        host="10.10.13.35",        
        port="5432"    
    )

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
    return spotify_details
   

if not os.path.exists(output_folder):
    os.makedirs(output_folder)


def CheckDuplicateSong(table, song):
    conn = None
    try:
        conn = ConnectToDB()
        c = conn.cursor()
        c.execute(
            f'''
            CREATE TABLE IF NOT EXISTS {table} (
                id SERIAL PRIMARY KEY,
                epoch BIGINT,
                entry_date TIMESTAMP,
                college VARCHAR(255),
                artist VARCHAR(255),
                title VARCHAR(255),
                album VARCHAR(255),
                genre VARCHAR(255),
                release_date INTEGER,
                popularity INTEGER,
                duration INTEGER,
                album_art TEXT
            )
            '''
        )
        query_last_song = f'SELECT title FROM {table} ORDER BY id DESC LIMIT 1'
        c.execute(query_last_song)
        data = c.fetchall()
        if data:
            title = data[0][0]
            if title != song['title']:
                WriteToTable(song, table)
                print(f'Table: {table} Title: {song["title"]} Artist: {song["artist"]} Year: {song["release_date"]}')
        else:
            WriteToTable(song, table)
            print(f'Table: {table} Title: {song["title"]} Artist: {song["artist"]} Year: {song["release_date"]}')
        
        conn.commit()  
    except Exception as e:
        print(f'Error: {e}')
    finally:
        if conn:
            conn.close()  

        
#this is ugly af but it works 🤪
def WriteToTable(song_entry_dict, table_name):
    conn = ConnectToDB()
    cursor = conn.cursor()
    try:
        cursor.execute(
            
                f'''
                INSERT INTO {table_name} (epoch, entry_date, college, artist, title, album, genre, release_date, popularity, duration, album_art) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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

yeet = None

def IdentifySong(audio_file, college_name):
    try:
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True)
        if not song_response.stdout:
            print(f'Could not get valid response from songrec command for {college_name}')
            return
        try:
            json_song_response = json.loads(song_response.stdout)
        except json.JSONDecodeError:
            print(f"Could not parse json for {college_name}")
            return
        if not json_song_response.get('matches'):
            print(f"Unable to identify song for {college_name}")
        else:
            epoch = round(time.time())
            local_timezone = timezone(timedelta(hours=-4))
            entry_date = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')
            college = college_name
            artist = json_song_response.get('track', {}).get('subtitle', None)
            title = json_song_response.get('track', {}).get('title', None)
            album = json_song_response.get('track', {}).get('sections', [{}])[0].get('metadata', [{}])[0].get('text', None)
            release_date = json_song_response.get('track', {}).get('sections', [{}])[0].get('metadata', [{}])[2].get('text', None)
            genre = json_song_response.get('track', {}).get('genres', {}).get('primary', None)
            album_art = json_song_response['track']['images']['coverart']
            album_art = json_song_response.get('track', {}).get('images', {}).get('coverart', None)

            if (artist or title or album) == None:
                print("Unable to get song details for artist / title / album")
                return
            try:
                get_song_search = json_song_response.get('track', {}).get('hub', {}).get('providers', [{}])[0].get('actions', [{}])[0].get('uri', None)
                if get_song_search:
                    get_song_search = get_song_search.split(":", 2)[-1]
            except (IndexError, KeyError):
                get_song_search = None

            client_id = '0df099f908434dabb0fbc671bdca2e9b' #I rotate keys eventually and use a .env file eventually :)
            client_secret = '74dce11de46c41689bb330ecb3b169b6' #DON'T GIVE AF RN!!!!

            if get_song_search:
                spotify_details = GetSpotifyDetails(GetToken(client_id, client_secret), get_song_search)
                popularity = spotify_details.get('popularity', None)
                duration = spotify_details.get('duration', None)
            else:
                popularity = None
                duration = None
            
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
            CheckDuplicateSong(college_name, song_entry_dict)
    except Exception as e:
        print(f"Failed to identify song {e}")
    finally:
        RemoveFile(audio_file)


def StreamTime(college_name, radio_stream):
    while True: 
        try:
            r = requests.get(radio_stream, stream=True, verify=False)
            if r.status_code != 200:
                print(f"Not getting 200 response from {college_name} stream. Will try again in 5 minutes")
                time.sleep(300)
                continue
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
            time.sleep(2)  
        finally:
            r.close()  


#StreamTime('ohio_state', college_dict['ohio_state'])
            

def StreamAllColleges():
    with ThreadPoolExecutor(max_workers=len(college_dict)) as executor:
        for college_name, radio_stream in college_dict.items():
            time.sleep(5) #stagger my streams:
            executor.submit(StreamTime, college_name, radio_stream)       

if __name__ == "__main__":
    StreamAllColleges()