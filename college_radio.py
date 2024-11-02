import requests
import logging
import logging.handlers
import socket
import os
from datetime import datetime, timedelta, timezone
import time
import subprocess
import json
import psycopg2
import time
import os
from concurrent.futures import ThreadPoolExecutor
import urllib3
import yaml

#disable the dumbass warnings about no https
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#disable ipv6. I want only ipv4 addresses in logs. IPv6 taking up way too much space
requests.packages.urllib3.util.connection.HAS_IPV6 = False

hostname = socket.gethostname()
ip_address = requests.get("https://ipecho.net/plain").text

logger = logging.getLogger()
logger.setLevel(logging.INFO)

syslog_handler = logging.handlers.SysLogHandler(address=('log.broderic.pro', 514))  
formatter = logging.Formatter('%(levelname)s - %(message)s')
syslog_handler.setFormatter(formatter)
logger.addHandler(syslog_handler)


# read my yaml file:
with open('./config.yaml', 'r') as file:
    yaml_config = yaml.safe_load(file)




college_dict = yaml_config['college_dict']
database_dict = yaml_config['database']
spotify_dict = yaml_config['spotify']

output_folder = '../temp_music'


def ConnectToDB():
    return psycopg2.connect(
        dbname = database_dict['dbname'],  
        user = database_dict['user'], 
        password = database_dict['password'],
        host = database_dict['host'],      
        port = database_dict['port'] 
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
                logger.info(f'{hostname} {ip_address} Table: {table} Title: {song["title"]} Artist: {song["artist"]} Year: {song["release_date"]}')
        else:
            WriteToTable(song, table)
            logger.info(f'{hostname} {ip_address} Table: {table} Title: {song["title"]} Artist: {song["artist"]} Year: {song["release_date"]}')
        
        conn.commit()  
    except Exception as e:
        logger.error(f'{hostname} {ip_address} {e}')
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
        logger.error(f"{hostname} {ip_address} Failed to write to table: {e}")
    finally:
        conn.close()



def RemoveFile(audio_file):
    os.remove(audio_file)

yeet = None

def IdentifySong(audio_file, college_name):
    try:
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True)
        if not song_response.stdout:
            logger.error(f'{hostname} {ip_address} Could not get valid response from songrec command for {college_name}')
            time.sleep(15)
            return
        try:
            json_song_response = json.loads(song_response.stdout)
        except json.JSONDecodeError:
            logger.error(f"{hostname} {ip_address} Could not parse json for {college_name}")
            return
        if not json_song_response.get('matches'):
            logger.error(f"{hostname} {ip_address} Unable to identify song for {college_name}")
        else:
            print(json_song_response)
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
                logger.error(f"{hostname} {ip_address} Unable to get song details for artist / title / album")
                return
            try:
                get_song_search = json_song_response.get('track', {}).get('hub', {}).get('providers', [{}])[0].get('actions', [{}])[0].get('uri', None)
                if get_song_search:
                    get_song_search = get_song_search.split(":", 2)[-1]
            except (IndexError, KeyError):
                get_song_search = None

            client_id = spotify_dict['client_id'] 
            client_secret = spotify_dict['client_secret']  #fixed :)

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
        logger.error(f"{hostname} {ip_address} Failed to identify song {e}")
    finally:
        RemoveFile(audio_file)


def StreamTime(college_name, radio_stream):
    while True: 
        remove_old_audio = ["find", ".", "-type", "f", "-name", f"*{college_name}*", "-delete"]
        subprocess.run(remove_old_audio, capture_output=True, text=True)
        try:
            r = requests.get(radio_stream, stream=True, verify=False)
            if r.status_code != 200:
                logger.error(f"{hostname} {ip_address} Not getting 200 response from {college_name} stream. Will try again in 5 minutes")
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
            

start_index = int(os.getenv("START_INDEX", "0"))
end_index = int(os.getenv("END_INDEX", "5"))

def StreamAllColleges():
    college_keys = list(college_dict.keys())
    end_index_actual = min(end_index, len(college_keys))
    with ThreadPoolExecutor(max_workers=end_index_actual - start_index) as executor:
        for i in range(start_index, end_index_actual):
            college_name = college_keys[i]
            print(college_name)
            radio_stream = college_dict[college_name]
            time.sleep(5)
            executor.submit(StreamTime, college_name, radio_stream)

if __name__ == "__main__":
    StreamAllColleges()

   

if __name__ == "__main__":
    StreamAllColleges()