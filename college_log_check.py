import requests
import logging
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



with open('./config.yaml', 'r') as file:
    yaml_config = yaml.safe_load(file)


def ConnectToDB():
    return psycopg2.connect(
        dbname = database_dict['dbname'],  
        user = database_dict['user'], 
        password = database_dict['password'],
        host = database_dict['host'],      
        port = database_dict['port'] 
    )

def QueryLastEntry(college):
    conn = ConnectToDB()
    c = conn.cursor()
    query = f"SELECT entry_date from all_colleges where college=\'{college}\' ORDER BY id DESC LIMIT 1"
    c.execute(query)
    data = c.fetchall()
    if not data:
        print(f"no entries from {college}")
        return
    date = data[0][0]
    
    time_now = datetime.now(timezone.utc).replace(tzinfo=None)
    diff = time_now - date
    hours = 24
    if diff > timedelta(hours=hours):
        print(f"{college} no log in last {hours} hours!")
    
    # print(date)

database_dict = yaml_config['database']
college_group_obj = yaml_config['college_groups']
# print(college_group_list)
college_group_ints = list(college_group_obj.keys())


for group in college_group_obj:
    college_group_list = college_group_obj[group]
    for college in college_group_list:
        QueryLastEntry(college[0])
        # print(college[0])

# print("YEEEEEEET:")
# print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))