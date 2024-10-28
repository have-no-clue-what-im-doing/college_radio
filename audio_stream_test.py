import requests
from datetime import datetime, timedelta, timezone
import time
import subprocess
import json
import sqlite3
import time
import os
from concurrent.futures import ThreadPoolExecutor
import urllib3

output_folder = './'

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
                    if (current_time - start_time) >= 90: 
                        break
            
            #IdentifySong(file_path, college_name)
        
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)  
        finally:
            r.close()  

StreamTime('yeet', 'https://d3byg0ij92yqk6.cloudfront.net/streamWSOU11491934270.aac')