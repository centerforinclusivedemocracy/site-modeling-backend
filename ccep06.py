# -*- coding: utf-8 -*-
"""
Created on Fri Jan 31 09:18:08 2020

@author: Gorgonio

# ========================================================
  Overview
# ========================================================
In this script, we create/or place the various files each county needs into a folder
that stores all files for the website.
The external inputs include:
- indicator data from R scripts (tract level)
- Transit data
- Outputs of CCEP3 (scored sites) and CCEP5 (model outputs)

# ============================================================
  Directory usage (derived from DK workflow, but simplified)
# ============================================================

DIR_IP1 = ...CCEPScriptInputs\Indicator_Layers_Tracts\<files_for_all_states> 
DIR_OP1 = ...\CCEPScriptOutputs\CCEP6_Web_Indicator_Layers\<state>_<county_code> -- intermediate 
DIR_OP2 = ...\CCEPScriptOutputs\CCEP6_Final_County_Folders\<state>\data\<county_code> -- final

DIR_OP1 (Intermediate)
- Step 1 creates DIR_OP1
- Steps 2-3 create indicator_menu_fields and indicator_data.csv in DIR_OP1
- Steps 4-8 were dropped on cleanup
- Step 9-10 combines indicator data into tracts shp, and writes indicator_data shp zip to DIR_OP1
- Step 11-13 writes db files (tract, county, squars, pois) to DIR_OP1
- Step 14-16 writes output of CCEP3/CCEP5 to DIR_OP1, and generates site_area_count
- Step 17 copies transit files to DIR_OP1

DIR_OP2
- Step 18 copies over all files into DIR_OP2, in required directory structure

"""

import os
import pandas as pd
import geopandas
import shutil
from shutil import make_archive, copyfile
import ccep_utils as u
import ccep_datavars as dv
import ccep_webvars as wv

# To reduce geometry precision for tracts geojson
from shapely.wkt import loads
import re

# Number of decimal places to use for rounding Double or Float fields
DEC_PLACES = 5

# Round off the number of decimal places in specified dataframe columns to 5
def round_df_decimals(df, col_list, dec_places):
    for col in col_list:
        df[col] = df[col].round(decimals=dec_places)
    return df
    

