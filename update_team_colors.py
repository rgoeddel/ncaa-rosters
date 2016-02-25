# -*- coding: utf-8 -*-
import sys
import getopt
import json
import re
from os import listdir

def main(args):
    # Open colors database
    f = open(args[0], 'r')
    school_to_colors = json.loads(f.read())
    f.close()

    # Get list of roster files
    rosters = filter(lambda f: f.endswith('.json'),
                     [f.encode('utf-8') for f in listdir(args[1])])
    schools = []
    for roster in rosters:
        schools.append(roster[:-5])
    start_len = len(schools)

    # Handle abrreviated/mistyped entries
    abbrv = {"BYU" : "Brigham Young",
             "SMU" : "Southern Methodist",
             "VMI" : "Virginia Military Institute",
             "Ole Miss" : "Mississippi",
             "NC State" : "North Carolina State",
             "Florida Intl" : "Florida International",
             "The Citadel" : "Citadel",
             "Southern Mississippi" : "Southern Miss",
             "Southern" : "Southern University",
             "Stephen F Austin" : "Stephen F. Austin",
             "Presbyterian College" : "Presbyterian",
             "San José State": "San Jose State"}


    school_len = len(schools)+1
    while school_len > len(schools):
        school_len = len(schools)
        # Match school names against our school+color database.
        # We are looking for a unique best match. If none exists,
        # Move on and hope something fixes it
        for school in schools:
            if school in abbrv:
                s = re.sub(r'\W+', '', abbrv[school])
            else:
                s = re.sub(r'\W+', '', school)
            match = None
            for full_school in school_to_colors:
                fs = re.sub(r'\W+', '', full_school)
                if s in fs and match == None:
                    match = full_school
                elif s in fs:
                    match = None
                    break

            # Update entry
            if match != None:
                print "Matched %s to %s" % (school, match)

                filename = args[1]+school+'.json'
                f = open(filename, 'r')
                school_data = json.loads(f.read())
                f.close()

                colors = school_to_colors[match];
                school_data['color'] = colors;
                with open(filename, 'w') as outfile:
                    json.dump(school_data, outfile)
                    outfile.close()

                schools.remove(school)
                del school_to_colors[match]

    print ("\nRelaxing restrictions...\n")

    # Handle remaining cases by looking shortest multi-match
    school_len = len(schools)+1
    while school_len > len(schools):
        school_len = len(schools)

        for school in schools:
            match = None
            for full_school in school_to_colors:
                if school not in full_school:
                    continue
                if '-' in full_school:
                    continue
                if match == None:
                    match = full_school
                if len(match) > len(full_school):
                    match = full_school

            # Update entry
            if match != None:
                print "Matched %s to %s" % (school, match)

                filename = args[1]+school+'.json'
                f = open(filename, 'r')
                school_data = json.loads(f.read())
                f.close()

                colors = school_to_colors[match];
                school_data['color'] = colors;
                with open(filename, 'w') as outfile:
                    json.dump(school_data, outfile)
                    outfile.close()

                schools.remove(school)
                del school_to_colors[match]

    print ("\nProcessed %d of %d schools\n") % (start_len-len(schools), start_len)

    # Missing entries
    print ("Missing entries for: ")
    for school in sorted(schools):
        print ("\t%s") % (school)


def usage():
    print ('python update_team_colors.py [team_colors.json] [rosters_folder]')

# Option argument: feed json record of hometown latlons
if __name__ == "__main__":
    reload(sys)
    sys.setdefaultencoding('utf8')

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

    if len(args) > 1:
        main(args)

