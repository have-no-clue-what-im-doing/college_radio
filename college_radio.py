import requests
import logging
#import logging.handlers
import socket
import os
from datetime import datetime, timedelta, timezone
import time
import subprocess
import json
import psycopg2
from concurrent.futures import ThreadPoolExecutor
import urllib3
import yaml

#disable the dumbass warnings about no https
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#disable ipv6. I want only ipv4 addresses in logs. IPv6 taking up way too much space
requests.packages.urllib3.util.connection.HAS_IPV6 = False

hostname = socket.gethostname()
#ip_address = requests.get("https://ipecho.net/plain").text

logger = logging.getLogger()
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# read my yaml file:
with open('./config.yaml', 'r') as file:
    yaml_config = yaml.safe_load(file)




college_dict = yaml_config['college_dict']
database_dict = yaml_config['database']
spotify_dict = yaml_config['spotify']
proxy_string = yaml_config['proxy']



if proxy_string:
    proxies = {
        'http': f'http://{proxy_string}',
        'https': f'http://{proxy_string}'
    }
else:
    proxies = None

output_folder = '../temp_music'


def ConnectToDB():
    return psycopg2.connect(
        dbname = database_dict['dbname'],  
        user = database_dict['user'], 
        password = database_dict['password'],
        host = database_dict['host'],      
        port = database_dict['port'] 
    )

def GetToken(client_id, client_secret, college_name):
    try:
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
    except Exception as e:
        logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'SPOTIFY_API_FAILED',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Unable to retrieve Spotify API token',
                    'error': str(e)
                }))


def GetSpotifyDetails(token, song_title, college_name):
    try:
        url = f'https://api.spotify.com/v1/search?q={song_title}&type=track&limit=1'
        headers = {
        f'Authorization': f'Bearer {token}',
        }
        r = requests.get(url, headers=headers)
        response = r.json()
        #print('response ', response)
        popularity = response['tracks']['items'][0]['popularity']
        duration = round((response['tracks']['items'][0]['duration_ms']) / 1000)
        spotify_details = {
            'popularity': popularity,
            'duration': duration
        }
        return spotify_details
    except Exception as e:
        logger.error(json.dumps({
            'type': 'error',
            'error_code': 'SPOTIFY_API_FAILED',
            'hostname': hostname,
            'college': college_name,
            'message': 'Request to Spotify API failed',
            'error': str(e)
        }))
   

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

def RemoveFile(college_name):
    try:
        temp_music_dir = os.listdir('../temp_music')
        default_underscore = 2
        working_path = os.path.join('..', 'temp_music')
        for song in temp_music_dir:
            get_underscore_song_file = len(song.split('_'))
            get_underscore_college_name = len(college_name.split('_')) + default_underscore
            if college_name in  song and get_underscore_song_file == get_underscore_college_name:
                final_file_path = os.path.join(working_path, song)
                #print(f'removing: {final_file_path} for {college_name}')
                os.remove(final_file_path)
    except Exception as e:
        logger.error(json.dumps({
            'type': 'error',
            'error_code': 'REMOVE_OLD_FILE_FAILED',
            'hostname': hostname,
            'college': college_name,
            'message': 'Failed to search / remove file',
            'error': str(e)
        }))

def CheckDuplicateSong(college_name, song):
    conn = None
    try:
        conn = ConnectToDB()
        c = conn.cursor()

        query_last_song = f'SELECT title FROM all_colleges WHERE college = \'{college_name}\' ORDER BY id DESC LIMIT 1'
        c.execute(query_last_song)
        data = c.fetchall()
        if data:
            title = data[0][0]
            if title != song['title']:
                WriteToTable(song)
                logger.info(json.dumps({
                    'type': 'info',
                    'hostname': hostname,
                    'college': college_name,
                    'title': song["title"],
                    'artist': song["artist"],
                    'year': song["release_date"]
                    }))
        else:
            WriteToTable(song)
            logger.info(json.dumps({
                    'type': 'info',
                    'hostname': hostname,
                    'college': college_name,
                    'title': song["title"],
                    'artist': song["artist"],
                    'year': song["release_date"]
                    }))
        
        conn.commit()  
    except Exception as e:
        logger.error(f'{hostname}  {e}')
    finally:
        if conn:
            conn.close() 
        
