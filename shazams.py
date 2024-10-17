import requests
from bs4 import BeautifulSoup

url = 'https://www.shazam.com/song/266377070/trying-your-luck'
r = requests.get(url)

soup = BeautifulSoup(r.content, 'html5lib')
print(soup)
html_data = soup.prettify()
#print(html_data)
