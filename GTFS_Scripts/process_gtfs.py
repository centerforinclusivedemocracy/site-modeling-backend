#!/bin/env python3
"""
GTFS processing script
"""

STATE_PREFIX = "CA"

COUNTY_SETS = [
    {
        'name': "Amador County",
        'fipscode': "005",
        'gtfsfolders': [
            'California/amador-gtfs',
            'California/calaveras-ca-us'
        ],
    },
    {
        'name': "Butte County",
        'fipscode': "007",
        'gtfsfolders': [
            'California/butte',
        ],
    },
    {
        'name': "El Dorado County",
        'fipscode': "017",
        'gtfsfolders': [
            # 'California/el-dorado',  # are these the same data? they look really similar SS: Likely duplicates
            'California/eldoradotransit-ca-us',
            'California/laketahoe-ca-us'
        ],
    },
    {
        'name': "Fresno County",
        'fipscode': "019",
        'gtfsfolders': [
            'California/fax_gtfs',
            'California/fresnocounty-ca-us', # SS: This is FCRTA
            'California/kcapta-ca-us'
        ],
    },
    {
        'name': "Log Angeles County",
        'fipscode': "037",
        'gtfsfolders': [
            'California/LA/avta-gtfs',
            'California/LA/elmonte-ca-us',
            'California/LA/foothilltransit-ca-us',
            'California/LA/LADOT',
            'California/LA/dpwlacounty-ca-us', # SS: this is LA Go Bus
            'California/LA/LA Metro',
            'California/LA/Lawndale Beat',
            'California/LA/Long Beach Transit (LBT)',
            'California/LA/Metrolink',
            'California/LA/PVPTA',
            'California/LA/Thousand Oaks',
            'California/LA/Torrance'
            #'California/LA/PVVTA', SS: Out of scope - Riverside County
            #'California/LA/beaumont-ca-us', SS: Out of scope - Riverside County
            #'California/LA/corona-ca-us', SS: Out of scope - Riverside County
        ],
    },
    {
        'name': "Madera County",
        'fipscode': "039",
        'gtfsfolders': [
            'California/madera-max',
            'California/madera-mcc',
            'California/yosemite-ca-us'
        ],
    },
    {
       'name': "Mariposa County",
       'fipscode': "043",
       'gtfsfolders': [
            'California/yosemite-ca-us'
       ],
    },
    {
        'name': "Napa County",
        'fipscode': "055",
        'gtfsfolders': [
            'California/napa-vine',
        ],
    },
    {
       'name': "Nevada County",
       'fipscode': "057",
       'gtfsfolders': [
           'California/nevada-co', # SS: This is Gold Country
           'California/laketahoe-ca-us'
       ],
    },
    {
       'name': "Orange County",
       'fipscode': "059",
       'gtfsfolders': [
            'California/orange-co-google_transit', # SS: This is OCTA
           #'California/google_transit-orange', # SS Likely duplicate to OCTA
           'California/LA/anaheim-ca-us',
           'California/LA/Laguna Beach Transit'
       ],
    },
    {
       'name': "Sacramento County",
       'fipscode': "067",
       'gtfsfolders': [
           'California/sac-regional-transit', # SS: This is SRT
           'California/eldoradotransit-ca-us',
       ],
    },
    {
        'name': "San Mateo County",
        'fipscode': "081",
        'gtfsfolders': [
            'California/BART',
            'California/caltrain',
            'California/commute-org',
            'California/samtrans'
        ],
    },
    {
       'name': "Santa Clara County",
       'fipscode': "085",
       'gtfsfolders': [
           'California/gtfs_vta',
           'California/caltrain'
       ],
    },
    {
        'name': "Trinity County",
        'fipscode': "105",
        'gtfsfolders': [
            'California/trinitytransit'
        ],
    },
    {
        'name': "Tuolomne County",
        'fipscode': "109",
        'gtfsfolders': [
            'California/tuoloumne',
            'California/yosemite-ca-us',
            'California/calaveras-ca-us'
        ],
    },
    {
        'name': "Calaveras County",
        'fipscode': "009",
        'gtfsfolders': [
            'California/calaveras-ca-us'
        ],
    },
]


##################################################################################################################################


import csv
import os


# main processing: given a dataset from COUNTY_SETS, go through its GTFS folders and process each one,
# then collect them into a giant transit_stops.csv CSV
def process_dataset(dataset):
    collected_transit_stops = []
    for gtfsfolder in dataset['gtfsfolders']:
        print("    {}".format(gtfsfolder))
        newtransitstops = process_gtfs(gtfsfolder)
        collected_transit_stops += newtransitstops

    write_transitstops_csv(dataset['outfilename'], collected_transit_stops)


