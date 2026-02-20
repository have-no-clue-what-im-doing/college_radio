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
import ffmpeg

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

#save time to update codec every 24 hours
codec_cache = {} 

# read my yaml file:
with open('./config.yaml', 'r') as file:
    yaml_config = yaml.safe_load(file)




database_dict = yaml_config['database']

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


if not os.path.exists(output_folder):
    os.makedirs(output_folder)


def RemoveFile(college_name):
    try:
        temp_music_dir = os.listdir('../temp_music')
        working_path = os.path.join('..', 'temp_music')
        for song in temp_music_dir:
            if song.startswith(f"{college_name}_"): 
                final_file_path = os.path.join(working_path, song)
                os.remove(final_file_path)     
    except Exception as e:
        logger.error(json.dumps({
            'level': 'error',
            'error_code': 'REMOVE_OLD_FILE_FAILED',
            'hostname': hostname,
            'college': college_name,
            'message': 'Failed to search / remove file',
            'error': str(e)
        }))
            


def CheckDuplicateSong(college_name, title):
    conn = None
    try:
        conn = ConnectToDB()
        c = conn.cursor()

        query_last_song = f'SELECT title FROM all_colleges WHERE college = \'{college_name}\' ORDER BY id DESC LIMIT 1'
        c.execute(query_last_song)
        data = c.fetchall()
        if data:
            last_title = data[0][0]
            if last_title != title:
                return True
                
            else:
                return False
        else:
            return True
    except Exception as e:
        logger.error(json.dumps({
            'level': 'error',
            'error_code': 'DUPLICATE_CHECK_FAIL',
            'hostname': hostname,
            'college': college_name,
            'message': 'Failed to check for duplicate song in table / write to table',
            'error': str(e)
        }))
        return False
    finally:
        if conn:
            conn.close() 
        
        
