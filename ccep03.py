# -*- coding: utf-8 -*-
"""
Created on Thu Jan  2 14:21:52 2020

@author: Gorgonio

This script takes the scored sites produced by the R scripts, and limits them based
on constraints on population, road length, number of POIs, and optionally, type of POI.

If any LKS data is available for the county, scored sites near the LKS points 
are flagged to be included within the constraints.
"""

import os
import pandas as pd
import ccep_utils as u
from scipy.spatial import KDTree


def run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, ip_path, plot=False): 
    
    # Set up path and file variables...
    
    # Output of R scripts, containing scored sites
    ip_path_R = f"{op_path}\R_Master_County_Scored_Sites" 
    ip_ss_file = f"{ip_path_R}\{state}_{county_code}_scored_sites_raw.csv" 
    
    # LKS data, optional
    # Note from DK: These are sites identified as being a location that must be included as a potential site, 
    # regardless of the constraints applied by this process (except the requirement of roads being present). 
    # File has three columns (name, lat, lon).
    ip_path_lks = f"{ip_path}\LKS\Master_County_LKS_Data"
    ip_lks_file = f"{ip_path_lks}\{state}_{county_code}_lks_data_{county_name}.csv"     

    # Fixed sites for CO only
    ip_path_fixedsites = f"{ip_path}\FixedSites"
    ip_fixedsites_file = f"{ip_path_fixedsites}\{state}_{county_code}_fixed_sites.csv"     
    
    # Output of this CCEP3 script
    op_path_ccep3 = f"{op_path}\CCEP3_Master_County_FLP_Files" 
    op_file = f"{op_path_ccep3}\{state}_{county_code}_all_sites_scored.csv"
    
    # Final suitable sites for DB
    fssl_file = f"{state}_{county_code}_suitable_sites_processed_final"
    
    # Start processing...
    
    # Load sites scored by R scripts
    desc = "01 - Read in scored sites, produced by R scripts"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    scored_sites = u.make_gpd(pd.read_csv(ip_ss_file),srid=srid,fromPostgis=False)
    # print(scored_sites.shape) # Print number of rows and columns. for verification

    desc = "02 A - Read in Local Knowledge Sites (LKS) data, if it exists"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    lks_data_found = False
    if os.path.exists(ip_lks_file):
        lks_data_found = True
        lks_data = u.make_gpd(pd.read_csv(ip_lks_file),srid=srid,fromPostgis=False)
        if plot:
            ax = scored_sites.plot(figsize=(15,15), color='gray')
            lks_data.plot(ax=ax)
    else:
        print("No LKS Data found. Either doesn't exist or file named incorrectly.")

    desc = "02 B - Read in Fixed Sites data, if it exists (Colorado only)"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    if state != "co":
        print(f"Processing {state}, not colorado, so fixed sites logic will be skipped")
    else:
        fixedsites_found = False
        if os.path.exists(ip_fixedsites_file):
            fixedsites_found = True
            fixedsites_alldata = u.make_gpd(pd.read_csv(ip_fixedsites_file),srid=srid,fromPostgis=False)
            if plot:
                ax = scored_sites.plot(figsize=(15,15), color='gray')
                fixedsites_alldata.plot(ax=ax)
        else:
            print("No Fixed Sites data found. Either doesn't exist or file named incorrectly.")


    # If LKS data exists, attach it to the point grid, i.e. find 2 scored sites (grid cells) that are
    # nearest to each LKS point, record their id, and flag them as LKS, by setting new lks_data field =1
    desc = "03 A - If LKS exists, flag 2 scored sites nearest to each LKS site"
    print(f"{u.getTimeNowStr()} Run: {desc}")    
    nearest_scored_sites = {}
    k_nearest_sites = 2
    if lks_data_found:
        # Set up coords for scored sites
        # Output format of zip() changed in python 3, hence list() needed
        zip_list = list(zip(scored_sites.lon, scored_sites.lat)) 
        scored_site_coords = zip_list
        # Load the KDTree with these coordinates
        tree = KDTree(scored_site_coords)    
        # Set up the search data, i.e. LKS coordinates
        lks_coords = list(zip(lks_data.lon, lks_data.lat))
    
        # Do the search
        for idx, site in enumerate(lks_coords):
            # Note: Distance calculation is done in degrees (in WGS84)
            distances, indices = tree.query(site,k=k_nearest_sites) 
            for loop_idx, scored_site_idx in enumerate(indices):
                # print('lks site', lks_data.iloc[idx]['name'], 'near_site', scored_sites.iloc[scored_site_idx].idnum, distances[loop_idx])
                nearest_scored_sites[scored_sites.iloc[scored_site_idx].idnum] = [lks_data.iloc[idx]['name'],distances[loop_idx] ]
    
        # Note from DK: Yellow indicates the nearest sites to the LKS site, 
        # blue point indicates the coordinates of the LKS site 
        if plot:
            ax = scored_sites.plot(figsize=(15,15), color='gray')
            # Even though keys() is not converted to a list for python3, this code
            # correctly handles it, nad pulls out scored sites with these ids
            scored_sites[scored_sites.idnum.isin(nearest_scored_sites.keys())].plot(markersize=100, alpha=.5, color='yellow', ax=ax)
            lks_data.plot(ax=ax)

    # Attach the LKS data if any was found (set field to 1), otherwise mark with 0 to indicate not LKS Site
    scored_sites['lks_data'] = 0
    scored_sites.loc[scored_sites.idnum.isin(list(set(nearest_scored_sites.keys()))),'lks_data'] =1

    # If Fixed sites data exists, attach it to the point grid, i.e. find 1 scored site (grid cells) that is
    # nearest to each Fixed Site point, record its id, and flag it as a Fixed Site, 
    # by setting new fixed_site field =1
    desc = "03 B - If Fixed Site exists, flag 1 scored site nearest to each Fixed site"
    print(f"{u.getTimeNowStr()} Run: {desc}")

    if state != "co":
        print(f"Processing {state}, not colorado, so fixed sites logic will be skipped")
    else:
        fixedsites_types = ["fs_1day", "fs_15day"]
        
        # For each type of fixed site... 
        for fs in fixedsites_types:
            # Subset data, pick rows where fixed site type = 1
            fixedsites_data = fixedsites_alldata[fixedsites_alldata[fs] == 1]
            
            nearest_scored_sites = {}
            k_nearest_sites = 1
            if fixedsites_found and fixedsites_data.shape[0] > 0:
                # Set up coords for scored sites
                # Output format of zip() changed in python 3, hence list() needed
                zip_list = list(zip(scored_sites.lon, scored_sites.lat)) 
                scored_site_coords = zip_list
                # Load the KDTree with these coordinates
                tree = KDTree(scored_site_coords)    
                # Set up the search data, i.e. Fixed Sites coordinates
                fixedsites_coords = list(zip(fixedsites_data.lon, fixedsites_data.lat))
            
                # Do the search
                for idx, site in enumerate(fixedsites_coords):
                    # Note: Distance calculation is done in degrees (in WGS84)
                    distances, indices = tree.query(site,k=k_nearest_sites) 
                    # Since k=1, these are not lists, so make them (to keep below code consistent with LKS)
                    distances = [distances]
                    indices = [indices]
                    for loop_idx, scored_site_idx in enumerate(indices):
                        nearest_scored_sites[scored_sites.iloc[scored_site_idx].idnum] = [fixedsites_data.iloc[idx]['name'],distances[loop_idx] ]
            
                # Note from DK: Yellow indicates the nearest sites to the Fixed sites, 
                # green point indicates the coordinates of the Fixed site 
                if plot:
                    ax = scored_sites.plot(figsize=(15,15), color='gray')
                    # Even though keys() is not converted to a list for python3, this code
                    # correctly handles it, nad pulls out scored sites with these ids
                    scored_sites[scored_sites.idnum.isin(nearest_scored_sites.keys())].plot(markersize=100, alpha=.5, color='yellow', ax=ax)
                    fixedsites_data.plot(ax=ax)
        
            # Attach the Fixed Site data if any was found (set field to 1), otherwise mark with 0 to indicate not Fixed Site
            scored_sites[fs] = 0
            scored_sites.loc[scored_sites.idnum.isin(list(set(nearest_scored_sites.keys()))),fs] = 1


    # Add columns for some selected types of POIs, and flag as 1 if there's a match
    # This is to be used if you want to include all sites with this POI in the output
    # Note from DK: Assume the selected types of Points of Interest are universally reasonable 
    # as vote sites for counties, though they can be manually edited if desired.
    desc = "04 - For selected POI types, add fields and flag as 1 if site is that type of POI"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    # TODO: Warning in output:  value is trying to be set on a copy of a slice from a DataFrame
    for t in ['fire_station', 'library', 'town_hall', 'public_building', \
              'school', 'community_centre', 'arts_centre', 'college', 'university']:
        scored_sites[t] = 0
        scored_sites[t].loc[scored_sites.poi_classes.notnull()] = \
            [1 if t in i else 0 for i in scored_sites[scored_sites.poi_classes.notnull()].poi_classes]

    # Create constraints
    # Note from DK: There are a variety of constraints we could apply to determine 
    # if the site is feasible. We are using the number of pois, the presence of 
    # population, road density and the presence of LKS sites (if they exist).
    desc = "05 - Create constraint queries, on road length, population, number of POIs, LKS data, and optionally POI types"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # For LA, we need to reduce the size of the distance matrix, by reducing the number of sites.
    if county_name == "los_angeles":
        min_pop = 50
        print("Using higher min population for LA to reduce size of distance matrix")
    else:
        min_pop = 0
    
    # Q1: Note from DK: Road density is of .07 or above, and the population is greater than 0 
    # Note from DK: Assume that .07 road density (length) is a universally reasonable level of length 
    # that indicates an area with great concentration of built evnrionment, or a location that could 
    # reasonably host a vote site. 
    #
    # Note: Length above is in degrees (since layer is in WGS84) - consistent with generation in CCEP1
    # Updated to use block_prop_pop which is population for that grid cell, instead of pop10 
    # which is sum of populations from any/all blocks that intersect that grid cell
    q1 = ((scored_sites.road_length >= 0.07 ) & (scored_sites.block_prop_pop > min_pop))
    
    # Q2: Note from DK: Some minimum road density, at Least 2 POIS, and some population
    # Note: Length above is in degrees (since layer is in WGS84) - consistent with generation in CCEP1
    q2 = ((scored_sites.road_length >= 0.01)  & \
          (scored_sites.poi_classes.notnull()) & (scored_sites.num_poi > 1) & \
          (scored_sites.block_prop_pop > min_pop))
    
    # Q3: Is an LKS site
    q3 = (scored_sites.lks_data > 0 )
    
    # Q4: Types of POIs
    q4 = ((scored_sites.fire_station == 1) |  (scored_sites.library == 1) | (scored_sites.town_hall == 1) | \
          (scored_sites.public_building == 1) |  (scored_sites.school == 1) | (scored_sites.community_centre == 1) |
          (scored_sites.arts_centre == 1) |  (scored_sites.college == 1) | (scored_sites.university == 1) 
          ) & (scored_sites.block_prop_pop > min_pop)
    
    if state == "co":
        # Q5: Is a FIXED site
        q5 = (scored_sites.fs_1day > 0) | (scored_sites.fs_15day > 0)
        
        limit_query = (q1 | q2 | q3 | q4 | q5)
    else: # CA / TX / AZ
        # If Q4 is included, the dataset will increase to include sites with selected POI types, 
        # that didn't meet other criteria
        # Don't include q4 for LA to reduce the size of the distance matrix
        if county_name == "los_angeles":
            limit_query = (q1 | q2 | q3)
            print("Skipping q4 for LA to reduce size of distance matrix")
        else:
            limit_query = (q1 | q2 | q3 | q4)

    # print(scored_sites[limit_query].shape) # Print number of rows and columns. for verification
    
    if plot:
        ax = scored_sites.plot(figsize=(15,15), color='gray')
        scored_sites[limit_query].plot(color='yellow',markersize=30,ax=ax)
        if lks_data_found:
            lks_data.plot(ax=ax,color='blue',markersize=20)
        if fixedsites_found:            
            fixedsites_data.plot(ax=ax,color='green',markersize=20)
        
    # Write output to CSV
    desc = "06 - Subset data on constraints, and write to CSV"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    scored_sites[limit_query].to_csv(op_file,index=False)
    
    # Save data to DB, for later review in QGIS
    desc = "07 - Write the subset data to DB, add geometry to it"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    qry_text = f"""drop table if exists {fssl}.{fssl_file};"""
    db.qry(qry_text)
    to_db_df = scored_sites[limit_query].drop('geometry',axis=1)        
    db.df2table(to_db_df,fssl,fssl_file)
    qry_text = f"""
        alter table {fssl}.{fssl_file} add column geom geometry;
        update {fssl}.{fssl_file} set geom = st_setsrid(st_point(lon, lat),{srid}) ;
        """
    db.qry(qry_text)