def run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, state_srid, ip_path, state_code, mts_in_pt05mile, plot=False): 
    
    # ========================================================
    # Set up variables
    # ========================================================
    
    # Schema shortcuts
    admin = dv.admin
    
    # FIPS code used for selection in web indicator data
    fips_code = f"{state_code}{county_code}"
    
    # ========================================================
    # Set up input paths
    # ========================================================
    
    # Input indicator layers by Tract (provided by Laura)
    # We're splitting up input directories by state because CA and CO share a county code, 
    # and there are too many files in which to manually include state in filename
    # Sample -- P:\proj_a_d\CCEP\Vote Center Siting Tool\data\03_FromEC2_Jupyter\Website_Data_091118\Website_Data\Indicator_Layers_022218
    # 
    ip_path_indicator = fr"{ip_path}\Indicator_Layers_Tracts"
        
    # Transit data
    ip_transit_path = fr"{ip_path}\GTFS"
    
    # Model output, from CCEP5
    model_op_ccep5 = fr"{op_path}\CCEP5_Master_County_FLP_Files"    
    
    # Scored sites, from CCEP3
    scored_sites_op_ccep3 = fr"{op_path}\CCEP3_Master_County_FLP_Files"

    # Input LKS data used in scoring sites
    ip_lks_path = fr"{ip_path}\LKS\Master_County_LKS_Data"
    ip_lks_file = fr"{ip_lks_path}\{state}_{county_code}_lks_data_{county_name}.csv"

    # Fixed sites for CO only
    ip_path_fixedsites = f"{ip_path}\FixedSites"
    ip_fixedsites_file = f"{ip_path_fixedsites}\{state}_{county_code}_fixed_sites.csv"         
    
    # Manually clipped tracts for website rendering
    tracts_clipped = fr"{ip_path}\Census_JSONs_ClippedForWeb\Final_Tracts\tracts_{county_code}_{county_name}.json"

    # ========================================================
    # Set up output paths and files
    # ========================================================
        
    # Temporary output indicator layers (pre-processing)
    # Sample -- P:\proj_a_d\CCEP\Vote Center Siting Tool\data\03_FromEC2_Jupyter\Website_Data_091118\Website_Data\Indicator_Layers_For_Web_022218_version\d032618_039 and d032618_039_final
    op_path_indicator_processed = fr"{op_path}\CCEP6_Web_Indicator_Layers\{state}_{county_code}"
    
    # Final output county folders   
    # Sample -- P:\proj_a_d\CCEP\Vote Center Siting Tool\data\03_FromEC2_Jupyter\final_files_Linux_032618\FinalCountyFolders
    op_path_final = fr"{op_path}\CCEP6_Final_County_Folders\{state.upper()}\data\{county_code}"
    
    # Various specific output files
    indic_fields_csv = fr"{op_path_indicator_processed}\indicator_menu_fields.csv"
    indic_data_csv = fr"{op_path_indicator_processed}\indicator_data.csv"
    indic_shp_dir = fr"{op_path_indicator_processed}\indicator_data"
    
    poi_gov_csv = fr"{op_path_indicator_processed}\poi_govish.csv"
    poi_misc_csv = fr"{op_path_indicator_processed}\poi_misc.csv"
    poi_combined_csv = fr"{op_path_indicator_processed}\poi.csv"
    
    site_count_csv = fr"{op_path_indicator_processed}\site_area_count.csv"
    
    transit_stops_csv = fr"{op_path_indicator_processed}\transit_stops.csv"
    transit_stops_latlon_csv = fr"{op_path_indicator_processed}\transit_stops_latlononly.csv"
    fixedsites_csv = fr"{op_path_indicator_processed}\fixed_sites.csv"
    
    tracts_json = fr"{op_path_indicator_processed}\tracts.json"
    # Temporarily remove county file production, since website doesn't use it
    #county_json = fr"{op_path_indicator_processed}\county.json"
    tract_squares_json = fr"{op_path_indicator_processed}\tract_centroid_squares.json"
    

    # ========================================================
    # Process indicator input files - steps 1 - 10 
    # ========================================================
    
    desc = "01 - Set up intermediate variables, and intermediate output directory" 
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # Set up variables
    csv_rename = {} # Rename input indicator data to this, for csv
    shp_rename = {} # Rename input indicator data to this, for shp
    col_retain_set = set() # Retain these columns from input indicator data
    
    # Support native american populations for AZ, only in indicator tract displays
    if state == "az":
        wv.indic_field_map['pct_native'] = ["prc_native", "pr_nat", "population",\
                     "Percent Native America Population", \
                     "The percentage of the population that is Native American."]

    for k,v in wv.indic_field_map.items():
        csv_rename.update({k:v[0]})
        shp_rename.update({v[0]:v[1]})
        if v[0] not in ["fips", "countyfp"]:
            col_retain_set.add(v[0])    

    # Create intermediate output directory    
    if os.path.exists(op_path_indicator_processed):
        print("Intermediate output folder already exists, will over-write files in it")
    else:
        os.mkdir(op_path_indicator_processed)
        print("Created intermediate output folder") 
    
    desc = "02 - Generate indicator_menu_fields.csv" 
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # Create indicator menu file for web usage
    with open(indic_fields_csv,'w') as indicator_menu_fields:
        indicator_menu_fields.write('fieldname,section,title,description\n')
        for k,v in wv.indic_field_map.items():  
            if v[2] != "" and v[3] != "" and v[4] != "":
                indicator_menu_fields.write(f"{v[0]},{v[2]},{v[3]},{v[4]}\n")
            # Since dict contains latino data for section=population, add 
            # another row for section=siting
            if v[0] == ("prc_latino"):
                indicator_menu_fields.write(f"{v[0]},siting,{v[3]},{v[4]}\n")
    indicator_menu_fields.close()
    
    # Sort indicator file
    indic_df = pd.read_csv(indic_fields_csv)
    indic_df = indic_df.sort_values(by=['section','title'])
    indic_df.to_csv(indic_fields_csv, index=False)
    
    desc = "03 - Generate indicator_data.csv" 
    print(f"{u.getTimeNowStr()} Run: {desc}")    

    merged_files = pd.DataFrame()
    couldnt_subset_indic_data = []
    for fl in os.listdir(ip_path_indicator):
        if fl.endswith(f"{state.upper()}.csv"):
            print(f"Reading in {fl}...")
            ip_indic_df = pd.read_csv(f"{ip_path_indicator}\{fl}")
    
            # rename to what csv expects
            ip_indic_df = ip_indic_df.rename(columns=csv_rename)
    
            # Extract by county code (3 digit) or fips (5 digit)
            # May not be needed for files past first, merge on geoid subsets it
            if "fips" in ip_indic_df.columns:
                # extract 5 dig code
                ip_indic_df = ip_indic_df[ip_indic_df.fips == int(fips_code)]
            elif "countyfp" in ip_indic_df.columns:
                # extract 3 digit code
                ip_indic_df = ip_indic_df[ip_indic_df.countyfp == int(county_code)]
            else:
                couldnt_subset_indic_data.append(fl)
                            
            # drop unwanted cols, including county. Retain only what's in col_retain_set
            ip_indic_df = ip_indic_df[[col for col in ip_indic_df.columns if col in col_retain_set]]
    
            # Create or join with merged file
            if merged_files.shape[0] == 0:
                merged_files = ip_indic_df
                # Insert county code after geoid
                merged_files.insert(1,"countyfp",int(county_code))
            else:
                merged_files = merged_files.merge(ip_indic_df, on='geoid',how='left')
            
            # at end, compare columns in old data vs new data
    
    # Round off decimals to 5 places for all Double/Float fields, to reduce file size
    indic_cols = merged_files.columns.tolist()
    indic_cols_to_remove = []
    for ic in indic_cols:
        if ic in ['geoid', 'countyfp', 'pop10'] or ic.endswith('_unreliable_flag'):
            indic_cols_to_remove.append(ic)
    for icr in indic_cols_to_remove:
        indic_cols.remove(icr)
    merged_files = round_df_decimals(merged_files, indic_cols, DEC_PLACES)
    
    # Write indicator data to csv
    merged_files.to_csv(indic_data_csv,index=False)   
    
    desc = "04-08 - ... nothing! Not needed after code cleanup."
    
    desc = "09 - Merge indicator data to census tracts, prep tracts columns for shapefile generation" 
    print(f"{u.getTimeNowStr()} Run: {desc}")

    # Note: This could also be updated to use county-specific tracts
    tracts = u.make_gpd(db.table2df(admin,f"{state}_tracts"),srid)
    # Pull out tracts for just this county
    tracts = tracts[tracts.countyfp == county_code]
        
    # Remove polygons over water, by removing those with aland <= 0
    tracts['aland'] = tracts['aland'].astype('int64')    
    tracts = tracts[tracts.aland > 0]
    
    # Renamed lsad to namelsad to match data
    tracts = tracts.drop(['countyfp','name','namelsad','aland' ,'awater'], axis=1)
    
    if plot:
        tracts.plot()
    
    # Replaced int with int64 to avoid overflow error "int too large to convert to C long",
    # which happens because C long is 32-bit on Windows
    # https://stackoverflow.com/questions/38314118/overflowerror-python-int-too-large-to-convert-to-c-long-on-windows-but-not-ma
    tracts['geoid'] = tracts.geoid.astype('int64')
    
    # The int is needed only for the merge. Later it is put back to string.    
    tracts = tracts.merge(merged_files, on='geoid')

    # Rename columns (again!!)
    tracts = tracts.rename(columns=shp_rename)
    
    
    desc = "10 - Write tracts dataframe to indicator_data.zip shapefile" 
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    if not os.path.exists(indic_shp_dir):
        os.makedirs(indic_shp_dir)    
    
    # In original DK code, just this 1 field was converted
    # Presuming conversion was to preserve leading 0s
    tracts['geoid'] = tracts['geoid'].astype(str) 
    # Same behavior with (str) or ('str') - opening dbf in excel calls out quote before number

    # Needed this, otherwise error: Invalid field type <class 'decimal.Decimal'>
    tracts['shape_leng'] = tracts['shape_leng'].astype('float64')
    tracts['shape_area'] = tracts['shape_area'].astype('float64')
   
    # Write tracts to shapefile (default format, if not specified)   
    # When only path is specified, the shp filename matches that of the last dir in path
    tracts.to_file(indic_shp_dir)

    # Note, if also writing to csv for debugging, drop geom column, otherwise 
    # commas break on opening in excel
    
    # Create zip of shapefile dir
    make_archive(
      indic_shp_dir,      # name of output file
      'zip',        # the archive format - or tar, bztar, gztar 
      root_dir=indic_shp_dir) #archive made from this dir
    
    # Delete shapefile contents, and directory
    # Temporarily commented, to load into GIS software for verification
    #for item in os.listdir(indic_shp_dir):
    #    os.remove(os.path.join(indic_shp_dir, item))
    #os.removedirs(indic_shp_dir)

    # ========================================================
    # Process files from postgres database - steps 11 - 13
    # ========================================================
    
    desc = "11 - Save tract geojsons" 
    print(f"{u.getTimeNowStr()} Run: {desc}")

    tracts = u.make_gpd(db.table2df(ssl,f"{county_name}_tracts"), srid)
    # Needed this conversion, otherwise error: Invalid field type <class 'decimal.Decimal'>
    tracts['shape_leng'] = tracts['shape_leng'].astype('float64')
    tracts['shape_area'] = tracts['shape_area'].astype('float64')
    tracts['aland'] = tracts['aland'].astype('int64')
    tracts['awater'] = tracts['awater'].astype('int64')    
    
    # Remove polygons over water, by removing those with aland <= 0
    tracts = tracts[tracts.aland > 0]
    
    # If a manually clipped file exists, replace with that, before optimizing and writing out
    if os.path.exists(tracts_clipped) and os.path.isfile(tracts_clipped):
        tracts = geopandas.read_file(tracts_clipped)
    
    # To reduce file size, drop all columns except GEOID, which is the only one the website uses.
    tracts = tracts[['geoid', 'geometry']]

    # To reduce file size, reduce precision of geometry  for geojson to 5 dec places
    # Reference: https://gis.stackexchange.com/questions/321518/rounding-coordinates-to-5-decimals-in-geopandas
    simpledec = re.compile(r"\d*\.\d+")
    def mround(match):
        return "{:.5f}".format(float(match.group()))
    tracts.geometry = tracts.geometry.apply(lambda x: loads(re.sub(simpledec, mround, x.wkt)))
    
    tracts.to_file(tracts_json, driver='GeoJSON')

    # Currently the county data is used in intermediate processing below, but not by the website
    # So produce the data for internal use, but don't write to output
    # If we do produce it for the webstite in future, we need to generate it by 
    # dissolving tracts, so that the county boundary doesn't include water polygons, 
    # and matches the tract boundary
    county = u.make_gpd(db.table2df(ssl,f"{county_name}_county"), srid)
    # Needed this conversion, otherwise error: Invalid field type <class 'decimal.Decimal'>
    county['shape_leng'] = county['shape_leng'].astype('float64') 
    county['shape_area'] = county['shape_area'].astype('float64') 
    county['aland'] = county['aland'].astype('int64') 
    county['awater'] = county['awater'].astype('int64')         
    # Temporarily removed, until website requires it
    #county.to_file(county_json,driver='GeoJSON')


    desc = "12 - Create the small square symbols for the map" 
    print(f"{u.getTimeNowStr()} Run: {desc}")
    # We don't need this after the website was updated to use hatching instead
    # of the black squares. Leaving it in here for future reference, just in case!
    '''    
    # The 150m unit is for the unreliability squares
    centroid_file = f"{county_name}_tract_centroid_{state_srid}"
    qry_txt = f"""
    drop table if exists {ssl}.{centroid_file};
    create table {ssl}.{centroid_file} as 
    select cntrd.geoid, st_transform(ST_Expand(st_transform(cntrd.geom, {state_srid}):: geometry, 150),{srid}) geom
    from 
        (select geoid, st_centroid(geom) geom 
        from {ssl}.{county_name}_tracts
        where aland > 0
        )  as cntrd
    """    
    db.qry(qry_txt)
    
    tract_centroid_squares = u.make_gpd(db.table2df(ssl, centroid_file), srid)
    tract_centroid_squares.to_file(tract_squares_json,driver='GeoJSON')
    '''


    desc = "13 - Generate POI csv files" 
    print(f"{u.getTimeNowStr()} Run: {desc}")    
    
    govish_pois = u.make_gpd(db.table2df(ssl,f"{county_name}_pois_gov"),srid)    
    govish_pois['lon'] = govish_pois.geometry.x
    govish_pois['lat'] = govish_pois.geometry.y    
    govish_pois = govish_pois.drop(['geometry', 'gid'],axis=1)    
    govish_pois = round_df_decimals(govish_pois, ['lat', 'lon'], DEC_PLACES)    
    govish_pois.to_csv(poi_gov_csv, index='False', encoding='utf-8')

    misc_pois = u.make_gpd(db.table2df(ssl,f"{county_name}_pois_misc"),srid)    
    misc_pois['lon'] = misc_pois.geometry.x
    misc_pois['lat'] = misc_pois.geometry.y    
    misc_pois = misc_pois.drop(['geometry', 'gid'],axis=1)
    misc_pois = round_df_decimals(misc_pois, ['lat', 'lon'], DEC_PLACES)    
    misc_pois.to_csv(poi_misc_csv, index=False, encoding='utf-8')
    
    # Combine both Gov and Misc POIs into one file
    misc_pois.append(govish_pois).to_csv(poi_combined_csv, index=False, encoding='utf-8') 
    
    # ========================================================
    # Process files from CCEP3 and CCEP5 - steps 14 - 16
    # ========================================================
        
    desc = "14 - Create buffers of suitable site points for shapefile" 
    print(f"{u.getTimeNowStr()} Run: {desc}")    
    
    centroid_file = f"{state}_{county_code}_final_centroid_buffer"
    half_length_of_side = int(mts_in_pt05mile)/2

    # Create 800m squares around suitable sites, to match the squares on the website
    # _suitable_sites_processed_final is created in CCEP3
    # 800m square length is picked to match the dimensions of the processing grid    
    qry_txt = f"""
        drop table if exists {fssl}.{centroid_file};
        create table {fssl}.{centroid_file} as
        select sites.idnum,             
            st_transform(ST_Expand(st_transform(sites.geom, {state_srid}):: geometry, {half_length_of_side}),{state_srid}) geom
        from {fssl}.{state}_{county_code}_suitable_sites_processed_final as sites
    """
    db.qry(qry_txt)
    
    # Note: DK code had backup logic to use _suitable_sites_final, which was generated
    # in CCEP1, with a comment that it wasn't going to be used. So for consistency
    # we are sticking with the file _suitable_sites_processed_final from CCEP3
    
    # Load the buffered circles
    county_buffered_circles = u.make_gpd(db.table2df(fssl, centroid_file), state_srid)


    desc = "15 - From suitable site (ccep3) and model output (ccep5) files, " + \
    "\n- (a) join columns to buffer, " + \
    "\n- (b) output subset of cols to csv in '_processed' dir, " + \
    "\n- (c) generate and write counts to site_area_count csv"
    print(f"{u.getTimeNowStr()} Run: {desc}")    
        
    # Merge (combine) columns from files with buffer dataframe
    # And create copy of files to op _processed folder, subset by columns
    buffered_files = {}
    file_counts = []
    
    # Create a list of columns that will be rounded to 5 dec places in the model csvs
    cols_to_round = wv.csv_keep_cols.copy()
    cols_to_round.remove('idnum')

    for k in wv.model_output_files:
        #print(k) # For debugging
        if k == "all_sites_scored.csv":
            dir = scored_sites_op_ccep3
        else:
            dir = model_op_ccep5
        ip_file = f"{dir}\{state}_{county_code}_{k}"
        if state == "co":
            if k.startswith("eleven"):
                k = k.replace("eleven", "fifteen")
            if k.startswith("four"):
                k = k.replace("four", "one")
        if state == "tx":
            if k.startswith("eleven"):
                k = k.replace("eleven", "early_voting")
            if k.startswith("four"):
                k = k.replace("four", "election")                
        if state == "az":
            # Replace four with seven first, otherwise fourteen becomes seventeen
            if k.startswith("four"):
                k = k.replace("four", "seven")                                		
            if k.startswith("eleven"):
                k = k.replace("eleven", "fourteen")
        op_file = f"{op_path_indicator_processed}\{k}"
        label = k[0:-4]
        
        # Process for shapefile
        temp_df_shp = pd.read_csv(ip_file)
        if 'geometry' in temp_df_shp.columns:
            temp_df_shp = temp_df_shp.drop('geometry',axis=1)
        temp_df_shp = temp_df_shp.rename(columns={'COUNTYFP10':'county',
                                          'center_score':'vc_score',
                                          'droppoff_score':'db_score'})        
        temp_df_shp = county_buffered_circles.merge(temp_df_shp, on='idnum')
        #print (temp_df_shp.shape) # For debugging
        
        # TODO: Instead of writing this data to memory, check if the shp from step 16
        # can be created here. Memory wasn't an issue for large counties though, 
        # so not critical to fix, merely efficiency improvement
        buffered_files[label] = temp_df_shp
        
        # Process for csv
        # Does not fail if dataframe is empty (though writing to shp does)
        temp_df_csv = pd.read_csv(ip_file)
        temp_df_csv = temp_df_csv[temp_df_csv.center_score.notnull()]
        temp_df_csv = temp_df_csv[wv.csv_keep_cols]
        file_counts.append([label,temp_df_csv.shape[0]])
        
        # Round off all non-integers to 5 decimal places
        temp_df_csv = round_df_decimals(temp_df_csv, cols_to_round, DEC_PLACES)
        temp_df_csv.to_csv(op_file, index=False)

    site_area_count = pd.DataFrame(file_counts,columns=['file','count'])    
    site_area_count.to_csv(site_count_csv,index=False)    


    desc = "16 - Create zipped shapefile folders" 
    print(f"{u.getTimeNowStr()} Run: {desc}")    
    
    skip_files= []
    for label in buffered_files:
        temp_df = buffered_files[label][wv.shp_keep_cols]
        
        if len(temp_df) > 0:
            # Round off all non-integers to 5 decimal places
            temp_df = round_df_decimals(temp_df, ['vc_score', 'db_score'], DEC_PLACES)
            
            shp_dir = f"{op_path_indicator_processed}\{label}" 
            if not os.path.exists(shp_dir):
                os.makedirs(shp_dir)
            # Save df to shapefile
            temp_df.to_file(shp_dir)
    
            # Create zip 
            make_archive(
              f"{shp_dir}_shp", # name of output file
              'zip',            # the archive format - or tar, bztar, gztar 
              root_dir=shp_dir) # zip created from this dir
    
            # Delete shapefile contents, and directory
            # Temporarily commented, to load into GIS software for verification
            #for item in os.listdir(shp_dir):
            #    os.remove(os.path.join(shp_dir, item))
            #os.removedirs(shp_dir)
            
            print(f"Created {label}_shp.zip")
        else:
            skip_files.append(f"{label}.csv")
            print(f"\n***** {label} dataframe was empty and will be skipped from output generation\n")  
    
    # ========================================================
    # Process transit files - step 17
    # ========================================================
    desc = "17 - Clean up, combine and transfer transit files" 
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    transit_dfs = []
    file_prefix = f"{state}_{county_code}"
    file_suffix = ".csv"
    for f in os.listdir(ip_transit_path):
        if f.endswith(file_suffix) and f.startswith(file_prefix):
            print(f"Reading in transit file {f}")
            temp_df = pd.read_csv(f"{ip_transit_path}\{f}")
            transit_dfs.append(temp_df) ##  dataframe to list
    
    # If an empty transit file is available (just header, no data), then it is counted here
    # i.e. len will count 1 for each available file, whether empty or not
    if len(transit_dfs) > 0:
        all_transit = transit_dfs[0]
        for df in transit_dfs[1:]:
            all_transit = all_transit.append(df)
    
        # Select subset of columns, and rename
        all_transit = all_transit[['provider', 'stop_lat', 'stop_lon','num_stops_per_week','score']]
        all_transit.columns = ['provider', 'lat', 'lon','num_stops_per_week','score']
    
        # Add index and id
        all_transit['id'] = all_transit.index
        
        # Flag (drop?) points that happen to fall outside the county
        transit_df = u.make_gpd(all_transit, srid, fromPostgis=False)
        transit_count_before = transit_df.shape[0]
        
        if transit_count_before == 0:
            # No GTFS available, save empty file with header to csv
            # Do this here, because header is lost in checking against county boundary
            # and we need header for the website
            transit_df = transit_df.drop(['id', 'geometry'], axis=1)
            transit_df.to_csv(transit_stops_csv, index=False)
            
            transit_df = transit_df.drop(['provider', 'num_stops_per_week', 'score'], axis=1) 
            transit_df.to_csv(transit_stops_latlon_csv, index=False)
            
            transit_count_after = 0
        else:
            # Use county var that was already created in step 11    
            transit_df['in_county'] = transit_df['geometry'].apply(lambda x: x.intersects(county['geometry'][0]))
            transit_df = transit_df[transit_df.in_county]
            transit_count_after = transit_df.shape[0]
            
            # Clean up transit file to reduce size, generate output file
            transit_df = transit_df.drop(['id', 'geometry', 'in_county'], axis=1)
            transit_df = round_df_decimals(transit_df, ['lat', 'lon'], DEC_PLACES)
            transit_df.to_csv(transit_stops_csv, index=False)

            # Remove all additional columns for web rendering, except lat lon
            transit_df = transit_df.drop(['provider', 'num_stops_per_week', 'score'], axis=1) 
            transit_df.to_csv(transit_stops_latlon_csv, index=False)
        
            if plot:
                ax = county.plot()
                transit_df.plot(ax=ax,color='yellow')
    else:
        print(f"No transit file found for {file_prefix}")
    
    # ========================================================
    # Copy over LKS files - step 18
    # ========================================================
    desc = "18 - Create files from LKS categories" 
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    if os.path.exists(ip_lks_file) and os.path.isfile(ip_lks_file):
        lks_df = pd.read_csv(ip_lks_file)
        for k,v in wv.lks_categories_to_layers.items():
            lks_df_subset = lks_df[lks_df.category == k]
            
            # Drop category after subsetting, not needed in output
            lks_df_subset = lks_df_subset.drop(['category'], axis=1)
            # Round lat and lon to 5 dec places to reduce file size
            lks_df_subset = round_df_decimals(lks_df_subset, ['lat', 'lon'], DEC_PLACES)
            
            op_subset = fr"{op_path_indicator_processed}\{v}"
            print(f"Copying LKS file from {ip_lks_file}, for category {k}, to {op_subset}")
            lks_df_subset.to_csv(op_subset, index=False)
    else:
        print(f"No LKS file found at {ip_lks_file}")

    
    # ========================================================
    # Copy over LKS files - step 18
    # ========================================================
    desc = "19 - Colorado only - Copy Fixed Site files to output directory" 
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    if state == "co":                
        # Copy fixed sites to intermediate processing directory
        if os.path.exists(ip_fixedsites_file) and os.path.isfile(ip_fixedsites_file):
            print(f"Copying Fixed Sites file from {ip_fixedsites_file} to {fixedsites_csv}")
            fs_df = pd.read_csv(ip_fixedsites_file)
            # Reduce file size by dropping extraneous columns, rounding lat-lon to 5 dec places
            fs_df = fs_df.drop(['county', 'FIPS'], axis=1)
            fs_df = round_df_decimals(fs_df, ['lat', 'lon'], DEC_PLACES)
            fs_df.to_csv(fixedsites_csv)            
        else:
            print(f"No Fixed Sites file found at {ip_fixedsites_file}")

        # Add fixed sites to the list of files that must be copied over to the final output directory
        wv.final_file_destination_lookup.append(('fixed_sites.csv', 'point_files'))        
        
    else:
        print("Since state is not CO, fixed sites don't need to be copied over to output")
        
    # ========================================================
    # Export, validate for gaps - steps 19-20
    # ========================================================
        
    desc = "20 - Final data export for website" 
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # Create directory for county
    if not os.path.exists(op_path_final):
        os.mkdir(op_path_final)

    # Based on lookup list, create sub-directories and copy files        
    files_not_copied = []
    for fl in wv.final_file_destination_lookup:
        filename = fl[0]
        if state == "co":
            if filename.startswith("eleven"):
                filename = filename.replace("eleven", "fifteen")
            if filename.startswith("four"):
                filename = filename.replace("four", "one")        
        if state == "tx":
            if filename.startswith("eleven"):
                filename = filename.replace("eleven", "early_voting")
            if filename.startswith("four"):
                filename = filename.replace("four", "election")                        
        if state == "az":
            # Replace four with seven first, otherwise fourteen becomes seventeen
            if filename.startswith("four"):
                filename = filename.replace("four", "seven")                        
            if filename.startswith("eleven"):
                filename = filename.replace("eleven", "fourteen")
        op_p = os.path.join(op_path_final, fl[1])
        op_f = os.path.join(op_p, filename)
        if not os.path.exists(op_p):
            os.mkdir(op_p)        
        source = os.path.join(op_path_indicator_processed, filename)
        destination = op_f
        try:
            shutil.copyfile(source, destination)
        except IOError:
            files_not_copied.append(fl[0])

    print(f"\nFile copy complete. Data can be found in {op_path_final}\n")
    
    desc = "21 - Validation checks" 
    print(f"{u.getTimeNowStr()} Run: {desc}")

    if len(skip_files) > 0:
        print(f"- The following files were empty (in step 16) and will be missing in the output: {skip_files}")    
    else:
        print("- No files were found to be empty in step 16")
    
    # Validation not repeated for transit_stops_latlononly.csv, since it is derived from transit_stops.csv
    if "transit_stops.csv" in files_not_copied:
        print(f" - Missing transit data for {county_code}. Please review data inputs and confirm.")
    elif transit_count_before == 0 and transit_count_after == 0: 
        print(f"- Transit file existed but was empty. Transit output will be empty (only header present)." + \
              " Please review data inputs and confirm.")    
    elif transit_count_after < transit_count_before: 
        print(f"- {transit_count_before - transit_count_after} transit stops" + \
              "fell out of the county boundary (in step 17) and were dropped.")    
    else: 
        print("- Transit data exists, and no transit stops were dropped in step 17")

    for k,v in wv.lks_categories_to_layers.items():
        if v in files_not_copied:
            print(f"- Missing LKS data for {county_code}, category {k}. Please review data inputs and confirm.")
        else: 
            print(f"- LKS file exists for category {k} and was copied over in step 18")

    if state == "co":
        if "fixed_sites.csv" in files_not_copied:
            print(f"- Missing Fixed Sites data for {county_code}. Please review data inputs and confirm.")
        else: 
            print("- Fixed Sites data exists and was copied over in step 19")

    if len(files_not_copied) > 0:
        print(f"- The following files were not copied (in step 20): {files_not_copied}. " + \
              "Verify if the file is missing or has other issues")    
    else:
        print("- All expected files were copied over in step 20")
        
    if len(couldnt_subset_indic_data) > 0:
        print(f"- Indicator data could not be subset by county/fips code " + \
              f"(in step 3), verify variables and joins for: {couldnt_subset_indic_data}")
    else:
        print(f"- All input indicator data could be subset and extracted for this county in step 3")
