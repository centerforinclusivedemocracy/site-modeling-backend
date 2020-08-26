
<!-- TOC -->

- [CCEP1 - Create potential suitable sites](#ccep1---create-potential-suitable-sites)
- [CCEP2 - Build Clusters](#ccep2---build-clusters)
- [R - Process transit, weight indicator data, combine with suitable sites](#r---process-transit-weight-indicator-data-combine-with-suitable-sites)
- [CCEP3 - Score suitable sites](#ccep3---score-suitable-sites)
- [CCEP4 - Generate travel time matrix](#ccep4---generate-travel-time-matrix)
- [CCEP5 - Run FLP model](#ccep5---run-flp-model)
- [CCEP6 - Web data prep](#ccep6---web-data-prep)
- [What is a site](#what-is-a-site)
- [Why a site is retained or dropped](#why-a-site-is-retained-or-dropped)
- [Projection used for each state](#projection-used-for-each-state)

<!-- /TOC -->

# Overview of logic in each CCEP Python Module

This is a summarized view of the script logic. More detailed updates are in the larger methodology doc: https://docs.google.com/document/d/1VL-ZHPVIb5raqBxT2-EtGW2ao4osvQiOi0o_gT8ougg/edit#

## CCEP1 - Create potential suitable sites
**Data consumed**
- Census data in Postgres DB
- OSM roads and POI data in Postgres DB

**Steps include**
- Census and OSM data prep
   - Subset census data for the county in question, create files for county, tract, blocks, and block centroids
   - Subset OSM roads for this county
   - Subset OSM POIs for this county, split out into Gov and Misc POIs
- Grid creation
   - Create a bounding box extent for county
   - Create a 1/2 mile (800m) grid within this extent
   - Select the cells that intersect county
   - Add IDs to the grid 
- Prep data to join to grid
   - Roads: Intersect roads by grid boundary, add grid id to each segment, copy over some OSM road attributes to new road layer
   - POIs: Add a column of POI classes to a copy of the grid layer
   - Population: Calculation population for each grid cell (Intersect blocks by grids, calc poportional population of each intersection polygon based on ratio of its area to block area, aggregate population by grid cell id)
- Create suitable site layer
   - Attach above data to 'working' grid, also calculating road length (in degrees) and number of POIs
   - Remove any sites that do not have roads, or do not have traversable road types ('unclassified','bridleway','unknown','path', 'trac%')
      - Retained road types include: cycleway, footway, living_street, motorway*, pedestrian, primary*, residential, secondary*, service, steps, tertiary*, trunk*
   - Create centroids of suitable sites, export to CSV for CCEP3

## CCEP2 - Build Clusters
**Data consumed**
- Registered voter data
- Census blocks for county, from Postgres DB

**Steps include**
- Join census blocks and registered voter data on block id
- Determine number of clusters: (Sum of all registered voters / 10,000) * 2. Min clusters = 30
   - For Los Angeles CA, we use 15,000 threshold
- Create clusters using KMeans clustering (more info [here](https://towardsdatascience.com/understanding-k-means-clustering-in-machine-learning-6a6e67336aa1) and [here](https://blogs.oracle.com/datascience/introduction-to-k-means-clustering))
- Export to .pkl format (and .csv for debugging)
   - The output file contains rows of blocks that had reg. voter data, including X-Y of their centroid, and a field with cluster IDs, to identify which cluster ID each block belongs to

## R - Process transit, weight indicator data, combine with suitable sites
**Data consumed**
- Suitable sites points from CCEP1 (grid centroids)
- GTFS transit data, with frequency scores, from GTFS script
- Indicator data
- Census geographies

**Steps include**
- Remove any sites that fall outside the county boundary
- Combine columns from county data into sites data
- Add the appropriate block, block group and tract id to each site point
- Derive the transit scores for each site
   - Find the 3 nearest transit stops to each site
   - Eliminate any stops that are > 0.7 miles away
   - Invert the distance, so that stops that are further away have lower scores, stops that are closer have higher scores
   - Multiply by the stop frequency score that is calculated by the GTFS script, so that higher stop frequencies result in higher transit scores
   - Update the score to reflect how many (0 to 3) transit stops fell within the 0.7 mile radius - more stops result in a higher score
   - Normalize the resulting transit scores to be between 0 and 1
- Combine indicator data with the sites
- Created the weighted averages of the indicator data per site

## CCEP3 - Score suitable sites
**Data consumed**
- Suitable sites produced by R scripts
- Optional: Local Knowledge Sites (LKS)
- Optional: Fixed Sites (Colorado only)

**Steps include**
- Incorporate LKS data if it exists
   - Add a column for LKS to sites, populate with 1 for the 2 grid cells that are closest to each LKS site
- Incorporate Fixed Sites data if it exists (Colorado only)
   - Add a column for 1-day and 15-day Fixed Sites to sites, populate with 1 single grid cell that is closest to each Fixed Site.
   - We do it separately for 1-day and 15-day Fixed Sites, since the 15-day layer uses a subset of the 1-day layer fixed sites.
- For 4 select POI types (fire station, post office, town hall, public building), add a column for each, and flag as 1 if the site had this POI
- Create constraint queries 
   - Q1: [Road length >= 0.07 degrees] & [pop > 0]
   - Q2: [Road length >= 0.01 degrees] & [pop > 0] & [number of POIs > 2] 
   - Q3: LKS flag > 0
   - Q4: Select POI flags () > 0 & [pop > 0]
   - Q5: Fixed Sites flags > 0 (Colorado only)
- Apply constraint queries 
   - For LA, we set population threshold to 50  instead of 0, and skip Q4. This is to reduce the number of produced scored sites, to be within a limit that the model can feasibly process
- Export to csv, and write to Postgres DB

## CCEP4 - Generate travel time matrix
**Data consumed**
- Scored sites from CCEP3
- Clusters (of blocks by voter totals) from CCEP2
- OSM road network from API

**NOTE**  
- This script is set to first check the output directories if files already exist, and if yes, *not* re-generate them (because files like the OSM network and distance matrix can be very large).  
- However, if any of the inputs to the script have changed, i.e. if sites or clusters have been regenerated in the prior steps, please delete the prior CCEP4 files from the output directories to ensure that the script *does* regenerate them, otherwise the IDs of the old and new data will not match, causing the script to fail.

**Steps include**
- Read in county boundary
- Read in OSM network, either based on county boundary, or county bounding box. 
   - If first time run, netowrk will be stored on disk, and used in future runs
- Calculate edge speeds and weights
   - Speeds (convert numbers below to km, x 1.60934)
   ```
      'motorway_link': 55,
      'motorway': 55,
      'primary': 30,
      'secondary': 30,
      'tertiary': 30
       all other: 25 * 0.5
   ```
   - Weights = [ (edge length / 1000) / edge speed ] * 60
- Create pandana network from OSM nodes and edges
- Load block-voter clusters, create centroids of clusters
- Assign closest road nodes (near-nodes) to cluster centroids, using pandana network
   - If more than 1 cluster centroid has the same nearnode id, keep the nearest centroid and delete the rest
- Assign closest road nodes (near-nodes) to scored sites, using pandana network
   - Remove any duplicate near-nodes that exist - same as with cluster centroids
- Using the near-node road ids, calculate distance between near-nodes for cluster centroids and those for scored sites (routing). This produces the cost between pairs of near-node ids, each of which represents a pair of cluster centroid - scored site points
   - If no path can be found, the original code would set a distance of 0, making the 2 points 'closest' when in reality they were inaccessible by the network. Fixed to set cost to 9999 in this situation.
- Re-arrange the data so that costs are between pairs of cluster centroid and scored site points. (In above step, the near-nodes were needed just to calculate the cost from the road network)
- Export intermediate files (as generated)
   - OSM network (delete to refresh for new runs)
   - Cost matrix between near-node ids (delete for new runs, or if cluster ids or scored site ids have changed, i.e. CCEP2/3 have been re-run)
   - Cluster centroids (used in CCEP5)   
- Export final file
   - Cost matrix between cluster centroids and scored sites

## CCEP5 - Run FLP model
**Data consumed**
- Scored sites from CCEP3
- Clusters (of blocks by voter totals) from CCEP2
- Cluster centroids from CCEP4
- Cluster centroid to score site travel time matrix from CCEP4

**Steps include**
1. Split the 2 scores that come from weighted avgs calculations (center_score, droppoff_score) into quantiles. 
   - For each category range, determine how many values exist, and order by categories. Order is important because cost adjustment assumes bottom quantiles are listed first
   - Do the cost adjustment - Top quantiles are 50% the cost, while bottom quantiles are 200% the cost. 
   - Create a lookup of cost adjustments, i.e. cost adjustment for each site's idnum
2. Determine number of vote sites for each category (short-term, long-term, and drop box)
   - This data was obtained for us by CCEP, and should not be changed (required by law)
   - Note that each state uses a different terminology for their vote center names. The code we inherited used a mix of 3/10-day and 4/11-day for CA, and the final output has:
      - California has 4-day, 11-day, and dropbox centers.
      - Colorado has 1-day, 15-day, and dropbox centers
      - Arizona has 7-day, 14-day, and dropbox centers.
      - Texas has election day, and early voting centers. 
3. Set up capacity for each typoe of vote site
   - Default capacities are as follows, but in some cases they have to be overridden to meet the demand (number of reg voters / number of vote centers), or to allow the model sufficient flexibility to complete
      - For short-term sites: 20,000 (except Napa 25,000, Nevada 13,000 - chosen by DataKind/CCEP, Maricopa 70,00)
      - For long-term sites: 75,000 (Colorado 129,000, Maricopa 200,000)
      - Dropbox sites: 40,000 (Maricopa 500,000, Los Angeles 80,000)
4. Set up inputs to the FLP model ([Model explanation](https://scipbook.readthedocs.io/en/latest/flp.html)). Our inputs are:
   - Customer `i` = List of clusters (of blocks that have registered voters), from CCEP2
   - Customer demand `d` = registered voter totals for each cluster
   - Facilities `j` = list of voting sites, i.e. scored sites from CCEP3
   - Cost of operating each facility `f`, from item 1 above
      - For 3 and 10 day sites, 12,000 * center_score cost adjustment lookup
      - For dropbox sites, 7,500 * droppoff_score cost adjustment lookup
   - Capacity, i.e. amount of demand the facility can handle `M` = capacity from item 3 above
   - Travel cost between customer and site `c` = travel cost matrix from CCEP4 (between scored sites and cluster centroids)
   - Required number of sites `k` = number of vote centers from step 2 above
5. Use the FLP model to determine short-term, long-term, and drop box sites
   - Since long-term sites should also be short-term sites, find any that are not, and replace them with the nearest short-term site. 
   - For Colorado, provide fixed sites list (i.e. scored sites tagged as fixed sites) as an override constraint to the model
   - If the model hit a constraint conflict and failed, it would originally return *ALL* sites. This was erroneous because it exceeded the legal amount of sites required. We fixed this by having the model exit with a failure, so that the cause of the constraint failure can be investigated and fixed, to allow the model to run to completion. 
6. Find 10% more 3 day sites (if the county has the desire to open more)
7. For any sites with a travel time of > 15 minutes to the nearest vote sites, look for addition vote sites that might be faster to access by 25% or more
   - It's possible that none are returned, either because all clusters were within 15 minutes of their nearest site, or because for the ones that were further away, no alternate site was found that was at least 25% closer
8. Export the 5 types of sites from items 5, 6, and 7 above. 

## CCEP6 - Web data prep
**Data consumed**
- Scored sites from CCEP3
- Model output from CCEP5
- Tract-level indicator data 
- GTFS transit data 
- LKS (local knowledge site) data
- Colorado fixed sites
- Clipped tracts (where required)

**Steps include**
1. Census tract boundaries are prepared and incorporated into the data. Any tracts that are water-only are eliminated.
1. Square polygons at the centroid of each tract are produce to be used with unreliability flags. Centroids for water-only tracts are eliminated.
1. In cases where a tract extended significantly into the water, we prepared manually clipped tract files. If these exist, the code will replace the system-generated tract file with this one. Note that the tract centroids are calculated from the source tracts, and do not currently get adjusted after the tracts are clipped. This is because the tract centroid squares are likely to go away in a future design revision.
1. All the indicator variables are combined into a single CSV file, and merged with census tracts for web display. A corresponding shapefile is prepared for user download. `indicator_menu_fields.csv` is created to provide layer order and details to the website.
   - The website uses tracts.json, and combines with the csv indicator data, for display. It does not render from the shp.
1. For all the FLP model outputs, CSV files are gathered, and shapefiles are produced for user download. `site_area_count.csv` is created to provide the number of sites in each layer to the website.
   - Similar to above, here the website draws its own 800m circles (or squares), it does not render from the shp.
1. CSV files are generated for all POI types (government, miscellaneous, and combined)
1. Individual CSV files are produced for all transit stops, Local Knowledge Sites (for example - prior vote center locations or polling places), and Fixed Sites (for Colorado)
1. All files are optimized to reduce size, by removing extraneous columns generated in processing, and rounding all fractional fields (especially lat-long points), to 5 decimal places
1. If a county does not have data points in any layer, be it a points layer or model output, the code here will produce an empty csv file, with just the header. The website requires this so it doesn't break. The code however cannot produce an empty shapefile, so in these scenarios, the shp.zip file will be missing in cases where a layer was empty. If a user tries to download it, they will get a 404 error on the site. Removing this file's link from the county's download popup has to be coded on the front end website code.


# Miscellaneous information

## What is a site
_(From email thread on 5/19/2020)_

A site represents a region, specifically a square with 1/2 mile (800 m) sides. Any location within the square is considered suitable. (For the UI, though circles were selected, it is actually the bounding box around the circles that the site truly represents.)

## Why a site is retained or dropped
_(From email thread on 5/19/2020)_

Selected sites: 
- When the grid of 1/2 mile squares is first created across a county, any square that includes official OSM roads is retained as a selected site. Any square that has no roads, or has only unofficial roads (like paths or bridleways), is dropped.

Scored sites: 
- Sites that meet the criteria of the 5 queries listed in CCEP3 above are retained. Sites that don't meet any of the stated CCEP3 criteria, are dropped
- To note:
   - Proportional population for a grid square (site) is calculated based on the area of each block it intersects, and the population of that block
   - Population check is > 50 for LA county (> 0 for all others)
   - For LKS selection - the 2 sites nearest to each LKS point are tagged, and each of these is retained 
   - For Fixed Sites selection - the 1 site nearest to each Fixed Site point is tagged, and each of these is retained 

FLP Model selection:
- From the available 'scored sites', the model selects the required number of sites based on its internal logic, optimizing for demand (clusters of blocks based on registered voter population), and travel costs between clusters and sites.
- For Colorado, we present the scored sites that were flagged as 'Fixed' to the model, to ensure these are among those suggested in the output
- The required number of sites of each type, per county, was set based on the spreadsheets Mindy provided for CA and CO counties. 

## Projection used for each state
The projections below were selected after reviewing many different projections for each state, and selecting for maximum horizontal and veritical alignment of the grid. Unfortunately projections are optimized for large areas, so it's possible that the grid may be slightly angled in some locations, while appearing straight in others. 
- CA EPSG 3310 NAD 83 / California Albers in meters
- CO EPSG 26954 NAD83 / Colorado Central 
- AZ EPSG 26949 NAD83 / Arizona Central
- TX EPSG 3083 NAD83 / Texas Centric Albers Equal Area


