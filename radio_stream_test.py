import requests
import json

radio_stream = 'http://arouseosu.com:8800/stream'
radio_stream2 = 'https://s4.radio.co/sa4dd72cde/listen'

r = requests.get(radio_stream, stream=True, verify=False)
t = requests.get(radio_stream2, stream=True)


print(r.status_code)
print(t.status_code)