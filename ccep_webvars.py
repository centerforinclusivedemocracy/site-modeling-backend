# -*- coding: utf-8 -*-
"""
Created on Tue Feb  4 10:42:30 2020

@author: Gorgonio
"""

# This is a list of all files from CCEP5 except where noted below
# Used in CCEP6 steps 14 and 16 
model_output_files = ['additional_sites_distance.csv',
                      'additional_sites_model.csv',
                      'all_sites_scored.csv', # From CCEP3 
                      'eleven_day_sites.csv',
                      'four_day_sites.csv',
                      'dropbox_sites.csv']

# In CCEP6 step 15, only retain these columns in csv created from suitable sites, and 
#  model output files
csv_keep_cols = ['idnum',
                 'lon',
                 'lat',
                 'dens.cvap.std',
                 'dens.work.std',
                 'popDens.std',
                 'prc.CarAccess.std', 
                 'prc.ElNonReg.std' ,
                 'prc.disabled.std',
                 'prc.latino.std',
                 'prc.nonEngProf.std',
                 'prc.pov.std',
                 'prc.youth.std',
                 'rate.vbm.std',
                 'dens.poll.std',
                 'center_score',
                 'droppoff_score']

# In CCEP6 step 16, only retain these columns in op shapefiles
shp_keep_cols = ['idnum','geometry','county','vc_score','db_score']

# This dictionary is used to map column names from the input indicator data (provided
# by Laura), to the output fields and strings.
# Value 0 = field names in indicator_data.csv
# Value 1 = field names in indicator_data.zip (shapefile)
# Values 2, 3, 4 = section, title, and description in indicator_menu_fields.csv (displayed on website)
# Don't use commas in strings. Use &#x002C in place of commas, if needed
indic_field_map = {
    "GEOID":            ["geoid", "geoid", "", "", ""],
    "GEOID_Tract":      ["geoid", "geoid", "", "", ""],
    "FIPS":             ["fips", "fips", "", "", ""],
    "w_FIPS":           ["fips", "fips", "", "", ""],
    "COUNTYFP10":       ["countyfp", "countyfp", "", "", ""],
    "cvapDens":         ["cvapdens", "cvapdens", "siting",\
                         "County Percentage of Voting Age Citizens", \
                         "The number of citizens in this tract who are voting age divided by the county's total number of voting age citizens."],
    "cvapDens_flag":    ["cvapdens_unreliable_flag", "cvap_un", "", "", ""],                         
    "jobShareTract":    ["job_dens", "job_dens", "siting",\
                         "County Worker Percentage", \
                         "The percent of employed county residents in a tract out of the total employed county residents in the county."],
    # TODO: Confirm
    "popDensKM2":       ["popdens", "popdens", "siting",\
                         "Population Density", \
                         "The total population density per square kilometer."],
    # Extra fields from popdens file that were present in prior output                          
    "pop":              ["pop10", "pop10", "", "", ""],
    "area_km2":         ["areakm", "areakm", "", "", ""],                          
    # TODO: Confirm                         
    "pollShare":        ["pollvoter_dens", "polvtrdens", "siting",\
                         "Polling Place Voter Percentage", \
                         "The number of voters who voted at a polling place divided by the total number of voters who voted at a polling place in the county."],
    "AsnVBM":           ["vbm_rate_asn", "vbm_asn", "siting",\
                         "Vote by Mail Rate (Asian-American)", \
                         "The percentage of Asian-American voters who voted by mail."],
    "LatVBM":           ["vbm_rate_lat", "vbm_lat", "siting",\
                         "Vote by Mail Rate (Latino)", \
                         "The percentage of Latino voters who voted by mail."],
    "TotVBM":           ["vbm_rate_tot", "vbm_tot", "siting",\
                         "Vote by Mail Rate (Total)", \
                         "The percentage of voters who voted by mail."],
    "YouthVBM":         ["vbm_rate_youth", "vbm_yth", "siting",\
                         "Vote by Mail Rate (Youth)", \
                         "The percentage of voters between the age of 18 and 24 years old who voted by mail."],
    "CarAccess.prc":    ["prc_caraccess_final", "pr_car", "siting",\
                         "Percent of Population with Vehicle Access", \
                         "The percentage of the population with access to a vehicle."],
    "CarAccess_flag":   ["prc_caraccess_final_unreliable_flag", "pr_car_un", "", "", ""],
    "LEP.prc":          ["prc_nonengprof_final", "pr_ngpr", "siting",\
                         "Percent Limited English Proficient Population", \
                         "The percentage of the population that has limited English proficiency."],
    "LEP_flag":         ["prc_nonengprof_final_unreliable_flag", "pr_ngpr_un", "", "", ""],
    "BelowPoverty.prc": ["prc_pov_final", "pr_pov", "siting",\
                         "Percent of the Population in Poverty", \
                         "The percentage of the population with income below the poverty level."],
    "BelowPoverty_flag": ["prc_pov_final_unreliable_flag", "pr_pov_un", "", "", ""],
    "youth.prc":        ["prc_youth_final", "pr_yth", "siting",\
                         "Percent of the Youth Population", \
                         "The percentage of the population between the age of 18 and 24 years old."],
    "youth_flag":       ["prc_youth_final_unreliable_flag", "pr_yth_un", "", "", ""],
    "disab.prc":        ["prcdisabled_final", "pr_dsb", "siting",\
                         "Percent Disabled Population", \
                         "The percentage of the population that is disabled."],
    "disab_flag":       ["prcdisabled_final_unreliable_flag", "pr_dsb_un", "", "", ""],
    "Tot_EligNonReg_prc_FINAL": ["tot_elignonreg_prc_final", "pr_elno", "siting",\
                         "Eligible Non-Registered Voter Rate", \
                         "The percentage of voting age citizens who are not registered to vote."],
    "TotElig_flag":     ["tot_elignonreg_prc_final_unreliable_flag", "pr_elno_un", "", "", ""],
    "BlackNHL.prc":     ["prc_black", "pr_blk", "population",\
                         "Percent African-American Population", \
                         "Percent of the tract population that is African-American alone&#x002C not Hispanic or Latino."],
    "BlackNHL_flag":    ["prc_black_unreliable_flag", "pr_blk_un", "", "", ""],
    "AsianNHL.prc":     ["prc_asian", "pr_asn", "population",\
                         "Percent Asian-American Population", \
                         "Percent of the tract population that is Asian-American alone&#x002C not Hispanic or Latino."],
    "AsianNHL_flag":    ["prc_asian_unreliable_flag", "pr_asn_un", "", "", ""],
    "Latino.prc":       ["prc_latino", "pr_lat", "population",\
                         "Percent Latino Population", \
                         "The percentage of the population that is Hispanic or Latino."],
    "Latino_flag":      ["prc_latino_unreliable_flag", "pr_lat_un", "", "", ""],
    "WhiteNHL.prc":     ["prc_white", "pr_wht", "population",\
                         "Percent White Population", \
                         "Percent of the tract population that is White alone&#x002C not Hispanic or Latino."],
    "WhiteNHL_flag":    ["prc_white_unreliable_flag", "pr_wht_un", "", "", ""]    
}


