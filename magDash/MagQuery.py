'''Query information about the Magellans. Most of this I discovered by
looking at the weather.lco.cl JS code'''
import requests
import json
import re

seeingURL = {
   'BAADE':'https://weather.lco.cl/clima/weather/Magellan/PHP/grabMag1.php',
   'CLAY':'https://weather.lco.cl/clima/weather/Magellan/PHP/grabMag2.php'
   }
MAGweather = "https://weather.lco.cl/clima/weather/Test/PHP/grabWeather.php"
DUPweather = "https://weather.lco.cl/clima/weather/Test/PHP/grabDupontweather.php"
pointingURL = 'http://sam.lco.cl/TOPS/pointing/pointing.php?magtel={}'
pointingPat = re.compile('target: ?"([^"]+)"')

def getMagEnvData(tel='BAA'):
   data = {}
   html = requests.get(seeingURL[tel])
   d = json.loads(html.txt)
   data.update(d[-1])
   html = requests.get(MAGweather)
   d = json.loads(html.txt)
   data.update(d[-1])

def getMagPointingData(tel='BAA'):
   html = requests.get(pointingURL.format(tel))
   res = pointingPat.search(html.text)
   if res is None:
      return None
   return res.group(1)

