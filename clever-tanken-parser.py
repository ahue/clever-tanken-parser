# -*- coding: utf-8 -*-

import requests
# import urllib.request
import time
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import hashlib
import json
import argparse

parser = argparse.ArgumentParser(description='Request fuel prices at a location in Germany.')
group = parser.add_mutually_exclusive_group(required=True)
latlon_group = group.add_argument_group('latlon', 'Latitude & Longitude')
group.add_argument('--zipcode', "-z", type=int, help='German zip code (5 digits), e.g. 80678')
latlon_group.add_argument('--lat', type=float, help='Latitude, e.g. 48.1280277')
latlon_group.add_argument('--lon', type=float, help='Longitude, e.g. 11.3633374')
parser.add_argument('--fuel', '-f', type=str, help='Fuel type', default="diesel", choices=["diesel", "autogas", "truck_diesel", "e10", "superplus", "super"], required=True)
parser.add_argument('--sort', "-s", type=str, help='Sort by (p=price)', default="km", choices=["km", "p", "abc"], required=False)
parser.add_argument('--radius', "-r", type=int, help='Radius [km] (5-25km)', default=5, required=False)


args = parser.parse_args()
# print(args)

# url = "https://www.clever-tanken.de/tankstelle_liste?r=5&spritsorte=3&lat=48.1180277&lon=11.6633374&sort=km"
# url = "https://www.clever-tanken.de/tankstelle_liste?spritsorte=3&r=5&ort=81825&sort=km"

radius = min((round(float(max(5, args.radius)) / 5))*5,25)
sorten = dict(autogas=1,lkw_diesel=2,diesel=3,e10=5,superplus=6,super=7)

base_url = "https://www.clever-tanken.de/tankstelle_liste?spritsorte={}&r={}&sort={}&".format(sorten[args.fuel], radius, args.sort)

if args.zipcode:
  base_url += "&ort={}".format(args.zipcode)
else:
  base_url += "&lat={}&lon={}".format(args.lat, args.lon)

# print(base_url)


response = requests.get(base_url)

soup = BeautifulSoup(response.text, "html.parser")

tankstellen = soup.find_all(lambda tag: tag.name == "a" 
                            and tag.has_attr("href") 
                            and "tankstelle_details" in tag["href"])

def get_price(tankstelle):
  price_text = tankstelle.find(lambda tag: tag.name=="div" 
                               and tag.has_attr("class") 
                               and "price-text" in tag["class"]).text
  price = float(re.findall(r'\d\.\d{3}', price_text)[0])
  return(price)

def get_changed_timestamp(tankstelle):
  """
  returns the timestamp of the last recorded change or the timestamp the station opens (as a negative value)
  """
  changed_text = tankstelle.find_all(lambda tag: tag.name=="span" 
                                     and tag.has_attr("class") 
                                     and "price-changed" in tag["class"])
  # print(changed_text)

  if changed_text[0].text.strip() == "öffnet":
    opens_day = re.findall(r'Mo|Di|Mi|Do|Fr|Sa|So', changed_text[1].text)[0] 
    opens_hrs = int(re.findall(r'(\d{1,2}):', changed_text[1].text)[0])
    opens_sec = int(re.findall(r':(\d{1,2})', changed_text[1].text)[0])

    # TODO: We likely will get problems with "opens today"
    wd = datetime.now().weekday()
    wdidx = ["Mo","Di","Mi","Do","Fr","Sa","So"].index(opens_day) - wd
    # distinguish
    # is the day is after or equal the current day of the week
    # or is before the current weekday --> then go to the next week
    offset = wdidx if wdidx >= 0 else 7 - wdidx
    opens = datetime.now() + timedelta(days=offset)
    opens = opens.replace(hour=opens_hrs, minute=opens_sec, 
                          second=0, microsecond=0)

    # print([opens_day, opens_hrs, opens_sec])
    return -opens.timestamp()


  if len(changed_text)==1:
    changed_date = re.findall(r'\d{1,2}\.\d{1,2}.\d{4}', changed_text[0].text)[0]
    changed_clock = re.findall(r'\d{1,2}:\d{1,2}', changed_text[0].text)[0]
    # print([changed_date, changed_clock])
    changed_ts = datetime.strptime('{} {}'.format(changed_date, changed_clock), 
                                   '%d.%m.%Y %H:%M')

  elif len(changed_text)==2 and "Gestern" in changed_text[0].text:
    opens_hrs = int(re.findall(r'(\d{1,2}):', changed_text[0].text)[0])
    opens_sec = int(re.findall(r':(\d{1,2})', changed_text[0].text)[0])
    changed_ts = datetime.now() - timedelta(days=1)
    changed_ts = changed_ts.replace(hour=opens_hrs, minute=opens_sec,
                                    second=0, microsecond=0)

  elif len(changed_text)==3:
    changed_day = changed_text[1].text
    changed_num = int(re.findall(r'\d{1,2}', changed_text[2].text)[0])
    changed_unit = re.findall(r'Sek|Min|Std', changed_text[2].text)[0]

    if changed_unit == "Min":
      changed_num *= 60
    if changed_unit == "Std":
      changed_num *= 3600
    if changed_day != "Heute":
      raise("Parsing changed before failed. Parsed value of changed_day = {}".format(changed_day))

    changed_ts = datetime.now() - timedelta(seconds=changed_num)
  
  return(changed_ts.timestamp())

def get_location_details(tankstelle):
  location_name = tankstelle.find(lambda tag: tag.name=="span" 
                                  and tag.has_attr("class") 
                                  and "fuel-station-location-name" in tag["class"]).text.strip()
  location_street = tankstelle.find(lambda tag: tag.name=="div" 
                                    and tag.has_attr("class") 
                                    and "fuel-station-location-street" in tag["class"]).text.strip()
  location_city = tankstelle.find(lambda tag: tag.name=="div" 
                                  and tag.has_attr("class") 
                                  and "fuel-station-location-city" in tag["class"]).text.strip()
  location_distance = float(re.findall(r'\d+\.\d+', tankstelle.find(lambda tag: tag.name=="div" 
                                                                    and tag.has_attr("class") 
                                                                    and "fuel-station-location-distance" in tag["class"]).text)[0])
  return({
      "name": location_name,
      "street": location_street,
      "city": location_city,
      "distance": location_distance
  })

res = []
for tankstelle in tankstellen:
  obj = dict()
  ts = get_changed_timestamp(tankstelle)
  if ts>0:
    # TODO: check that changed actually is correct!
    obj["changed"] = int(ts)
    obj["price"] = get_price(tankstelle)
    obj["fuel"] = args.fuel
  else:
    obj["opens"] = -int(ts)
  
  obj["location"] = get_location_details(tankstelle)

  id_hash = hashlib.sha1()
  id_hash.update((obj["location"]["name"] + obj["location"]["street"] + obj["location"]["city"]).encode("UTF-8"))
  obj["location"]["id"] = id_hash.hexdigest()
  obj["id"] = obj["location"]["id"] + "_" + str(int(ts)) + "_" + args.fuel
  res.append(obj)
res

print(json.dumps(res))