#this is ugly af but it works 🤪
def WriteToTable(song_entry_dict):
    conn = ConnectToDB()
    cursor = conn.cursor()
    try:
        cursor.execute(
            
                f'''
                INSERT INTO all_colleges (epoch, entry_date, college, artist, title, album, genre, release_date, rank, duration, bpm, gain, explicit, isrc, deezer_id) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    song_entry_dict['rank'],
                    song_entry_dict['duration'],
                    song_entry_dict['bpm'],
                    song_entry_dict['gain'],
                    song_entry_dict['explicit'],
                    song_entry_dict['isrc'],
                    song_entry_dict['deezer_id']
                )
            )
        conn.commit()
        logger.info(json.dumps({
                    'level': 'info',
                    'error_code': 'TABLE_WRITE',
                    'hostname': hostname,
                    'college': song_entry_dict['college'], 
                    'title': song_entry_dict['title'], 
                    'artist': song_entry_dict['artist'],
                    'year': song_entry_dict['release_date'],
                    'message': 'Successful table write'
                    }))
    except Exception as e:
        logger.error(json.dumps({
                    'level': 'error',
                    'error_code': 'SONG_WRITE_FAIL',
                    'hostname': hostname,
                    'college': song_entry_dict['college'],
                    'message': 'Failed to write song to table',
                    'error': str(e)
                }))
    finally:
        cursor.close()
        conn.close()
        


def GetDeezerDetails(deezer_isrc, college_name):
    # print(f"Deezer isrc: {deezer_isrc} college: {college_name}")
    try:
        r = requests.get(f'https://api.deezer.com/track/isrc:{deezer_isrc}', proxies=proxies, stream=True, verify=False, timeout=15)
        if r.status_code != 200:
            r.close()
            logger.error(json.dumps({
                'level': 'error',
                'error_code': 'NO_HTTP_200',
                'hostname': hostname,
                'college': college_name,
                'message': 'Did not receive a 200 response from Deezer api request'
            }))
            return 
        json_song_response = json.loads(r.text)
        r.close()
        # print(f"deezer json response: {json_song_response}")
        if json_song_response:
            duration = json_song_response.get('duration', None)
            deezer_id = json_song_response.get('id', None)
            isrc = json_song_response.get('isrc', None)
            rank = json_song_response.get('rank', None)
            explicit = json_song_response.get('explicit_lyrics', None)
            bpm = json_song_response.get('bpm', None)
            gain = json_song_response.get('gain', None)

            deezer_details = {
                'duration': duration,
                'rank': rank,
                'bpm': bpm,
                'gain': gain,
                'explicit': explicit,
                'isrc': isrc,
                'deezer_id': deezer_id
            }
            return deezer_details
        else:
            logger.error(json.dumps({
                'level': 'error',
                'error_code': 'DEEZER_JSON_ERROR',
                'hostname': hostname,
                'college': college_name,
                'message': f'Deezer API did not return track details / unable to parse to json'
            }))
    except Exception as e:
        logger.error(json.dumps({
            'level': 'error',
            'error_code': 'DEEZER_API_REQUEST_FAIL',
            'hostname': hostname,
            'college': college_name,
            'message': 'Request.get call to Deezer API failed',
            'error': str(e)
        }))
        # return None
    return

      

def IdentifySong(audio_file, college_name):
    try:
        env = os.environ.copy()
        if proxy_string:
            env['HTTPS_PROXY'] = f'http://{proxy_string}'
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True, env=env)
        if not song_response.stdout:
            logger.error(json.dumps({
                    'level': 'error',
                    'error_code': 'SONGREC_FAIL_NO_RESPONSE',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'No response from songrec'
                }))
            time.sleep(15)
            return
        try:
            json_song_response = json.loads(song_response.stdout)
        except json.JSONDecodeError:
            logger.error(json.dumps({
                    'level': 'error',
                    'error_code': 'SONGREC_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Unable to parse json from songrec reply'
                }))
            return
        if not json_song_response.get('matches'):
            logger.info(json.dumps({
                    'level': 'info',
                    'error_code': 'SONGREC_NO_SONG',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Songrec failed to identify the song'
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
                    'level': 'error',
                    'error_code': 'SONGREC_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Songrec reply did not give title / artist / album'
                }))
                return
            if CheckDuplicateSong(college_name, title):
                songrec_isrc = json_song_response.get('track', {}).get('isrc', None) 
                
                if songrec_isrc:
                    deezer_details = GetDeezerDetails(songrec_isrc, college_name)
                    if deezer_details:
                        duration = deezer_details.get('duration', None)
                        rank = deezer_details.get('rank', None)
                        bpm = deezer_details.get('bpm', None)
                        gain = deezer_details.get('gain', None)
                        explicit = deezer_details.get('explicit', None)
                        isrc = deezer_details.get('isrc', None)
                        deezer_id = deezer_details.get('deezer_id', None)
                        if all(v is None for v in (duration, rank, bpm, gain, explicit, isrc, deezer_id)):
                            logger.error(json.dumps({
                            'level': 'warning',
                            'error_code': 'DEEZER_API_NULL_VALUE',
                            'hostname': hostname,
                            'college': college_name,
                            'message': 'Deezer API returned a null value'
                            }))

                    else:
                        duration = None
                        rank = None
                        bpm = None
                        gain = None
                        explicit = None
                        isrc = None
                        deezer_id = None
                        logger.error(json.dumps({
                        'level': 'error',
                        'error_code': 'DEEZER_API_FAIL',
                        'hostname': hostname,
                        'college': college_name,
                        'message': 'Failed to retrieve Deezer details'
                        }))
                else:
                    duration = None
                    rank = None
                    bpm = None
                    gain = None
                    explicit = None
                    isrc = None
                    deezer_id = None
                    logger.error(json.dumps({
                        'level': 'error',
                        'error_code': 'ISRC_FAIL',
                        'hostname': hostname,
                        'college': college_name,
                        'message': 'Failed to retrieve Deezer isrc'
                        }))
                    
                
                song_entry_dict = {
                    'epoch': epoch,
                    'entry_date': entry_date,
                    'college': college,
                    'artist': artist,
                    'title': title, 
                    'album': album,
                    'release_date': release_date,
                    'genre': genre,
                    'duration': duration,
                    'rank': rank,
                    'bpm': bpm,
                    'gain': gain,
                    'explicit': explicit,
                    'isrc': isrc,
                    'deezer_id': deezer_id
                }
                WriteToTable(song_entry_dict)
            #print(song_entry_dict)
            
    except Exception as e:
        logger.error(json.dumps({
                    'level': 'error',
                    'error_code': 'SONGREC_FAIL',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Songrec failed to retrieve song details',
                    'error': str(e)
                }))
    finally:
        RemoveFile(college_name)


def AudioMapping(codec):
    if codec == 'mp3':
        return ('mp3', 'copy')
    elif codec == 'aac':
        return ('m4a', 'aac')  # Re-encode instead of copy
    elif codec == 'opus':
        return ('opus', 'copy')
    elif codec == 'vorbis':
        return ('ogg', 'copy')
    else:
        return ('mp3', 'libmp3lame')


def StreamTime(college_name, radio_stream):
    global codec_cache
    
    while True: 
        try:
            r = requests.get(radio_stream, stream=True, verify=False, timeout=15)
            if r.status_code != 200:
                logger.error(json.dumps({
                    'level': 'error',
                    'error_code': 'NO_HTTP_200',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'Did not receive a 200 response from radio stream',
                }))
                r.close()
                time.sleep(300)
                continue
            r.close()


            current_time = round(time.time())
            
            if (college_name not in codec_cache or 
                current_time - codec_cache[college_name]['cached_at'] >= 86400):
                
                probe = ffmpeg.probe(radio_stream)
                codec_cache[college_name] = {
                    'codec': probe['streams'][0]['codec_name'],
                    'cached_at': current_time
                }
            
            codec = codec_cache[college_name]['codec']
            ext, audio_codec = AudioMapping(codec)  # Get both extension and codec
            
            audio_id = college_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_path = os.path.join(output_folder, f'{audio_id}.{ext}')
            
            stream = ffmpeg.input(radio_stream, t=60)
            stream = ffmpeg.output(stream, file_path, acodec=audio_codec, vn=None)  # Use variable codec
            ffmpeg.run(stream, overwrite_output=True, quiet=True, capture_stderr=True)
            
            IdentifySong(file_path, college_name)
        
        except ffmpeg.Error as e:
            logger.error(json.dumps({
                'level': 'error',
                'error_code': 'FFMPEG_ERROR',
                'hostname': hostname,
                'college': college_name,
                'message': e.stderr.decode() if e.stderr else str(e)
            }))
            time.sleep(300)
        except Exception as e:
            logger.error(json.dumps({
                'level': 'error',
                'error_code': 'STREAM_TIME_ERROR',
                'hostname': hostname,
                'college': college_name,
                'message': str(e)
            }))
            time.sleep(100)


# from docker config, if unable to get GROUP var, default to value of 1
radio_group = int(os.getenv("GROUP", "1"))


#create radio stream group list from config.yaml. grab group int from docker compose
college_group_dict_list = yaml_config['college_groups'][radio_group]





def StreamAllColleges():
    executor = ThreadPoolExecutor(max_workers=12)
    
    for college_entry in college_group_dict_list:
        college_name = college_entry[0]
        radio_stream = college_entry[1]
        print(college_name)
        executor.submit(StreamTime, college_name, radio_stream)
        time.sleep(5)
    
    while True:
        time.sleep(3600)

if __name__ == "__main__":
    StreamAllColleges()

