# Python script to read fuel prices from clever-tanken.de

* Requests endpoint https://www.clever-tanken.de/tankstelle_liste
* Uses `beautifulsoup4` for parsing
* Works as of 23.4.2020; Changes in website structure may break the parser

```
usage: clever-tanken-parser.py [-h] --zipcode ZIPCODE [--lat LAT] [--lon LON]
                               --fuel
                               {diesel,autogas,truck_diesel,e10,superplus,super}
                               [--sort {km,p,abc}] [--radius RADIUS]

Request fuel prices at a location in Germany.

optional arguments:
  -h, --help            show this help message and exit
  --zipcode ZIPCODE, -z ZIPCODE
                        German zip code (5 digits), e.g. 80678
  --fuel {diesel,autogas,truck_diesel,e10,superplus,super}, -f {diesel,autogas,truck_diesel,e10,superplus,super}
                        Fuel type
  --sort {km,p,abc}, -s {km,p,abc}
                        Sort by (p=price)
  --radius RADIUS, -r RADIUS
                        Radius [km] (5-25km)
```

Returns a JSON list with objects. If `changed` property is contained, it is an price update. If `opens` is contained, the gas station is currently closed and `opens` holds the time it opens again.

```
[
  {
    "fuel": "diesel",
    "id": "5c1af18375c2bae386c57566b68909f9a552bbc9_1587672172_diesel",
    "location": {
      "distance": 0.5,
      "name": "ARAL",
      "street": "Landshuter Allee 163",
      "id": "5c1af18375c2bae386c57566b68909f9a552bbc9",
      "city": "80637 M\\u00fcnchen"
    },
    "price": 1.109,
    "changed": 1587672172
  },
  {
    "id": "518ec15208adf92800ed76bb7e07f94c09eb88ca_-1587700800_diesel",
    "location": {
      "distance": 0.5,
      "name": "TOTAL",
      "street": "Leonrodstr. 48",
      "id": "518ec15208adf92800ed76bb7e07f94c09eb88ca",
      "city": "80636 M\\u00fcnchen"
    },
    "opens": 1587700800
  }
]
```