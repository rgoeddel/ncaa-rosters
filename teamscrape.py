# -*- coding: utf-8 -*-
# This project is copyrighted by Robert Goeddel, 13 Jan 2016
# It makes use of the Nominatim service provided by OpenStreetMap contributors

import sys
import time
import json
import requests
import cssutils
from BeautifulSoup import BeautifulSoup

# This query is rate-limited so we don't piss off OSM
city_map = {}
QUERY_DELAY = 2.0 # [s]
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

def get_players(roster_url):
    roster_html = rate_limit(QUERY_DELAY, espn_request, (roster_url))
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
    idx = 0
    for td in tds:
        if td.text == u'HOMETOWN':
            break
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
        hometowns.append(tds[idx].text)

    return (color, hometowns)

def query_osm(hometown):
    global city_map

    query_url = 'http://nominatim.openstreetmap.org/search/'
    query_args = '?format=json'

    # First, check to see if we have seen this city already. If so,
    # return the cached entry
    if hometown in city_map:
        return city_map[hometown]

    # Query for and return hometown info. Then convert from JSON
    query = (query_url+hometown+query_args).encode('utf-8')
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

            jdict = {'name' : name, 'color' : color, 'hometowns' : {}}

            for hometown in hometowns:
                # Throw away EPSN's junk '--'
                if not ',' in hometown:
                    continue

                # Handle PQ for Province du Quebec. OSM expects QC
                if 'PQ' in hometown[-2:]:
                    hometown = hometown[:-2] + 'QC'

                # XXX Fix me to rate limit at the query to OSM itself, not in
                # general...
                ll = query_osm(hometown)

                # Handle error states
                if not ll:
                    continue

                if hometown in jdict['hometowns']:
                    entry = jdict['hometowns'][hometown]
                    entry['count'] = entry['count'] + 1
                    jdict['hometowns'][hometown] = entry
                else:
                    entry = {'count' : 1, 'license' : osm_license, 'lat' : ll[0], 'lon' : ll[1]}
                    jdict['hometowns'][hometown] = entry

            with open('rosters/'+name+'.json', 'w') as outfile:
                json.dump(jdict, outfile)
                outfile.close()

    # When done, save city->latlon mappings because why not?
    with open('/tmp/city_map.json', 'w') as outfile:
        json.dump(city_map, outfile)
        outfile.close()

if __name__ == "__main__":
    main()
