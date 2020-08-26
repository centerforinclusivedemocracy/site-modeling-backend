# -*- coding: utf-8 -*-
"""
Created on Mon Jan 13 15:06:06 2020

@author: Gorgonio

# Note from DK

This script is used to build a travel time matrix.

** NOTE **
It can only be run on counties for which we have registered voter data,
and clusters have been created in CCEP2.

The script loads 
- the scored suggested sites from CCEP3, 
- the cluster centroids from CCEP2, and
- the OSM road network
It then creates a python dictionary that stores the travel costs from 
every cluster centroid to every scored site. This is the distance "matrix",
which is saved to a file.

Assumptions
- Assumptions were made about average travel speed on road segments of different types
- Assumes the OSM network is a reasonably accurate road network representation
- Assumes driving network is a suitable network representation for voter access

"""

# ===================================
# IMPORTS
# ===================================
import os
import osmnx as ox
import pandas as pd
import geopandas as gpd
import pandana as pdna
import shutil
from sklearn.externals import joblib
from shapely.geometry import MultiPoint
import ccep_utils as u
import ccep_datavars as dv

# ===================================
# GLOBAL VARIABLES
# ===================================

# Assumptions made my DK about travel speeds on road network
# Ref: http://wiki.openstreetmap.org/wiki/Key:highway
speeds = {'motorway_link': 55,
  'motorway': 55,
  'primary': 30,
  'secondary': 30,
  'tertiary': 30
 }

# Global var for distance calculations
# Note from DK: Distance Record stores the result from build_distances(). 
# It is outside of the function in case the execution is interrupted.
# Function can be restarted and will only calculate those ODs that have not been done yet. 
distance_record = {}

# ===================================
# FUNCTIONS
# ===================================
def assign_speed(x):
    if isinstance(x,list):
        x = x[0]
    # Convert miles to kms
    if x in speeds:
        return speeds[x] * 1.60934
    else:
        return (25 * 1.60934) *.5

# Function for routing    
def get_cost(path, edges):
    indv_paths = []
    for i,v in enumerate(path):
        if i+1 < len(path):
            indv_paths.append( (path[i],path[i+1]) )
    clean_idx = []
    for p in indv_paths:
        p ='_'.join([str(i) for i in p])
        clean_idx.append(p)
    travel_time = edges.loc[clean_idx].weight.sum()
    return travel_time
    
# Function for routing
def build_distances(net, edges, origin, origin_nearnode, destination, destination_nearnode):
    counter = 0
    global distance_record

    print("Building distances...")
    for i in origin[origin_nearnode]: # number of clusters 
        for j in destination[destination_nearnode]: # number of scored sites
            ## If we already have it don't redo it
            if (i,j) in distance_record:
                pass
            else:
                path_val =  {'path':net.shortest_path(i, j, 'weight'),'cost':None}
                cost_val = get_cost(path_val['path'], edges)
                if len(path_val['path']) == 0:
                    if cost_val == 0.0:
                        cost_val = 99999.0
                    else:
                        # Path is empty but cost is non 0
                        print("**** Found a pair of nodes with no path, but non-0 cost. Please examine. ")
                        print(path_val, cost_val)
                distance_record[(i,j)] = path_val
                distance_record[(i,j)]['cost'] = cost_val
            
            counter += 1
            if counter % 10000 == 0:
                print(f"Number of rows processed: {counter}, at {u.getTimeNowStr()}")


