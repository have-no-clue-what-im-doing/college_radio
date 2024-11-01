import requests
import json

radio_stream = 'https://dvstream2.bgsu.edu/wfal'
#radio_stream2 = 'https://s4.radio.co/sa4dd72cde/listen'

r = requests.get(radio_stream, stream=True, verify=False)
#t = requests.get(radio_stream2, stream=True)


print(r)
#print(t.status_code)