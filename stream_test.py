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

college_dict = {
    'ohio': 'https://streamer.radio.co/s319507a6f/listen',
    'cincinnati': 'https://s4.radio.co/sa4dd72cde/listen',
    'oxford_miami': 'https://s2.radio.co/s20123bfa0/listen',
    'ohio_state': 'http://arouseosu.com:8800/stream'
}

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

codec_cache = {} 

output_folder = '../temp_music'



if not os.path.exists(output_folder):
    os.makedirs(output_folder)






def IdentifySong(audio_file, college_name):
    try:
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True)
        json_song_response = json.loads(song_response.stdout)
        if json_song_response:
            # pass
            print(json.dumps(json_song_response, indent=2))
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
        client_id = 'a075e6a082b44e3c9c915a76d2d0f718' #I rotate keys eventually and use a .env file eventually :)
        client_secret = '25064ddad8a94c48843d9ccf1fb98ea7' #DON'T GIVE AF RN!!!!
        album_art = json_song_response['track']['images']['coverart']
    except Exception as e:
        print(f"Failed to identify song {e}")



import ffmpeg

def StreamTime(college_name, radio_stream):
    global codec_cache
    
    while True: 
        try:
            # r = requests.get(radio_stream, stream=True, verify=False, timeout=15)
            # if r.status_code != 200:
            #     logger.error(json.dumps({
            #         'level': 'error',
            #         'error_code': 'NO_HTTP_200',
            #         'hostname': hostname,
            #         'college': college_name,
            #         'message': 'Did not receive a 200 response from radio stream',
            #     }))
            #     r.close()
            #     time.sleep(300)
            #     continue
            # r.close()


            current_time = round(time.time())
            
            if (college_name not in codec_cache or 
                current_time - codec_cache[college_name]['cached_at'] >= 86400):
                
                probe = ffmpeg.probe(radio_stream, timeout=15000000)
                codec_cache[college_name] = {
                    'codec': probe['streams'][0]['codec_name'],
                    'cached_at': current_time
                }
            
            codec = codec_cache[college_name]['codec']
            
            ext, audio_codec = AudioMapping(codec)  # Get both extension and codec
            print(f"extension: {ext} codec: {audio_codec}")
            
            audio_id = college_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_path = os.path.join(output_folder, f'{audio_id}.{ext}')
            
            stream = ffmpeg.input(radio_stream, t=15, reconnect=1, reconnect_streamed=1, timeout=15000000, re=None)
            stream = ffmpeg.output(stream, file_path, acodec=audio_codec, vn=None)
            cmd = ffmpeg.compile(stream, overwrite_output=True)
            result = subprocess.run(cmd, capture_output=True, timeout=90)
            if result.returncode != 0:
                logger.error(json.dumps({
                    'level': 'error',
                    'error_code': 'FFMPEG_ERROR',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'ffmpeg exited with error',
                    'error': result.stderr.decode()
                }))
                time.sleep(300)
                continue
            local_file_probe = ffmpeg.probe(file_path)
            audio_length = float(local_file_probe['format']['duration'])
            if audio_length and audio_length >= 5:
                # print(f"audio length: {audio_length} file path: {file_path}")
                IdentifySong(file_path, college_name)
            else:
                logger.error(json.dumps({
                    'level': 'error',
                    'error_code': 'FFMPEG_DURATION_ERROR',
                    'hostname': hostname,
                    'college': college_name,
                    'message': 'ffmpeg did not download a large enough audio file to inspect / ffmpeg local probe failed',
                    'error': f"audio length: {audio_length}."
                }))
                time.sleep(100)
                continue

            
        
        except ffmpeg.Error as e:
            logger.error(json.dumps({
                'level': 'error',
                'error_code': 'FFMPEG_ERROR',
                'hostname': hostname,
                'college': college_name,
                'message': "ffmpeg failed during stream time",
                'error': e.stderr.decode() if e.stderr else str(e)
            }))
            time.sleep(300)
        except Exception as e:
            logger.error(json.dumps({
                'level': 'error',
                'error_code': 'STREAM_TIME_ERROR',
                'hostname': hostname,
                'college': college_name,
                'message': "ffmpeg failed during stream time",
                'error': str(e)
            }))
            time.sleep(1)

StreamTime('cincinnatiii', 'https://xcsb.live/listen/xcsb-cleveland/xcsb.aac')
            
'''
def StreamAllColleges():
    with ThreadPoolExecutor(max_workers=len(college_dict)) as executor:
        for college_name, radio_stream in college_dict.items():
            executor.submit(StreamTime, college_name, radio_stream)       

if __name__ == "__main__":
    StreamAllColleges()

'''