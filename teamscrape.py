# -*- coding: utf-8 -*-
# This project is copyrighted by Robert Goeddel, 13 Jan 2016
# It makes use of the Nominatim service provided by OpenStreetMap contributors

import sys
import getopt
import time
import json
import requests
import cssutils
from BeautifulSoup import BeautifulSoup

# Candian province codes.
# PQ included because apparently some ESPN worker is Québécois
# We assume that if something contains a common (',') and a canadian
# province code, it's in Canada. Otherwise, it's in the USA. Either way,
# affix the country to the place when querying nominatim to clear up
# some of the mystifyingly incorrect places
canada_codes = ['AB', 'BC', 'MB', 'NB', 'NL', 'NS', 'NT', 'NU', 'ON', 'PE',
             'QC', 'SK', 'YT', 'PQ'];

# This query is rate-limited so we don't piss off OSM
city_map_path = '/tmp/city_map.json'
city_map = {}
QUERY_DELAY = 2.0 # [s]
ESPN_DELAY = 1.0 # [s]
last_query_time = time.clock()
osm_license = u'Data © OpenStreetMap contributors, ODbL 1.0. http://www.openstreetmap.org/copyright'

def rate_limit(min_delay, fn, *args):
    global QUERY_DELAY
    global last_query_time

    now = time.clock()
    diff = now - last_query_time
    delay = max(0, min_delay - diff)
    last_query_time = now
    time.sleep(delay)

    return fn(*args)

def espn_request(url):
    req = requests.get(url.encode('utf-8'))
    try:
        req.raise_for_status()
    except HTTPError as e:
        print e
        sys.exit('ERR: ESPN request error')

    raw_html = req.text
    req.close()
    return raw_html

# Players don't always have text here, so you have to be careful.
# Handle non-existent hometowns as '--'
def get_hometown_from_player_page(player_url):
    print (player_url)
    player_html = rate_limit(ESPN_DELAY, espn_request, (player_url))
    player_soup = BeautifulSoup(player_html)

    hometown_item = player_soup.find('ul', {'class' : lambda x: x and
                                                      'player-metadata' in x
                                           }
                                    )
    hometown = hometown_item.find('li')
    if not (hometown and 'Hometown' in hometown.text):
        return '--'
    return hometown.text[8:]

def get_players(roster_url):
    roster_html = rate_limit(ESPN_DELAY, espn_request, (roster_url))
    team_soup = BeautifulSoup(roster_html)

    # Extract team color
    style = team_soup.find('style').contents[0]
    sheet = cssutils.parseString(style)
    color = u'#000'
    for rule in sheet:
        for prop in rule.style:
            if prop.name == u'background':
                color = prop.value

    # Extract player hometowns
    table = team_soup.findAll('table', {'class' : 'tablehead'})
    header = team_soup.findAll('tr', {'class' : 'colhead'})
    tds = header[0].findAll('td')
    hometown_idx = 0
    name_idx = 0
    idx = 0
    for td in tds:
        if td.text == u'NAME':
            name_idx = idx;
        if td.text == u'HOMETOWN':
            hometown_idx = idx
        idx = idx + 1

    player_rows = table[0].findAll('tr', {'class' : lambda x: x and
                                                   ('oddrow' in x or
                                                    'evenrow' in x)
                                         }
                                  )

    # Null homedown is -- on ESPN
    hometowns = []
    for row in player_rows:
        tds = row.findAll('td')
        hometown = tds[hometown_idx].text;
        # Hometowns are unlisted when it's just a country of origin. In
        # that case, try to grab it from their player page.
        if (hometown == '--'):
            hometown = rate_limit(ESPN_DELAY,
                                  get_hometown_from_player_page,
                                  (tds[name_idx].find('a')['href']))
            if hometown != '--':
                hometowns.append(hometown)
            else:
                print ('Skipping hometown for player')
        else:
            hometowns.append(hometown)

    return (color, hometowns)