# process a GTFS folder, merging agency name, stop IDs and lat/lngs, etc.
# to form a list of dicts representing the transit stops, suitable for writing out to a CSV
def process_gtfs(gtfsfolder):
    agency_file = os.path.join(gtfsfolder, 'agency.txt')
    stops_file = os.path.join(gtfsfolder, 'stops.txt')
    times_file = os.path.join(gtfsfolder, 'stop_times.txt')

    # fetch THE agency name used for all stops
    # we found 1 outlier where there was >1 agency, but we're not really concerned about agency name so aren't worrying about it
    with open(agency_file, encoding='utf-8-sig') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            agency_name = row['agency_name']

    # fetch the set of stops and create their stub records
    transitstops = []
    with open(stops_file, encoding='utf-8-sig') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            transitstops.append({
                # basic info
                'provider': agency_name,
                'stop_id': row['stop_id'],
                'stop_lat': float(row['stop_lat']),
                'stop_lon': float(row['stop_lon']),
                # stub stops 'n' scores
                'num_stops_per_week': 0,
                'score': 0,
            })

    # collect all bus stop times, then for each transit stop assign the count of times listed there (num_stops_per_week)
    # note that some stops will have 0 stops per day and that's oaky; we're not sure why, maybe out-of-service stops or special events?
    allstoptimes = []
    with open(times_file, encoding='utf-8-sig') as csvfile:
        csvreader = csv.DictReader(csvfile)
        for row in csvreader:
            allstoptimes.append(row)

    for transitstop in transitstops:
        stopsperday = [i for i in allstoptimes if i['stop_id'] == transitstop['stop_id']]
        transitstop['num_stops_per_week'] = len(stopsperday)

    # go back over the stops, and give them a simple linear score
    # based on their num_stops_per_week relative to the min & max num_stops_per_week noted in this dataset for this agency
    # 0s are omitted for the bucket calculation and get a special 0 score
    stopcounts = [i['num_stops_per_week'] for i in transitstops if i['num_stops_per_week'] > 0]
    stopsmin = min(stopcounts)
    stopsmax = max(stopcounts)

    if stopsmax == stopsmin:
        print("        WARNING: All stops have {} num_stops_per_week and will get score 1".format(transitstops[0]['num_stops_per_week']))

    for transitstop in transitstops:
        if stopsmax == stopsmin:  # handle goofy case where all stops have same num_stops_per_week so there's 0 range, give them all a score of 1
            score = 1
        elif transitstop['num_stops_per_week'] < 1:
            score = 0
        else:
            score = (transitstop['num_stops_per_week'] - stopsmin) / (stopsmax - stopsmin)
            score = 1 + round(3 * score) 

        """
        # debugging scores for a specific stop
        if transitstop['stop_id'] == '2382238':
            print("Stop {}".format(transitstop['stop_id']))
            print("{} in range {} - {} = {}".format(transitstop['num_stops_per_week'] , stopsmin, stopsmax, score))
            import sys
            sys.exit(666)
        """

        # assign the score but also mention odd cases
        if not score:
            print("        WARNING: Transit stop has no times and gets 0 score: {} {} in {}".format(transitstop['provider'], transitstop['stop_id'], times_file))
        transitstop['score'] = score

    # done!
    return transitstops


# write a final CSV of the collected transit stops
def write_transitstops_csv(csvfilename, transitstops):
    # the fields to write, which means both the header column names AND the field names from the transit stop dicts
    fields = [
        'stop_id',
        'num_stops_per_week',
        'score',
        'stop_lat',
        'stop_lon',
        'provider',
    ]

    with open(csvfilename, 'w') as csvfile:
        csvout = csv.writer(csvfile, quoting=csv.QUOTE_NONNUMERIC)
        csvout.writerow(fields)
        for transitstop in transitstops:
            row = [transitstop[i] for i in fields]
            csvout.writerow(row)


# if this is run from CLI, go ahead and execute it
if __name__ == '__main__':
    for dataset in COUNTY_SETS:
        # fill in some source and target file names, prepend folder names, etc.
        # yes, we're mutating a global in-place, but it's one time at startup
        # why make the human type it, when we can compute it?
        outfilename = '{}_{}.csv'.format(STATE_PREFIX.lower(), dataset['fipscode'])
        dataset['outfilename'] = os.path.join('outputs', outfilename)
        dataset['gtfsfolders'] = [os.path.join('inputs', i) for i in dataset['gtfsfolders']]

        print("{}  =>  {}".format(dataset['name'], dataset['outfilename']))
        process_dataset(dataset)

    print("DONE")
