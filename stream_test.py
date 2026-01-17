import requests
from datetime import datetime, timedelta, timezone
import time
import subprocess
import json
import sqlite3
import time
import os
import ffmpeg
from concurrent.futures import ThreadPoolExecutor

college_dict = {
    'ohio': 'https://streamer.radio.co/s319507a6f/listen',
    'cincinnati': 'https://s4.radio.co/sa4dd72cde/listen',
    'oxford_miami': 'https://s2.radio.co/s20123bfa0/listen',
    'ohio_state': 'http://arouseosu.com:8800/stream'
}

output_folder = '../temp_music'



if not os.path.exists(output_folder):
    os.makedirs(output_folder)






def IdentifySong(audio_file, college_name):
    try:
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True)
        json_song_response = json.loads(song_response.stdout)
        if json_song_response:
            print(json_song_response)
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
    while True: 
        try:
            audio_id = college_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_path = os.path.join(output_folder, f'{audio_id}.mp3')
            
            stream = ffmpeg.input(radio_stream, t=60)
            stream = ffmpeg.output(stream, file_path, acodec='copy', vn=None) 
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            IdentifySong(file_path, college_name)
        
        except ffmpeg.Error as e:
            print(f"Error: {e.stderr.decode() if e.stderr else e}")
            time.sleep(10)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)


StreamTime('west_georgia', 'https://kbhu.bhsu.edu/index.html?sid=1')
            
'''
def StreamAllColleges():
    with ThreadPoolExecutor(max_workers=len(college_dict)) as executor:
        for college_name, radio_stream in college_dict.items():
            executor.submit(StreamTime, college_name, radio_stream)       

if __name__ == "__main__":
    StreamAllColleges()

'''