# Destination of final output files, for CCEP6 step 18
# This matches the structure expected by the website
final_file_destination_lookup = [
    # We want this file at a top-level directory, common to all counties
    ('indicator_menu_fields.csv',           r'..\..\data'),
    # Geomtery files for website rendering
    ('tracts.json',                         '.'),
    ('tract_centroid_squares.json',         '.'),    
    # Indicator files
    ('indicator_data.csv',                  'indicator_files'),
    ('indicator_data.zip',                  'indicator_files'),
    # Point files
    ('transit_stops.csv',                   'point_files'),
    ('transit_stops_latlononly.csv',        'point_files'),
    ('poi.csv',                             'point_files'),
    ('poi_misc.csv',                        'point_files'),
    ('poi_govish.csv',                      'point_files'),
    ('primary_votecenters_2020.csv',        'point_files'), # Was lks.csv before
    ('primary_pollingplaces_2020.csv',      'point_files'), # New for non-VCA counties
    # Model files
    ('site_area_count.csv',                 'model_files'),    
    ('additional_sites_distance.csv',       'model_files'),
    ('additional_sites_model.csv',          'model_files'),
    ('all_sites_scored.csv',                'model_files'),     
    ('eleven_day_sites.csv',                'model_files'),
    ('four_day_sites.csv',                  'model_files'),
    ('dropbox_sites.csv',                   'model_files'),
    ('dropbox_sites_shp.zip',               'model_files'),
    ('eleven_day_sites_shp.zip',            'model_files'),
    ('four_day_sites_shp.zip',              'model_files'),
    ('additional_sites_model_shp.zip',      'model_files'),
    ('additional_sites_distance_shp.zip',   'model_files'),
    ('all_sites_scored_shp.zip',            'model_files')      
]

# Each csv file listed here also has to be in the list 'final_file_destination_lookup' above,
# with the appropriate destination directory
lks_categories_to_layers = {
    "2020primary_votecenter": "primary_votecenters_2020.csv",
    "2020primary_pollingplace":  "primary_pollingplaces_2020.csv"
}