def query_osm(hometown):
    global city_map
    global canada_codes

    query_url = 'http://nominatim.openstreetmap.org/search?'
    query_args = 'format=json'

    city = ''
    state = ''
    country = ''
    # Apply country code as necessary
    if ',' in hometown:
        city = hometown[:hometown.find(',')].strip()
        state = hometown[hometown.find(',')+1:].strip()

        canada = False
        for cn in canada_codes:
            canada |= cn in hometown
        if canada:
            country = 'Canada'
        else:
            country = 'USA'
    else:
        country = hometown.strip()


    # Check to see if we have seen this city already. If so,
    # return the cached entry
    if hometown in city_map:
        return city_map[hometown]

    print (city + ', ' + state + ', ' + country)

    # Query for and return hometown info. Then convert from JSON
    query = query_url
    if not (city or state or country):
        return []

    if city:
        query = query + 'city=' + city + '&'
    if state:
        query = query + 'state=' + state + '&'
    if country:
        query = query + 'country=' + country + '&'
    query = (query + query_args).encode('utf-8')
    print (query)
    req = rate_limit(QUERY_DELAY, requests.get, (query))
    try:
        req.raise_for_status()
    except HTTPError as e:
        print e
        sys.exit('ERR: OSM request error')

    # We assume that the first entry is the correct one. In the event that
    # the returned list is empty, return an error value
    req_json= req.json()
    req.close()
    if not req_json:
        return req_json
    json_data = req_json[0]

    city_map[hometown] = (json_data['lat'], json_data['lon'])
    return city_map[hometown]

def main():
    global OSM_DELAY
    global osm_license

    # Fetch the main ESPN teams page. We will strip rosters out from here
    base_url = 'http://espn.go.com'
    teams_url = base_url + '/college-football/teams'

    teams_html = espn_request(teams_url)

    # Chuck it into BS
    soup = BeautifulSoup(teams_html)

    # Pull out each conference
    confs = soup.findAll('div',
                         { 'class' : lambda x: x
                                     and 'mod-teams-list-medium' in x.split()
                         }
                        )

    # iterate through conferences and extract teams, then fetch players from teams
    for conf in confs:
        teams = conf.findAll('li')
        for team in teams:
            name = team.find('a', {'class' : 'bi'}).contents[0].strip()
            roster_url = team.find('a', {'href' : lambda x: x
                                                  and 'roster' in x
                                        }
                                  )['href']
            (color, hometowns) = get_players(base_url + roster_url)

            name = name.strip('; ')
            print (u'%s has %d players and primary color %s\n' % (name,
                   len(hometowns), color))

            jdict = {'name' : name, 'color' : color, 'license' : osm_license, 'hometowns' : {}}

            for hometown in hometowns:
                # Handle PQ for Province du Quebec. OSM expects QC
                hometown = hometown.replace('PQ', 'QC')
                ll = query_osm(hometown)

                # Handle error states
                if not ll:
                    continue

                if hometown in jdict['hometowns']:
                    entry = jdict['hometowns'][hometown]
                    entry['count'] = entry['count'] + 1
                    jdict['hometowns'][hometown] = entry
                else:
                    entry = {'count' : 1, 'lat' : ll[0], 'lon' : ll[1]}
                    jdict['hometowns'][hometown] = entry

            with open('_data/rosters/'+name+'.json', 'w') as outfile:
                json.dump(jdict, outfile)
                outfile.close()

    # When done, save city->latlon mappings because why not?
    with open('/tmp/city_map.json', 'w') as outfile:
        json.dump(city_map, outfile)
        outfile.close()

def usage():
    print ('python teamscrape.py [optional-city-database.json]')

def load_city_map(args):
    f = open(args[0], 'r')

    global city_map_path
    city_map_path= args[0]

    global city_map
    city_map = json.loads(f.read())

    f.close()

# Option argument: feed json record of hometown latlons
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:],'h')
    except getopt.GetoptError as e:
        print str(e)
        usage()
        sys.exit(-1)

    for o, a in opts:
        if o == '-h':
            usage()
            sys.exit()

    if len(args) > 0:
        load_city_map(args)

    main()

