# -*- coding: utf-8 -*-
"""
Created on Mon Dec 23 15:02:43 2019

@author: Gorgonio

Notes from DK (all 3 sections below):

**Purpose of this Notebook:** 
    1. Generate a variety of county specific geospatial files in the postgres database
    2. Generate POIs for each county
    3. Generate a suitable site layer for each county: Suitable sites are those areas
       where we think a vote site could feasibly be located.     
       
**NOTES** 
    1. Part of the process involves creating a grid over the county - wherever 
       possible it is best to not recreate the grid but rather update the files 
       that come after the grid this allows for the same ID field across 
       iterations and the option to compare differences. 
    2. This code will automatically overwrite old files - if you wish to retain 
       an earlier version - you must rename that table in the database, or 
       save it in some other format. We overwrite files to reduce clutter and 
       simplify the process of generating these files

**Assumptions**
    * A site can only be suitable if roads are available, as people need to be 
      able to travel to a site. 
    * Points of Interest indicate human activity and built environemnt 
      concentration, thus indicating potential sites. 
    * Certain types of points of interest are more likely to be associated with 
      potential vote sites than others. 
    * A half mile grid is decent unit for spatially segmenting space, provides 
      reasonable granularity while also providing efficient computation.               
"""

import time
import pandas as pd
import numpy as np
import ccep_utils as u
import ccep_datavars as dv