# ===================================
# MAIN EXECUTION MODULE
# ===================================
def run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, ip_path, bbox, plot=False): 
    
    # Create proper case county names
    county_label = county_name.replace("_", " ").title() + " County"
    state_label = state.title()
    
    op_file_osmnwk = fr"{op_path}\CCEP4_OSM_Network\{state}_{county_code}_osm_nwk.pkl"
    op_file_dist_matrix = fr"{op_path}\CCEP4_Distance_Matrix\{state}_{county_code}_clusters2sites_matrix.pkl" 
    op_file_final_nwk = fr"{op_path}\CCEP4_Final_Network\{state}_{county_code}_clusters2sites_matrix_not_osm_ids.pkl" 
    op_file_cluster_centroids = fr"{op_path}\CCEP4_Cluster_Centroids\{state}_{county_code}_cluster_centroids_df.pkl" 
    
    ip_cluster_file = fr"{op_path}\CCEP2_Master_County_FLP_Files\{state}_{county_code}_clusters.pkl"
    ip_scored_sites = fr"{op_path}\CCEP3_Master_County_FLP_Files\{state}_{county_code}_all_sites_scored.csv"
    bak_scored_sites = fr"{op_path}\CCEP3_Master_County_FLP_Files\{state}_{county_code}_all_sites_scored_bak_fromCCEP4.csv" 
    
    desc = "01 - Read in county"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    df_county = db.table2df(ssl,f"{county_name}_county")
    county_gdf = u.make_gpd(df_county,srid)

    # Load Network from OSM - using bbox set up in ccep_datavars.py
    #
    # Notes from DK: Using the county name instead of the bounding box will return 
    # a smaller network that will be easier to calculate distances from - but may 
    # have streets clipped that could offer connections within the county via a route 
    # outside the county. 
    # For some counties like Nevada, you must use bbox = True, otherwise portions of the 
    # network are not created because they lack connectivity. 
    # If it is a big county like Sacramento, and the connectivity within the county is 
    # good, it's likely ok to just use the county extract and set `bbox=False`.
    # Generally speaking, bbox=True is the safer option, it will just take longer to run
    #
    # If True, San Mateo 2-3 mins, Los Angeles 10-11 mins, Harris 5-6 mins
    # If False, San Mateo 1 min, Los Angeles 8 mins, Harris 4-5 mins
    #
    # If saved network already exists, load this. If not, generate from OSM, 
    # and save it for next run.
    if os.path.exists(op_file_osmnwk):
        desc = "02 - Load the OSM network from file on disk"
        print(f"{u.getTimeNowStr()} Run: {desc}")        
        G = joblib.load(op_file_osmnwk)
    else:
        # Load network
        if bbox:
            desc = "02 - Load the OSM network based on Bounding Box"
            print(f"{u.getTimeNowStr()} Run: {desc}")
            G = ox.graph_from_polygon(county_gdf.envelope[0], network_type='drive')
        else:
            desc = f"02 - Load the OSM network based on County Name = {county_label}"
            print(f"{u.getTimeNowStr()} Run: {desc}")
            G = ox.graph_from_place([f"{county_label}, {state_label}, USA"], network_type='drive')
        # Save network
        print("Save OSM network file to disk")
        joblib.dump(G,op_file_osmnwk)

    nodes, edges  = ox.graph_to_gdfs(G)

    if plot:
        ax = county_gdf.plot(alpha=1,figsize=(12,12), color='white',edgecolor='black', linewidth=2)
        edges.plot(linewidth=.5, color='black', alpha=.3,ax=ax)

    desc = "03 - Set up weights based on travel speeds"
    print(f"{u.getTimeNowStr()} Run: {desc}")        
        
    edges['speed'] = edges.highway.apply(assign_speed)
    edges['weight'] = ((edges['length']/1000)/(edges['speed']))*60    
    edges['from_to'] = edges.apply(lambda row: str(row.u) +'_' +str(row.v), axis=1)    
    edges.index = edges.from_to
    
    desc = "04 - Build the pandana network"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    # Note from DK: If you get a bunch of Pink warnings when this is run - thats ok      
    net = pdna.Network(nodes['x'], nodes['y'],
        edges['u'], edges['v'], edges[['weight']], twoway=False)


    desc = "05 - Load block-voter clusters from CCEP2"
    print(f"{u.getTimeNowStr()} Run: {desc}")    
    df = joblib.load(ip_cluster_file)
    num_clusters = df.cluster_labels.nunique()
    print(f"Total number of block-voter clusters: {num_clusters}")
    
    # Verified in a few counties - road extent covers entire county, and not just a city or two
    if plot:
        ax = county_gdf.plot(alpha=1,figsize=(15,15), color='white',edgecolor='red', linewidth=4)
        df.plot(column='cluster_labels', alpha=.7,legend=True, ax=ax)
        edges.plot(linewidth=.5, color='black', alpha=.3,ax=ax)

    desc = "06 - Create cluster centroids for distance calculation"
    print(f"{u.getTimeNowStr()} Run: {desc}")            
    # Note from DK: Take all the block centroids in each cluster and create a cluster centroid 
    cluster_centroids = {}
    cluster_centroids_df = []
    for i in df['cluster_labels'].unique():
        cluster_points = df[df['cluster_labels'] == i].geometry.tolist()
        centroid = MultiPoint(cluster_points).centroid
        cluster_centroids[i] = {'geom': centroid, 'x': centroid.x, 'y':centroid.y}
        cluster_centroids_df.append([i, centroid])
    cluster_centroids_df = gpd.GeoDataFrame(cluster_centroids_df,columns=['cluster_id','geometry'])

    desc = "07 A - Assign the closest road nodes to the cluster centroid X/Ys (create near-nodes for clusters)"
    print(f"{u.getTimeNowStr()} Run: {desc}")       
    ## Get the x and y values
    xs = [i.x for i in cluster_centroids_df.geometry]
    ys = [i.y for i in cluster_centroids_df.geometry]    
    ## Assign the near node
    cluster_centroids_df['near_node'] = net.get_node_ids(xs, ys).tolist()

    desc = "07 B - Check for duplicate near-nodes in clusters"
    print(f"{u.getTimeNowStr()} Run: {desc}")       

    # Sometimes 2 cluster centroids may end up with the same 'near-nodes', i.e. they are
    # both nearest to the same node on the network. If we find such duplicates, the code only
    # keeps the cell nearest to that node.
    check_for_dupes = cluster_centroids_df.near_node.value_counts()
    check_for_dupes = check_for_dupes[check_for_dupes > 1]
    check_for_dupes = check_for_dupes.index.tolist()
    num_dupes = len(check_for_dupes)
    print(f"Number of duplicate near nodes in clusters: {num_dupes}")
    if num_dupes > 0:
        print(f"OSM node ids that are duplicated in clusters: {check_for_dupes}")        
        
    desc = "7C - Fix duplicate 'near-nodes' in clusters, if they exist."
    print(f"{u.getTimeNowStr()} Run: {desc}")              
    # Removal of duplicate near-nodes is necessary because in step 14, we use near-node ID
    # to retrieve cluster ID
    if len(check_for_dupes) > 0:        
        print(f"Size of original cluster centroids data, rows/columns:{cluster_centroids_df.shape}")
        for dupe_nearnode in check_for_dupes:
            distances = {}
            deleted_ids = []
            for row in cluster_centroids_df[cluster_centroids_df.near_node == dupe_nearnode].iterrows():
                # For debugging...                
                node_pt_geom = nodes[nodes.osmid == dupe_nearnode]['geometry']
                site_pt_geom = row[1].geometry
                # Find distance between node and each cluster centroid that has this node as nearest-node
                distances[row[1]['cluster_id']] = node_pt_geom.distance(site_pt_geom).values[0]
                # From centroids evaluated so far, find closest site
                closest_site = min(distances, key=distances.get)
                # Delete non-closest centroid
                for k in distances:
                    if k != closest_site:
                        if k not in deleted_ids:
                            print(f"Dropping cluster centroid with cluster id {k}")
                            cluster_centroids_df = cluster_centroids_df[cluster_centroids_df.cluster_id != k]
                            deleted_ids.append(k)
                        
        print(f"Size of modified cluster centroids data, rows/columns:{cluster_centroids_df.shape}")
        
        # No need to back up and overwrite like with sites below, since this is only in memor
        
    desc = "08 - Load scored sites from CCEP3"
    print(f"{u.getTimeNowStr()} Run: {desc}")       
    ref_data = pd.read_csv(ip_scored_sites)
    ref_data = u.make_gpd(ref_data,srid,fromPostgis=False)
    print(f"Total number of potential scored sites: {ref_data.shape[0]}")

    if plot:
        ax = county_gdf.plot(alpha=1,figsize=(12,12), color='white',edgecolor='red', linewidth=4)
        ref_data.plot(ax=ax)
        edges.plot(linewidth=.5, color='black', alpha=.3,ax=ax)

    desc = "09 - Set up the geometry on scored sites"
    print(f"{u.getTimeNowStr()} Run: {desc}")       
    valid_sites = ref_data.copy(deep=True)
    
    # This was in DK code. But since our sites are always points, not polygons, 
    # we don't need this
    #if valid_sites.geom_type.iloc[0] == 'Polygon':
    #    valid_sites['geometry'] = valid_sites.geometry.centroid
        
    xs = [i.x for i in valid_sites.geometry]
    ys = [i.y for i in valid_sites.geometry]
    
    desc = "10 - Assign 'near-nodes' for scored sites"
    print(f"{u.getTimeNowStr()} Run: {desc}")           
    valid_sites['near_node'] = net.get_node_ids(xs, ys).tolist()

    desc = "11 - Check for duplicate 'near-nodes' in scored sites"
    print(f"{u.getTimeNowStr()} Run: {desc}")           
    # Notes from DK: Sometimes 2 cells may end up with the same 'near-nodes', i.e. they are
    # both nearest to the same node on the network. This should not happen since there are many many nodes,
    # so cells should not have the same 'near-node'. If we find such duplicates, the code only
    # keeps the cell nearest to that node.
    check_for_dupes = valid_sites.near_node.value_counts()
    check_for_dupes = check_for_dupes[check_for_dupes > 1]
    check_for_dupes = check_for_dupes.index.tolist()
    num_dupes = len(check_for_dupes)
    print(f"Number of duplicate near nodes in sites: {num_dupes}")
    if num_dupes > 0:
        print(f"OSM node ids that are duplicated in sites: {check_for_dupes}")

    # Found duplicates in LA, El Dorado, Orange, Harris cos
    # Haven't yet run for AZ, CO
    desc = "12 - Fix duplicate 'near-nodes' in scored sites, if they exist."
    print(f"{u.getTimeNowStr()} Run: {desc}")              
    # Removal of duplicate near-nodes is necessary because in step 14, we use near-node ID
    # to retrieve scored site ID
    if len(check_for_dupes) > 0:        
        print(f"Size of original sites data, rows/columns:{valid_sites.shape}")
        for dupe_nearnode in check_for_dupes:
            distances = {}
            deleted_ids = []
            for row in valid_sites[valid_sites.near_node == dupe_nearnode].iterrows():
                # For debugging...
                #print(f"Scored sites idnum with duplicate: {row[1]['idnum']}, near-node osm id {row[1]['near_node']}")
                node_pt_geom = nodes[nodes.osmid == dupe_nearnode]['geometry']
                site_pt_geom = row[1].geometry
                # Find distance between node and each site that has this node as nearest-node
                distances[row[1]['idnum']] = node_pt_geom.distance(site_pt_geom).values[0]
                # From sites evaluated so far, find closest site
                closest_site = min(distances, key=distances.get)
                # Delete non-closest site
                for k in distances:
                    if k != closest_site:
                        if k not in deleted_ids:
                            print(f"Dropping site with idnum {k}")
                            valid_sites = valid_sites[valid_sites.idnum != k]
                            deleted_ids.append(k)
                        
        print(f"Size of modified sites data, rows/columns:{valid_sites.shape}")
        print(f"Backing up original scored sites file to {bak_scored_sites}")
        shutil.copyfile(ip_scored_sites, bak_scored_sites)
        # Overwrite original file to incorporate removal of sites from above
        print(f"Overwriting original scored sites to incorporate deleted sites")
        valid_sites.to_csv(ip_scored_sites,index=False)

    # Note from DK: Output is dictionary of values, but the keys are the 
    # road network nodes that are closest to the both locations (clusters and sites)
    desc = "13 - Calculate Distances From Cluster Centroids to Sites (Routing). This produces cost between each pair of near-node IDs"
    print(f"{u.getTimeNowStr()} Run: {desc}")                   
    
    # build_distances() will update global dict distance_record
    # clear the dictionary between counties
    distance_record.clear()    
    len_clusterdf = len(cluster_centroids_df)
    len_scored_sites = len(valid_sites)    
    print(f"Num clusters = {len_clusterdf}, num scored sites = {len_scored_sites}")
    print(f"Expected length of distance matrix = {len_clusterdf * len_scored_sites}")

    # Only re-run this if file doesn't already exist, since it takes a while
    # for some counties, like Sacramento (20+ mins) and San Mateo (3+ mins)
    if os.path.exists(op_file_dist_matrix):
        print(f"Distance matrix exists, will not regenerate. File in {op_file_dist_matrix}")        
    else:
        build_distances(net, edges, cluster_centroids_df,'near_node', valid_sites, 'near_node')
        nearnode_network_distance_matrix = distance_record
        # Save to pickle object
        joblib.dump(nearnode_network_distance_matrix,op_file_dist_matrix)

    # Note from DK: The dictionary of distances has IDs that relate to the 
    # OSM network nodes, we want to translate it back to our Cluster and Site IDs.
    desc = "14 - Translate Near Node IDS to Actual IDS. This re-arranges data to provide costs between pairs of cluster and scored site IDs, derived from near-node IDs"
    print(f"{u.getTimeNowStr()} Run: {desc}")        
    # First load distance matrix (in case it wasn't newly generated above)
    nearnode_network_distance_matrix = joblib.load(op_file_dist_matrix)         
    print(f"Actual size of distance matrix = {len(nearnode_network_distance_matrix)}")
    distance_matrix_network = {}
    nearnode2clusterid = dict(zip(cluster_centroids_df.near_node, cluster_centroids_df.cluster_id)) # size of cluster count
    nearnode2validsite = dict(zip(valid_sites.near_node, valid_sites.idnum)) # size of scored site count
    for k in nearnode_network_distance_matrix:
        origin, destination = k
        distance_matrix_network[(nearnode2clusterid[origin], nearnode2validsite[destination])] = \
            nearnode_network_distance_matrix[k]['cost']
    print(f"Size of created distance matrix network = {len(distance_matrix_network)}")

    desc = "15 - Export files - distance matrix network with usable keys, and cluster centroids"
    print(f"{u.getTimeNowStr()} Run: {desc}")        
    # Export distance matrix with usable keys
    joblib.dump(distance_matrix_network, op_file_final_nwk)
    # Export cluster centroids
    joblib.dump(cluster_centroids_df, op_file_cluster_centroids)
