import requests
import json

radio_stream = 'https://prod-54-162-171-6.amperwave.net/uofwestgeorgia-wolfaac-hlsc1.m3u8'
#radio_stream2 = 'https://s4.radio.co/sa4dd72cde/listen'

r = requests.get(radio_stream, stream=True, verify=False)
#t = requests.get(radio_stream2, stream=True)


print(r)
#print(t.status_code)