def run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, state_srid, mts_in_pt05mile):
    # Requires osm.XX_roads, osm.XX_pois
    # Requires admin_bounds.XX_counties, admin_bounds.XX_tracts, admin_bounds.XX_blocks
   
    # Note from DK: All code below will overwrite existing files. 
    # If you don't want to overwrite you may need to alter the SQL, or backup the database,  
    # or just work from a different schema. 
    
    # Schema shortcuts
    osm = dv.osm
    admin = dv.admin
    
    op_path_ccep1 = f"{op_path}\CCEP1_Master_County_Suitable_Sites"
    
    desc = "01 - Clip state-wide roads to county"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_roads;
        create table {ssl}.{county_name}_roads as
        select a.* from {osm}.{state}_roads  a, 
            (
                select * from {admin}.{state}_counties 
                where countyfp = '{county_code}'
            ) as b 
        where
        st_intersects(a.geom,b.geom);"""
    u.run_query(desc, db, qry_text)
    
    desc = "02 - Extract county-specific shape into file"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_county;
        create table {ssl}.{county_name}_county as 
        select * from {admin}.{state}_counties
        where countyfp = '{county_code}';"""
    u.run_query(desc, db, qry_text)

    # Note from DK: This is used to create the geojson used on the website for indicator data
    desc = "03 - Extract county-specific tracts into file"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_tracts;
        create table {ssl}.{county_name}_tracts as 
        select * from {admin}.{state}_tracts 
        where countyfp = '{county_code}';"""
    u.run_query(desc, db, qry_text)
    
        # Note from DK:
    # POIs are used to help identify suitable sites
    # This table of all the POIS - use it for error checking and such in QGIS - not used in actual modeling 
    desc = "04 - Extract OSM POIs for the county"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_pois;
        create table {ssl}.{county_name}_pois as 
        select a.* from {osm}.{state}_pois a, {ssl}.{county_name}_county b
        where st_intersects(a.geom, b.geom)
    """
    u.run_query(desc, db, qry_text)
    
    desc = "05 - Create government POIs"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_pois_gov;
        create table {ssl}.{county_name}_pois_gov as
        select * from {ssl}.{county_name}_pois 
		where fclass in (
			'post_office',
			'fire_station',
			'library',
			'town_hall',
			'police',
			'public_building',
			'courthouse',
			'embassy') 
        and (name not like '%(historical%)' or name is null)    
    """
    u.run_query(desc, db, qry_text)
    
    desc = "06 - Create miscellaneous POIs"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_pois_misc;
        create table {ssl}.{county_name}_pois_misc as
        select * from {ssl}.{county_name}_pois 
		where fclass in (
            'school',
            'hospital',
            'kindergarten',
            'community_centre',
            'arts_centre',
            'college',
            'university',
            'mall',
            'nursing_home',
            'supermarket',
             'hostel',
             'motel',
             'cafe') 
        and (name not like '%(historical%)' or name is null)    
    """
    u.run_query(desc, db, qry_text)
    
    # Note from DK: We use this in the modeling work. These blocks will be clustered 
    # and used as origins for the Facility Location Model
    desc = "07 - Extract county-specific blocks into file"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_blocks;
        create table {ssl}.{county_name}_blocks as 
        select * from {admin}.{state}_blocks
        where countyfp10 = '{county_code}';"""
    u.run_query(desc, db, qry_text)
    
    # Note from DK: Thes may not be necessary any longer - but keeping it just in case 
    # Removed housing10 for GIN processing (unsure if used, and how to obtain this data)
    desc = "08 - Create centroids from blocks"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_block_centroids;
        create table {ssl}.{county_name}_block_centroids as
        select gid, countyfp10, tractce10, blockce, blockid10, 
            pop10, st_centroid(geom) geom 
            from {ssl}.{county_name}_blocks"""
    u.run_query(desc, db, qry_text)

    # Note from DK:
    # https://gis.stackexchange.com/questions/16374/creating-regular-polygon-grid-in-postgis/16390#16390
    # 
    # This function is re-created for each county and state, in case SRID changes
    desc = "09 - Create grid-creation function"
    qry_text = f"""
    CREATE OR REPLACE FUNCTION public.makegrid_2d (
      bound_polygon public.geometry,
      grid_step integer,
      metric_srid integer = {state_srid} --metric SRID 
    )
    RETURNS public.geometry AS
    $body$
    DECLARE
      BoundM public.geometry; --Bound polygon transformed to the metric projection (with metric_srid SRID)
      Xmin DOUBLE PRECISION;
      Xmax DOUBLE PRECISION;
      Ymax DOUBLE PRECISION;
      X DOUBLE PRECISION;
      Y DOUBLE PRECISION;
      sectors public.geometry[];
      i INTEGER;
    BEGIN
      BoundM := ST_Transform($1, $3); --From WGS84 (SRID 4326) to the metric projection, to operate with step in meters
      Xmin := ST_XMin(BoundM);
      Xmax := ST_XMax(BoundM);
      Ymax := ST_YMax(BoundM);

      Y := ST_YMin(BoundM); --current sector's corner coordinate
      i := -1;
      <<yloop>>
      LOOP
        IF (Y > Ymax) THEN  --Better if generating polygons exceeds the bound for one step. You always can crop the result. But if not you may get not quite correct data for outbound polygons (e.g. if you calculate frequency per sector)
            EXIT;
        END IF;

        X := Xmin;
        <<xloop>>
        LOOP
          IF (X > Xmax) THEN
              EXIT;
          END IF;

          i := i + 1;
          sectors[i] := ST_GeomFromText('POLYGON(('||X||' '||Y||', '||(X+$2)||' '||Y||', '||(X+$2)||' '||(Y+$2)||', '||X||' '||(Y+$2)||', '||X||' '||Y||'))', $3);

          X := X + $2;
        END LOOP xloop;
        Y := Y + $2;
      END LOOP yloop;

      RETURN ST_Transform(ST_Collect(sectors), ST_SRID($1));
    END;
    $body$
    LANGUAGE 'plpgsql';    
    """
    u.run_query(desc, db, qry_text)

    # Note from DK: 
    # We create a grid over the county and use that as our potential "siting unit". 
    # We generally don't want to create a grid unless we are processing a new county. 
    # **Uncomment IF**
    # * If you want to change the size of the grid 
    # * or you are creating a new grid for a different county
    # If you are changing the size you should change the name of the file in the sql text below. 
    #
    # Envelope is the bounding box around the entire county      
    desc = "10 - Create 0.5 mile grid - get envelope"
    print(f"{u.getTimeNowStr()} Run query: {desc}")
    t0 = time.time()    
    qry_text = f"""
        select st_astext(st_envelope(geom)) 
        from {ssl}.{county_name}_county"""
    qry_results = db.qry(qry_text)
    get_county_envelope = qry_results.fetchall()[0][0]
    minutes = u.getTimeDiffInMinutes(t0)
    print(f"...finished in {minutes} mins")

    # 'srid' below used for envelope, since that was created from county file, in 'srid'
    # make2grid_2d uses 'state_srid' by default, as 3rd parameter (same results if 
    # state_srid were to be passed below)
    desc = "11 - Create 0.5 mile grid - generate grid file (entire bounding box of each county)"
    print(f"{u.getTimeNowStr()} Run query: {desc}")
    t0 = time.time()
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_grid_p05miles ;
        create table {ssl}.{county_name}_grid_p05miles as
        SELECT cell FROM 
            (SELECT (
            ST_Dump(makegrid_2d(
                        ST_GeomFromText('{get_county_envelope}', {srid}), -- WGS84 SRID for binding geom
                        {mts_in_pt05mile}) -- cell step in meters for half mile
        )).geom AS cell) AS q_grid    
    """
    db.qry(qry_text) # Not using run_query() to avoid issues with passing get_county_envelope
    minutes = u.getTimeDiffInMinutes(t0)    
    print(f"...finished in {minutes} mins")

    desc = "12 - Select grid cells that intersect county boundary"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_grid;
        create table {ssl}.{county_name}_grid as
        select a.cell geom, st_area(a.cell) md_area 
        from {ssl}.{county_name}_grid_p05miles  a, 
            {ssl}.{county_name}_county b where
        st_intersects(a.cell,b.geom);    
    """
    u.run_query(desc, db, qry_text)

    #Note: This might run for a while
    desc = "13 - Add unique ID to grid"
    qry_text = f"""
        alter table {ssl}.{county_name}_grid add column idnum int;
        update {ssl}.{county_name}_grid c
            set idnum = c2.seqnum
            from (select c2.*, row_number() over () as seqnum
                  from {ssl}.{county_name}_grid c2
                 ) c2
            where c2.geom = c.geom;    
    """
    u.run_query(desc, db, qry_text)

    # This creates a road layer split by grid boundaries
    desc = "14 - Create roads that intersect grids, add grid_id to each road segment"
    print(f"{u.getTimeNowStr()} Run query: {desc}")
    t0 = time.time()
    # ... name of road/grid intersection file
    grid_intx = f"{county_name}_grid_intx"
    # ... delete if it exists
    qry_text = f"""drop table if exists {ssl}.{grid_intx};"""
    db.qry(qry_text)
    # ...run intersection to get both id fields into new roads file
    db.intersect(
        f'{ssl}.{grid_intx}', # op
        f'{ssl}.{county_name}_grid','idnum','grid_id',
        f'{ssl}.{county_name}_roads','gid','road_id'
    ) 
    minutes = u.getTimeDiffInMinutes(t0)
    print(f"...finished in {minutes} mins")

    # This adds some road attributes to clipped road file, which are used in step 23 below
    desc = "15 - Copy fclass and name cols from original clipped roads file to new roads file"
    t0 = time.time()    
    print(f"{u.getTimeNowStr()} Run query: {desc}...")
    for col in ['fclass','name']:
        try:
            db.add_column(ssl,grid_intx,col,'character varying')
            db.column_copy(ssl,grid_intx,col,'road_id_gid',ssl,f'{county_name}_roads',col,'gid')
        except:
            print("... column copy failed!!") # This needs to go after next print
            continue
    minutes = u.getTimeDiffInMinutes(t0)
    print(f"...finished in {minutes} mins")

    # This creates a subset of grid cells, that overlay the listed POIs
    # Manually verified that the list of POIs here matches that above
    desc = "16 - Attach all POI types to temporary grid"     
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_temp_grid_voting_pois;
        create table {ssl}.{county_name}_temp_grid_voting_pois as 
        select a.*, 
                st_area(a.geom) ,
                b.fclass poi_class 
            from 
                {ssl}.{county_name}_grid a, 
                    (select * from {ssl}.{county_name}_pois 
                        where fclass in (
                            'school',
                            'post_office',
                            'fire_station',
                            'library',
                            'hospital',
                            'town_hall',
                            'police',
                            'public_building',
                            'kindergarten',
                            'community_centre',
                            'arts_centre',
                            'college',
                            'courthouse',
                            'university',
                            'mall',
                            'embassy',
                            'nursing_home',
                            'supermarket',
                            'hostel',
                            'motel',
                            'cafe') 
                        and (name not like '%(historical%)' or name is null)
                    )  as b
        where st_dwithin(a.geom,b.geom, .002)    
    """
    u.run_query(desc, db, qry_text)

    # This creates a county-wide grid (same as county_grid), with a column 
    # added for POI classes from the cells in _temp_grid_voting_pois
    desc = "17 - Attach the voting POIs to the working grid"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_grid_wdata;
        create table {ssl}.{county_name}_grid_wdata as
        select a.* , b.poi_classes 
        from 
            {ssl}.{county_name}_grid a 
            left join 
                (select idnum, array_agg(poi_class) poi_classes
                from {ssl}.{county_name}_temp_grid_voting_pois 
                group by idnum
                ) as b
            on a.idnum = b.idnum
            order by idnum    
    """
    u.run_query(desc, db, qry_text)
    

    print("Steps 18-21 are to calculate proportional block population for each grid cell")
    # Note from DK: This isn't used too extensively - but we retain it anyways
        
    # This area is in Cartesian, in sq degrees
    # Ok because it is used with intx area to get ratio for proportional population,
    # and both areas are in the same unit
    desc = "18 - Add area column to blocks, and calculate"
    db.add_column(ssl,f'{county_name}_blocks','md_area','numeric')
    qry_text = f"""
        update {ssl}.{county_name}_blocks 
        set md_area = st_area(geom);
    """
    u.run_query(desc, db, qry_text)
    
    desc = "19 - Create grids that intersect blocks, add block id to each grid"
    # Note: This is the reverse of road and grid intersection in step 14
    # In each blocks2grid polygon, 
    #   gid_gid = gid (id) from blocks file
    #   grid_id_gid = id from grid file
    print(f"{u.getTimeNowStr()} Run query: {desc}")
    t0 = time.time()
    # ... delete if it exists    
    qry_text = f"""drop table if exists {ssl}.{county_name}_blocks2grid;"""
    db.qry(qry_text)
    db.intersect(
        f'{ssl}.{county_name}_blocks2grid', # op
        f'{ssl}.{county_name}_blocks','gid','gid',
        f'{ssl}.{county_name}_grid','idnum','grid_id'
    ) 
    minutes = u.getTimeDiffInMinutes(t0)
    print(f"...finished in {minutes} mins")

    desc = "20 - Link the grid info to the intersection"
    print(f"{u.getTimeNowStr()} Run query: {desc}")
    t0 = time.time()
    qry_text = f"""
        select a.gid_gid, a.grid_id_gid, st_area(a.geom) intx_area, b.md_area
        from {ssl}.{county_name}_blocks2grid a,
            {ssl}.{county_name}_grid b
        where 
            a.grid_id_gid = b.idnum    
    """
    qry_results = db.qry(qry_text)
    minutes = u.getTimeDiffInMinutes(t0)
    print(f"...finished in {minutes} mins")
    
    desc = "21 - Calculate the proportional population"
    print(f"{u.getTimeNowStr()} Run query: {desc}")
    t0 = time.time()
    qry_text = f"""drop table if exists {ssl}.{county_name}_table_grid_block_pop;"""
    db.qry(qry_text)

    intersection_df= pd.DataFrame(qry_results.fetchall(), 
                                  columns = ['gid_gid','grid_id_gid','intx_area','md_area'])
    blocks = db.table2df(ssl,f'{county_name}_blocks')
    # This filter shouldn't drop any values, because we're already working with county_specific blocks
    blocks=blocks[blocks.countyfp10 == county_code]    
    
    # This value is a ratio of areas (of intx to grid), not an area itself. Doesn't appear to get used.
    intersection_df['prop_area'] = intersection_df.intx_area / intersection_df.md_area
    
    blocks = blocks.rename(columns={'md_area':'block_md_area'})
    # Join block values into this intersection df
    intersection_df = intersection_df.merge(blocks[['gid','blockce','pop10','block_md_area']],
                                            left_on='gid_gid', right_on='gid')
    
    # block_prop_area is a ratio of areas (of intx to block), and is used to 
    # proportionately distribute the population of the block across the various grid intersections
    intersection_df['block_md_area'] = intersection_df.block_md_area.astype('float')
    intersection_df['block_prop_area']  = intersection_df.intx_area / intersection_df.block_md_area
    # This is the population for each intersection polygon
    intersection_df['block_prop_pop'] = intersection_df.block_prop_area * intersection_df.pop10

    # temp file for debugging population calculations
    qry_text = f"""drop table if exists {ssl}.{county_name}_temp_intersection_df;"""
    db.qry(qry_text)
    db.df2table(intersection_df, ssl,f'{county_name}_temp_intersection_df')
    
    grid_totals = intersection_df.groupby('grid_id_gid').agg({ 
                                      'pop10':[sum],
                                      'block_prop_pop':[sum],
                                      'blockce':lambda x: tuple(x),
                                     }).reset_index()
    grid_totals = grid_totals.reset_index()
    grid_totals.columns = grid_totals.columns.droplevel(1)
    grid_totals = grid_totals[['grid_id_gid','block_prop_pop','blockce','pop10']]
    grid_totals['block_prop_pop'] = np.round(grid_totals.block_prop_pop)
    db.df2table(grid_totals, ssl,f'{county_name}_table_grid_block_pop')

    minutes = u.getTimeDiffInMinutes(t0)
    print(f"...finished in {minutes} mins")

    #Originally, grid_wdata had poi_classes. Here, pop10 and block_prop_pop are added
    desc = "22 - Update working grid table with data"
    print(f"{u.getTimeNowStr()} Run query: {desc}")
    t0 = time.time()    
    working_table_name = f'{county_name}_table_grid_block_pop'
    destination_table_name = f'{county_name}_grid_wdata'
    db.add_column(ssl,destination_table_name,'pop10','bigint')
    db.add_column(ssl,destination_table_name,'block_prop_pop','bigint')
    db.column_copy(ssl,destination_table_name,'pop10','idnum',ssl,working_table_name,'pop10','grid_id_gid')
    db.column_copy(ssl,destination_table_name,'block_prop_pop','idnum',ssl,working_table_name,'block_prop_pop','grid_id_gid')
    minutes = u.getTimeDiffInMinutes(t0)
    print(f"...finished in {minutes} mins")  

    # grid_wdata is saved as suitable_sites_raw when road length is added,
    # and after dropping grids with certain road classes
    # Note: Length is in degrees/cartesian, and used in the same unit in CCEP3
    desc = "23 - Create raw suitable site layer"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_suitable_sites_raw;
        create table {ssl}.{county_name}_suitable_sites_raw as
        select a.*, b.road_length from {ssl}.{county_name}_grid_wdata  a,  
        	(
        	select grid_id_gid idnum, sum(st_length(geom)) road_length
        	from {ssl}.{county_name}_grid_intx 
        	where fclass not in ('unclassified','bridleway','unknown','path') and fclass not like 'trac%'
        	group by grid_id_gid 
        	) as b
        	where a.idnum = b.idnum;    
    """
    u.run_query(desc, db, qry_text)

    desc = "24 - Count the POIs in each cell"
    qry_text = f"""
        alter table {ssl}.{county_name}_suitable_sites_raw   
        add column num_poi integer;
        update {ssl}.{county_name}_suitable_sites_raw  
            set num_poi = cardinality(poi_classes);    
    """
    u.run_query(desc, db, qry_text)

    desc = "25 - Create centroids from suitable site layers"
    qry_text = f"""
        drop table if exists {ssl}.{county_name}_suitable_sites_raw_centroid;
        create table {ssl}.{county_name}_suitable_sites_raw_centroid as
        select *, st_x(st_centroid(geom)) lon, st_y(st_centroid(geom)) lat 
        from {ssl}.{county_name}_suitable_sites_raw;    
    """
    u.run_query(desc, db, qry_text)
    
    desc = "26 - Write centroids to output csv"
    print(f"{u.getTimeNowStr()} Run query: {desc}")
    t0 = time.time()    
    df_label = f'{county_name}_suitable_sites_raw_centroid'
    temp_df = db.table2df(ssl,df_label)
    temp_df = temp_df.drop('geom',axis=1)
    op_file = f'{op_path_ccep1}\{state}_{county_code}_suitable_site_raw_centroids.csv'
    temp_df.to_csv(op_file,index=False)
    minutes = u.getTimeDiffInMinutes(t0)
    print(f"...finished in {minutes} mins")
    print(f"File written to {op_file}")
