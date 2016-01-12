import sys
import re
import urllib3
import cssutils
from BeautifulSoup import BeautifulSoup

def espn_request(http, url):
    req = http.request('GET', url)
    if req.status != 200:
        sys.exit('ERR: ESPN servers gave bad status %d' % (req.status))

    raw_html = req.data
    req.close()
    return raw_html

def get_players(http, roster_url):
    roster_html = espn_request(http, roster_url)
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

# Fetch the main ESPN teams page. We will strip rosters out from here
base_url = 'http://espn.go.com'
teams_url = base_url+ '/college-football/teams'

http = urllib3.PoolManager()
teams_html = espn_request(http, teams_url)

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
        (color, hometowns) = get_players(http, base_url + roster_url)
        print ('%s has %d players and primary color %s\n' % (name,
               len(hometowns), color))

        f = open('/tmp/'+name+'.roster', 'w')
        f.write(color+'\n')
        for town in hometowns:
            # Skip unlisted towns
            if town != u'--':
                f.write(town+'\n')
        f.close()