# 'type="error" hostname="{hostname}" college="{college_name}" text="Unable to write success stat to table" error="{e}"')
def WriteToStats(college_name, request_type):
    conn = ConnectToDB()
    cursor = conn.cursor()
    try:
        if request_type == "success":
            cursor.execute(
                '''
                INSERT INTO stats (college, requests, failed) 
                VALUES (%s, 1, 0)
                ON CONFLICT (college) 
                DO UPDATE SET requests = stats.requests + 1
                ''',
                (college_name,)
            )
        elif request_type == "fail":
            cursor.execute(
                '''
                INSERT INTO stats (college, requests, failed) 
                VALUES (%s, 1, 1)
                ON CONFLICT (college) 
                DO UPDATE SET requests = stats.requests + 1, failed = stats.failed + 1
                ''',
                (college_name,)
            )
        conn.commit()
    except Exception as e:
        logger.error(json.dumps({
            'type': 'error',
            'error_code': 'STATS_WRITE_FAILED',
            'hostname': hostname,
            'college': college_name,
            'request_type': request_type,
            'message': 'Unable to write stat to table',
            'error': str(e)
        }))
    finally:
        cursor.close()
        conn.close()


        
#this is ugly af but it works 🤪
def WriteToTable(song_entry_dict):
    conn = ConnectToDB()
    cursor = conn.cursor()
    try:
        cursor.execute(
            
                f'''
                INSERT INTO all_colleges (epoch, entry_date, college, artist, title, album, genre, release_date, popularity, duration) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    song_entry_dict['duration']
                )
            )
        conn.commit()
    except Exception as e:
        logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'SONG_WRITE_FAIL',
                    'hostname': hostname,
                    'college': song_entry_dict['college'],
                    'message': 'Failed to write song to table',
                    'error': str(e)
                }))
    finally:
        conn.close()
        





def IdentifySong(audio_file, college_name):
    try:
        env = os.environ.copy()
        if proxy_string:
            env['HTTPS_PROXY'] = f'http://{proxy_string}'
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True, env=env)
        if not song_response.stdout:
            logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'SONGREC_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'No response from songrec',
                    'error': str(e)
                }))
            time.sleep(15)
            return
        try:
            json_song_response = json.loads(song_response.stdout)
        except json.JSONDecodeError:
            logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'SONGREC_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Unable to parse json from songrec reply',
                    'error': str(e)
                }))
            return
        if not json_song_response.get('matches'):
            logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'SONGREC_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Songrec failed to identify the song',
                    'error': str(e)
                }))
        else:
            epoch = round(time.time())
            local_timezone = timezone(timedelta(hours=-5))
            entry_date = datetime.now(local_timezone).strftime('%Y-%m-%d %H:%M:%S')
            college = college_name
            
            artist = json_song_response.get('track', {}).get('subtitle', None)
            title = json_song_response.get('track', {}).get('title', None)
    
            sections = json_song_response.get('track', {}).get('sections', [])
            metadata = sections[0].get('metadata', []) if sections else []
            
            album = metadata[0].get('text', None) if len(metadata) > 0 else None
            release_date = metadata[2].get('text', None) if len(metadata) > 2 else None
            
            genre = json_song_response.get('track', {}).get('genres', {}).get('primary', None)
            #album_art = json_song_response.get('track', {}).get('images', {}).get('coverart', None)
            
            if (not artist or not title or not album):
                logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'SONGREC_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Songrec reply did not give title / artist / album',
                    'error': str(e)
                }))
                return
            try:
                get_song_search = json_song_response.get('track', {}).get('hub', {}).get('providers', [{}])[0].get('actions', [{}])[0].get('uri', None)
                #print('song serach: ' + get_song_search)
                if get_song_search:
                    get_song_search = get_song_search.split(":", 2)[-1]
            except (IndexError, KeyError):
                #print('song search error')
                get_song_search = None
            client_id = spotify_dict[f'client_id_{spotify_api}'] 
            client_secret = spotify_dict[f'client_secret_{spotify_api}']  #fixed :)

            if get_song_search:
                spotify_details = GetSpotifyDetails(GetToken(client_id, client_secret, college_name), get_song_search, college_name)
                if spotify_details:
                    popularity = spotify_details.get('popularity', None)
                    duration = spotify_details.get('duration', None)
                else:
                    popularity = None
                    duration = None
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
                'duration': duration
            }
            #print(song_entry_dict)
            CheckDuplicateSong(college_name, song_entry_dict)
    except Exception as e:
        logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'SONGREC_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Songrec failed to retrieve song details',
                    'error': str(e)
                }))
    finally:
        RemoveFile(college_name)


def StreamTime(college_name, radio_stream):
    while True: 
        try:
            r = requests.get(radio_stream, stream=True, verify=False)
            if r.status_code != 200:
                logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'NO_HTTP_200',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Did not receive a 200 response from radio stream',
                    'error': str(e)
                }))
                time.sleep(300)
                continue
            # if r.status_code == 200:
            #     logger.info(f"{college_name} Response headers: {dict(r.headers)}")
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
            logger.error(json.dumps({
                    'type': 'error',
                    'error_code': 'HTTP_REQUESTS_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Failed to make general request to radio stream',
                    'error': str(e)
                }))
            time.sleep(2)  
        finally:
            r.close()  


#StreamTime('ohio_state', college_dict['ohio_state'])


spotify_api = int(os.getenv("SPOTIFY_API", "1"))

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

