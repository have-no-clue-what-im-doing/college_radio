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


def StreamTest(stream):
    probe = ffmpeg.probe(stream)
    if probe:
        codec = probe['streams'][0]["codec_name"]
        # print(json.dumps(probe))
        print(probe)
        print(codec)



StreamTest("https://broadcast.shoutcheap.com/stream/wsinradi/stream.pls")

# help(ffmpeg.run)