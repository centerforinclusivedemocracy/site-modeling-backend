# -*- coding: utf-8 -*-
"""
Created on Mon Dec 23 10:43:05 2019

@author: Gorgonio

This file contains 
- short names for DB schemas that are used across various ccep modules
- variables that have to be defined for all states and counties, 
  which are then passed by the main processing script into individual modules that require them
"""

# Schema shortcuts
ssl = "suitable_site_layers"
osm = "osm"
admin = "admin_bounds"
fssl = "final_suitable_sites"

# Data structure is as follows:
# County name: 
#   county code, 
#   bounding box choice for CCEP4, 
#   3-day capacity for vote sites for CCEP5, 
#   tuple of voter site overrides for CCEP5 (10 day sites, 3 day sites (total), drop box sites) - provided by client
CA_counties = {
    # --- Prior counties processed by CCEP/DK
    # These bounding box values came to us from DataKind
    'madera': ['039', True, 20000, (2,7,5)], 
    'napa': ['055', True, 25000, (2,9,6)], 
    'nevada': ['057', True, 13000, (2,7,5)], 
    'sacramento': ['067', False, 20000, (17,85,57)], 
    'san_mateo': ['081', False, 20000, (9,43,29)], 
    # --- New counties to process
    'amador': ['005', True, 20000, (2,3,2)],
    'butte': ['007', True, 20000, (3,12,8)],
    'el_dorado': ['017', True, 20000, (3,13,9)],
    'fresno': ['019', False, 20000, (10,48,32)],
    'los_angeles': ['037', False, 20000, (183,559,373)],
    'mariposa': ['043', True, 20000, (2,2,2)],
    'orange': ['059', False, 20000, (33,167,111)],
    'santa_clara': ['085', False, 20000, (19,98,65)],
    'tuolumne': ['109', True, 20000, (2,4,3)],
    'calaveras': ['009', True, 20000, (2,3,2)]

}

# bbox True if county is rural / sparse, or has an odd shape
# tuple of voter site overrides for CCEP5 (15 day sites, 1 day sites (total), drop box sites) - provided by client
CO_counties = {
    'adams': ['001', True, 20000, (3,20,22)], 
    'arapahoe': ['005', True, 20000, (4,29,32)], 
    'boulder': ['013', True, 20000, (2,17,16)], 
    'broomfield': ['014', True, 20000, (1,3,3)], # bbox True because OSM network cannot be loaded based on county name
    'denver': ['031', True, 20000, (5,33,35)], 
    'douglas': ['035', True, 20000, (3,18,15)],
    'eagle': ['037', True, 20000, (1,3,2)],
    'el_paso': ['041', False, 20000, (5,32,35)],
    'fremont': ['043', True, 20000, (1,3,2)],
    'garfield': ['045', True, 20000, (1,3,2)],
    'jefferson': ['059', True, 20000, (5,31,33)],
    'la_plata': ['067', True, 20000, (1,3,3)],
    'larimer': ['069', True, 20000, (3,18,17)],
    'mesa': ['077', True, 20000, (1,7,7)],
    'pueblo': ['101', True, 20000, (1,8,8)],
    'weld': ['123', True, 20000, (2,13,13)]
}

AZ_counties = {
    'maricopa': ['013', False, 70000, (40, 110, 15)]
}

TX_counties = {
    'harris': ['201', False, 20000, (60,800,0)]
}


states = {    
    "ca": [CA_counties, "3310", "06"], # NAD 83 California Albers in meters (originally used by DK)    
    "co": [CO_counties, "26954", "08"], # NAD83 / Colorado Central 
    "az": [AZ_counties, "26949", "04"], # NAD83 / Arizona Central
    "tx": [TX_counties, "3083", "48"] # NAD83 Texas Centric Albers Equal Area
}

