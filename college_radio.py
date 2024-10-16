import requests
from datetime import datetime
import subprocess
import json
from mutagen.mp3 import MP3
import time
import os

college_dict = {
    'ohio': 'https://streamer.radio.co/s319507a6f/listen',
    'cincinnati': 'https://s4.radio.co/sa4dd72cde/listen',
    'oxford_miami': 'https://s2.radio.co/s20123bfa0/listen',
    'ohio_state': 'http://arouseosu.com:8800/stream'
}

output_folder = '../temp_music'

if not os.path.exists(output_folder):
    os.makedirs(output_folder)


#print(str(datetime.now()))

def RemoveFile(audio_file):
    os.remove(audio_file)



def IdentifySong(audio_file):
    try:
        song_response = subprocess.run(['songrec', 'audio-file-to-recognized-song', audio_file], capture_output=True, text=True)
        json_song_response = json.loads(song_response.stdout)
        title = json_song_response['track']['title']
        album = json_song_response['track']['sections'][0]['metadata'][0]['text']
        release_date = json_song_response['track']['sections'][0]['metadata'][2]['text']
        genre = json_song_response['track']['genres']['primary']
        print(f'Title: {title}')
        print(f'Album: {album}')
        print(f'Release Date: {release_date}') 
        print(f'Genre: {genre}')
    except Exception as e:
        print(f"Failed to identify song {e}")
    finally:
        RemoveFile(audio_file)


def StreamTime():
    stream_url = 'http://arouseosu.com:8800/stream'
    r = requests.get(stream_url, stream=True)
    audio_id = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_path = os.path.join(output_folder, f'{audio_id}.mp3')
    start_time = time.time()
    try:
        with open(file_path, 'wb') as f:
            for block in r.iter_content(1024):
                f.write(block)
                current_time = time.time()
                if (current_time - start_time) >= 60:
                    break
    finally: 
        r.close()
        IdentifySong(file_path)
        StreamTime()
                
#test git push

StreamTime()
            
        
    