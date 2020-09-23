# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 10:38:57 2020

@author: Gorgonio


# Note from DK

This script is used for Facility Location Modeling


In this script we pull in the scored suitable sites (CCEP3), the travel time 
matrix (CCEP4), the clusters (CCEP2), etc. and we identify the "optimal" vote areas. 

Assumptions
- Assume shortest path routing reflects the travel patterns of people. 
- Assume routing from place of origin to potential vote site reflects actual 
voter patterns of travel. This could be adjusted if other assumptions were made 
about the share of people originating from different work locations, etc. 
- Assume driving network is a reasonable proxy for travel access to vote sites 
by all population. 
- Assume driving network is a suitable network representation for voter access. 
Though one could attempt to have different networks for different populations 
if they were able to segment their population into different travel modes. 
This would require alternative FLP model formulation. 
- Some FLP parameters were determined based on calibration and best judgement.

"""


import pandas as pd
from sklearn.externals import joblib
import numpy as np
from pyscipopt import multidict, Model, quicksum
import matplotlib.pyplot as plt
from scipy.spatial import KDTree
import ccep_utils as u
from math import ceil
import sys

# Temporary
#import matplotlib
#matplotlib.use('tkagg')

# FLP Model Definition and Execute functions

def flp(I,J,d,M,f,c,k,req_sites=None): 
    model = Model("flp") 
    x,y = {},{}
    for j in J: # J = scored sites
        y[j] = model.addVar(vtype="B", name="y(%s)"%j) 
        for i in I:
            x[i,j] = model.addVar(vtype="C", name="x(%s,%s)"%(i,j)) 
    
    for i in I:
        model.addCons(quicksum(x[i,j] for j in J) == d[i], "Demand(%s)"%i)  # Demand must be satisfied
    
    for j in M:
        model.addCons(quicksum(x[i,j] for i in I) <= M[j]*y[j], "Capacity(%s)"%i)  # Capacity cannot be exceeded
    
    for (i,j) in x:
        model.addCons(x[i,j] <= d[i]*y[j], "Strong(%s,%s)"%(i,j))  # Total demand must be less than total single site supply
        
    model.addCons(quicksum(y[j] for j in J) == k, "Facilities") # Must have a total of this many facilities
    
    if req_sites: ## If enabled these sites must be opened. 
        for j in req_sites:
            model.addCons(y[j] == 1)

    var1 = quicksum(f[j]*y[j] for j in J)
    var2 = quicksum(c[i,j]*x[i,j] for i in I for j in J)
    model.setObjective(var1 + var2, "minimize")
    model.data = x,y 
    return model

def execute_flp(I, J, d, M, f, c,k, type_of_facility, req_sites=False):
    model = flp(I, J, d, M, f, c,k,req_sites=req_sites)
    model.optimize()
    if model.getStatus() == "infeasible":
        print("Model run is 'infeasible'. This is very likely because of conflicting constraints. Please check, fix, and re-try.")
        sys.exit()
    elif model.getStatus() == "optimal":
        EPS = 1.e-6
        x,y = model.data
        edges = [(i,j) for (i,j) in x if model.getVal(x[i,j]) > EPS] 
        facilities = [j for j in y if model.getVal(y[j]) > EPS] 
        print(f"Optimal value = {model.getObjVal()}") 
        print(f"Facilities at nodes for {type_of_facility} = {facilities}")        
        return {'facilities':facilities, 'edges':edges}
    else:
        print(f"Model returned unexpected status of {model.getStatus()}. Please check, fix, and re-try.")
        sys.exit()

def run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, ip_path, county_capacity, site_override, plot=False): 

    ip_scored_sites = f"{op_path}\CCEP3_Master_County_FLP_Files\{state}_{county_code}_all_sites_scored.csv"

    ip_cluster_file = f"{op_path}\CCEP2_Master_County_FLP_Files\{state}_{county_code}_clusters.pkl"
    ip_file_dist_network = f"{op_path}\CCEP4_Final_Network\{state}_{county_code}_clusters2sites_matrix_not_osm_ids.pkl" 
    ip_file_cluster_centroids = f"{op_path}\CCEP4_Cluster_Centroids\{state}_{county_code}_cluster_centroids_df.pkl" 

    op_path_ccep5 = f"{op_path}\CCEP5_Master_County_FLP_Files"
    op_file_3day = f"{op_path_ccep5}\{state}_{county_code}_four_day_sites.csv"
    op_file_10day = f"{op_path_ccep5}\{state}_{county_code}_eleven_day_sites.csv"
    op_file_dropbox = f"{op_path_ccep5}\{state}_{county_code}_dropbox_sites.csv"
    op_file_addnl_model = f"{op_path_ccep5}\{state}_{county_code}_additional_sites_model.csv"
    op_file_addnl_distance = f"{op_path_ccep5}\{state}_{county_code}_additional_sites_distance.csv"
    op_file_cluster_centroids = f"{op_path_ccep5}\{state}_{county_code}_cluster_centroids.csv"
    # Files created for offline debugging of cluster-site distances - selected sites and all cluster-site pairs
    op_file_cluster_site_distances = f"{op_path_ccep5}\{state}_{county_code}_cluster_site_distances.csv"
    op_file_cluster_site_distances_all = f"{op_path_ccep5}\{state}_{county_code}_cluster_site_distances_all.csv"
    
    desc = "01 - Read in scored sites from CCEP3, voter-block clusters from CCEP2, " + \
        "distance matrix and cluster centroids from CCEP4, and county boundary from db"
    print(f"{u.getTimeNowStr()} Run: {desc}")

    scored_sites = pd.read_csv(ip_scored_sites)
    scored_sites = u.make_gpd(scored_sites,srid,fromPostgis=False)
    print(f"Size of scored sites = {scored_sites.shape}")
    
    # Remove any null scores that might have been introduced in the center_score field by R script
    scored_sites = scored_sites[scored_sites.center_score.notnull()]
    print(f"Size of scored sites after removing null center_score values = {scored_sites.shape}")
    # The original code did not drop nulls in droppoff score. Adding here, 
    # since it is used below in qcut, same as center_score
    scored_sites = scored_sites[scored_sites.droppoff_score.notnull()]
    print(f"Size of scored sites after removing null droppoff_score values = {scored_sites.shape}")
    
    cluster_centroids_df = joblib.load(ip_file_cluster_centroids)
    print(f"Size of cluster centroids, i.e. number of clusters = {cluster_centroids_df.shape}")

    block_cluster = joblib.load(ip_cluster_file)
    print(f"Number of blocks that comprise clusters from CCEP2 = {block_cluster.shape}")
    
    # Delete any rows where cluster label isn't in the CCEP4 cluster centroids output, 
    # because CCEP4 dropped it for duplicate nearnode ids
    block_cluster = block_cluster.loc[block_cluster['cluster_labels'].isin(cluster_centroids_df['cluster_id'])]
    print(f"Number of blocks that comprise clusters, after deleting clusters dropped in CCEP4 = {block_cluster.shape}")
    
    print("Loading distance matrix network...")
    distance_matrix_network = joblib.load(ip_file_dist_network)
    print(f"Size of distance matrix network = {len(distance_matrix_network)} (cluster centroids x scored sites)")

    county_gdf = u.make_gpd(db.table2df(ssl,f"{county_name}_county"),srid)
    
    # Note from DK for steps 2, 3 below:
    # Integrate Scores & Adjust Scoring
    # In the FLP Model we use Center / Dropbox Scores to adjust the cost of 
    # opening a facility. If a site has a score near the higher ened of all scores 
    # then the site is cheaper to open compared to a site with a score on the 
    # low end. We are making the sites with higher scores more attractive for 
    # siting a facility by making them cheaper. 

    desc = "02 - Split the center_score into quantiles, and do cost adjustment"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # Split the scores into 5 quantiles
    scored_sites['center_score_qcut'] = pd.qcut(scored_sites.center_score,[0,.2,.4,.6,.8,1])
    # Convert categories to strings
    scored_sites.center_score_qcut = scored_sites.center_score_qcut.astype(str)

    # For each category range, determine how many values exist, and order by categories
    # Note: Order is important because cost adjustment assumes bottom quantiles 
    # are listed first
    ref_qcuts = scored_sites.center_score_qcut.value_counts().sort_index()
    
    # Do the cost adjustment - Top quantiles are 50% the cost, while 
    # bottom quantiles are 200% the cost. 
    cost_adjustment = {}
    scaling = [2, 1.25, 1, .75, .50]
    for idx, i in enumerate(ref_qcuts.index):
        cost_adjustment[i] = scaling[idx]
    # This creates a dict of ranges of center_scores (5 buckets), with a cost factor for each

    # Create lookup of cost adjustment for each scored site by idnum    
    scored_sites['center_score_cost_adjustment'] = scored_sites.center_score_qcut.map(cost_adjustment)        
    cost_adjustment_lookup = dict(zip(scored_sites.idnum, scored_sites.center_score_cost_adjustment))

    desc = "03 - Split the dropoff_score (= dropbox) into quantiles, and do cost adjustment"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # Split the scores into 5 quantiles        
    scored_sites['dropbox_score_qcut'] = pd.qcut(scored_sites.droppoff_score,[0,.2,.4,.6,.8,1])
    # Convert categories to strings        
    scored_sites.dropbox_score_qcut = scored_sites.dropbox_score_qcut.astype(str)
    
    # For each category range, determine how many values exist, and order by categories
    # Note: Order is important because cost adjustment assumes bottom quantiles 
    # are listed first
    ref_qcuts = scored_sites.dropbox_score_qcut.value_counts().sort_index()
    
    cost_adjustment = {}
    scaling = [2, 1.25, 1, .75, .50]
    for idx, i in enumerate(ref_qcuts.index):
        cost_adjustment[i] = scaling[idx]
    # This creates a dict of ranges of dropbox_scores (5 buckets), with a cost factor for each

    # Create lookup of cost adjustment for each scored site by idnum    
    scored_sites['dropbox_cost_adjustment'] = scored_sites.dropbox_score_qcut.map(cost_adjustment)
    dropbox_cost_adjustment_lookup = dict(zip(scored_sites.idnum, scored_sites.dropbox_cost_adjustment))
    
    desc = "04 - Set up capacity for vote sites"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # 3-day (total) capacity thresholds are set up in ccep_datavars, for each county
    # Note from DK: Generally we allow the capacity to be 20,000 but you can calibrate 
    # the model results a bit by editing these values. For Nevada we wanted 
    # greater distribution of sites so we lowered capacity. This is only used 
    # for selecting the three day sites. (Note all 10 day sites are also 3 day sites)

    # capacity for 3-day sites is in ccep_datavars, because it changes by county for CA
	
    capacity_dropbox = 40000 # default for all counties
    if state == "ca" and county_name == "los_angeles": # overwrite only for LA
        capacity_dropbox = 80000 # To allow the model to complete without memory errors
    if state == "az" and county_name == "maricopa": 
        capacity_dropbox = 500000 

    capacity_tenday = 75000
    # The model requires capacity to be > total reg voters / num sites
    # Since the capacity is the same for each site, it might not matter what the value is in our case
    # as long as it's large enough that the right number of sites can be selected to meet demand
    # For CO, the number was too low for 10-day sites for most counties
    # Client doesn't recall source of CA values, and confirmed it is ok to bump up CO value
    if state == "co":
        capacity_tenday = 129000    
    if state == "az" and county_name == "maricopa": 
        capacity_tenday = 200000 
    
    # Creates a dict of site ids, and assigns county's capacity to each
    # Done separately below for M for drop box and 10 day sites
    capacity_val = {i: county_capacity for i in scored_sites.idnum.tolist()}
    

    desc = "05 - Determine the total number of vote sites"
    print(f"{u.getTimeNowStr()} Run: {desc}")
        
    # Verified that sum of R_totreg_r is appropriate given the input data format
    total_required_vote_sites = np.ceil(block_cluster.R_totreg_r.sum()/10000) ## Values provided by CCEP [10,000]
    total_required_10day = np.ceil(block_cluster.R_totreg_r.sum()/50000) ## Values provided by CCEP [50,000]
    total_required_dropbox = np.ceil(block_cluster.R_totreg_r.sum()/15000) ## Values provided by CCEP [15,000]
    
    if len(site_override) > 0: # Will be 3 even if some values are None
        print(f"Overriding voter totals...")
        if site_override[0] is not None: 
            total_required_10day = site_override[0]         # 10 day CA / 15 day CO
        if site_override[1] is not None: 
            total_required_vote_sites = site_override[1]    # 3 day CA / 1 day CO
        if site_override[2] is not None: 
            total_required_dropbox = site_override[2]       # drop box
    
    print(f"Total Vote Sites (3 day) = {int(total_required_vote_sites)}")
    print(f"Total 10 day = {int(total_required_10day)}")
    print(f"Total Drop Box = {int(total_required_dropbox)}")
    
    # Check if a sufficient number of sites have been provided in each category
    # to meet county demand, else log recommended value and exit. If we don't exit here,
    # later the model will fail
    demand = block_cluster.R_totreg_r.sum()
    
    print(f"For county {county_name}, demand to be met = {ceil(demand)}")
    
    supply_10day = total_required_10day * capacity_tenday
    if supply_10day < demand:
        x = demand / capacity_tenday
        y = demand / total_required_10day
        print(f"Ten day sites insufficient. Need {ceil(x)} sites (currently {total_required_10day})" + \
                        f" in ccep_datavars, or {ceil(y)} capacity (currently {capacity_tenday})")
        print("***** Exiting script. Please fix the above problem and retry")
        sys.exit()
    else:
        print(f"Ten day sites sufficient. Supply = {total_required_10day} x {capacity_tenday} = {supply_10day}, Ratio = {supply_10day/demand}")
    
    supply_db = total_required_dropbox * capacity_dropbox
    if (supply_db < demand) and total_required_dropbox > 0:
        x = demand / capacity_dropbox
        y = demand / total_required_dropbox
        print(f"Drop box sites insufficient. Need {ceil(x)} sites (currently {total_required_dropbox})"+ \
                        f" in ccep_datavars, or {ceil(y)} capacity (currently {capacity_dropbox})")
        print("***** Exiting script. Please fix the above problem and retry")        
        sys.exit()
    else:
        print(f"Drop box sites sufficient. Supply = {total_required_dropbox} x {capacity_dropbox} = {supply_db}, Ratio = {supply_db/demand}")

    supply_3day = total_required_vote_sites * county_capacity
    if supply_3day < demand:
        x = demand / county_capacity
        y = demand / total_required_vote_sites
        print(f"Three day sites insufficient. Need {ceil(x)} sites (currently {total_required_vote_sites})" + \
                        f" in ccep_datavars, or {ceil(y)} capacity (currently {county_capacity})")
        print("***** Exiting script. Please fix the above problem and retry")
        sys.exit()
    else:
        print(f"Three day sites sufficient. Supply = {total_required_vote_sites} x {county_capacity} = {supply_3day}, Ratio = {supply_3day/demand}")        
    print() # Space out the logs...
        
    desc = "06 - Set up inputs to FLP model"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # Inputs to model:
    # I = Customers - matches cluster count (list of ints from 0 to n-1)
    # D = dict of I (clusters), with value = reg voter total for that cluster
    # J = Facilities - list of site idnums
    # C = Cost - same as distance matrix network, i.e. all cluster-site pairs with distance between them
    # M = Capacity - pre-defined capacity (3-day in ccep_datavars, dropbox and 10-day defined above)
    # F = Opening Cost - cost factor from above * some fixed constant (12k, 7.5k)    
    # K = number of required vote sites, in each category
    
    # All customers and their demand - demand taken from the Registered Voter Sum
    # Group block centroids (which comprise clusters) by cluster label, and get sum of 
    # registered voters for each group
    I, d = multidict(block_cluster.groupby('cluster_labels').R_totreg_r.sum().to_dict())
    
    ## All potential facilities = all potential scored sites
    J = scored_sites.idnum.tolist()
    
    ## Set up the capacities. The default comes from ccep_datavars, and the other two values are hardcoded here    
    M_all_sites = capacity_val
    M_dropbox = {i: capacity_dropbox for i in J}
    M_tenday = {i: capacity_tenday for i in J}
    
    ## Set up opening costs - costs determined by calibration 
    f_all_sites = {i: 12000 * cost_adjustment_lookup[i] for i in J}
    f_dropbox = {i: 7500 * dropbox_cost_adjustment_lookup[i] for i in J}
    
    f_no_cost = {i: 0 for i in J}
    
    ## Travel costs
    c = distance_matrix_network
    
    # Extract list of fixed sites for CO, for this county
    fs_1day_list = []
    fs_15day_list = []
    if state == "co":
        # 1 day
        fixed_sites_1day = scored_sites[scored_sites.fs_1day == 1]
        if fixed_sites_1day.shape[0] > 0:
            fs_1day_list = fixed_sites_1day['idnum'].tolist()
        # 15 day
        fixed_sites_15day = scored_sites[scored_sites.fs_15day == 1]
        if fixed_sites_15day.shape[0] > 0:
            fs_15day_list = fixed_sites_15day['idnum'].tolist()
            

    desc = "07 - Set up the 3-day locations, using FLP model"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # If fixed sites exist, then provide that to model as required sites to include in output
    if len(fs_1day_list) > 0:
        force_sites = fs_1day_list # Will exist for ~ 11 CO counties
    else:
        force_sites = None
    
    if state == "co":
        print(f"Forced sites list for 1-day layer =  {force_sites}")

    three_day_results = execute_flp(I, J, d, 
        M_all_sites ,  # Note from DK: Assume lower capacity since more people in shorter time
        f_all_sites,  # Note from DK: Same opening cost as 10 day (center score)
        c, 
        total_required_vote_sites, # Note from DK: Include the already identified 10 day sites (for k)
        "3-day sites",
        req_sites =  force_sites
       )
    three_day_facilities = three_day_results['facilities']
    
    if plot:
        # Plot clusters
        ax = block_cluster.plot(column='cluster_labels',figsize=(20,20), alpha=.7,legend=True)
        # Plot points of 3-day sites
        scored_sites[scored_sites.idnum.isin(three_day_facilities)].plot(ax=ax, 
                                                                     color='black',
                                                                     edgecolor='yellow',
                                                                     markersize=100
                                                                    )
        # Plot IDs of 3-day sites
        for idx, row in scored_sites[scored_sites.idnum.isin(three_day_facilities)].iterrows():
            plt.annotate(s=row['idnum'], xy=[row['geometry'].x, row['geometry'].y],
                         horizontalalignment='left',color='black', fontsize=15)
        # Plot county boundary
        county_gdf.plot(ax=ax,color='',edgecolor='red', linewidth=4)        
        # Plot cluster centroids
        cluster_centroids_df.plot(ax=ax, color='blue',edgecolor='red',linewidth=2)
        # Plot IDs of cluster centroids
        for idx, row in cluster_centroids_df.iterrows():
            plt.annotate(s=row['cluster_id'], xy=[row['geometry'].x, row['geometry'].y],
                         horizontalalignment='center',color='green', fontsize=15)
        plt.title('3 Day Sites')

    desc = "08 - Set up the 10-day locations, using FLP model"
    print(f"{u.getTimeNowStr()} Run: {desc}")

    # If fixed sites exist, then provide that to model as required sites to include in output
    if len(fs_15day_list) > 0:
        force_sites = fs_15day_list # Will exist for ~ 4 CO counties
    else:
        force_sites = None

    if state == "co":        
        print(f"Forced sites list for 15-day layer =  {force_sites}")
    
    ten_day_results = execute_flp(I, J, d, 
        M_tenday , # Change to 10-day capacity
        f_all_sites, # See note from DK above: Same opening cost (center score) as 3-day 
        c, 
        total_required_10day, # Limit for 10-day sites (k)
        "10-day sites",
        req_sites =  force_sites
        )

    ten_day_facilities = ten_day_results['facilities']

    if plot:    
        # Plot clusters
        ax = block_cluster.plot(column='cluster_labels',figsize=(20,20), alpha=.7,legend=True)
        # Plot points of 10-day sites
        scored_sites[scored_sites.idnum.isin(ten_day_facilities)].plot(ax=ax, 
                                                                     color='black',
                                                                     edgecolor='yellow',
                                                                     markersize=100
                                                                    )
        # This was commented by DK, throws an error
        #cluster_centroids_df[cluster_centroids_df.cluster_id.isin(facilities)].plot(ax=ax, color='red',markersize=60)
        
        plt.title('10 Day Sites')
        
    desc = "09 - Select additional 10-day sites from 3-day sites (off-model)"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    # Note from DK: Since all 10 days sites are also 3 day sites, we find the 
    # nearest 3 day sites to the FLP selected 10 day sites, and then make 
    # those our 10 day sites. 

    # Set up the tree for 3-day sites
    
    # Limit to just the 3-day Sites
    df3 = scored_sites[scored_sites.idnum.isin(three_day_facilities)]
    # Save a list of coordinates for those sites
    df3_coords = list(zip(df3.lon, df3.lat))    
    # Load the KD tree with those coordinates
    tree = KDTree(df3_coords)
    
    # Prep the 10-day sites
    
    # Same as above but we don't load the tree because we are searching for 
    # the sites nearest to these. 
    df10 = scored_sites[scored_sites.idnum.isin(ten_day_facilities)]
    df10_coords = list(zip(df10.lon, df10.lat))
    
    # Find the nearest sites    
    selected_3day_indices = []
    for idx10, site in enumerate(df10_coords):
        # https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.spatial.KDTree.query.html
        # Up to 5 are returned, but 1 is selected
        distances, indices = tree.query(site,k=5)
        for idx, nearby_site in enumerate(indices):
            print(f"distance = {distances[idx]}, nearby site = {nearby_site}")
            if nearby_site in selected_3day_indices:
                print('site already selected')
                pass
            else:
                selected_3day_indices.append(nearby_site)
                break
    
    off_model_10day = df3.iloc[selected_3day_indices]
    print(f"Off model 10-day sites = {off_model_10day['idnum'].tolist()}")
    
    if plot:
        # This was commented by DK. Leaving as is.
        #three_day_facilities = list(set(three_day_facilities) - set(ten_day_facilities))
        
        ax = block_cluster.plot(column='cluster_labels',figsize=(20,20), alpha=.7,legend=True)
        scored_sites[scored_sites.idnum.isin(three_day_facilities)].plot(ax=ax, 
                                                                     color='black',
                                                                     edgecolor='yellow',
                                                                     markersize=100
                                                                    )
        
        scored_sites[scored_sites.idnum.isin(ten_day_facilities)].plot(ax=ax, 
                                                                     color='red',
                                                                     edgecolor='yellow',
                                                                     markersize=50
                                                                    )
        off_model_10day.plot(ax=ax, 
                                                                     color='blue',
                                                                     edgecolor='blue',
                                                                     markersize=25
                                                                    )
        plt.title('10 and 3 Day Sites')        
    
    desc = "10 - Set up the dropbox locations, using FLP model"
    print(f"{u.getTimeNowStr()} Run: {desc}")

    # Note from DK: Dropbox sites are distinct from 10 and 3 day sites, so we 
    # just run the model and identify the "best" sites. 
    if total_required_dropbox > 0:
        dropbox_sites_network_result = execute_flp(I, J, d, 
                                                   M_dropbox, 
                                                   f_dropbox, c, 
                                                   total_required_dropbox, # For k
                                                   "drop box sites")
        dropbox_facilities = dropbox_sites_network_result['facilities']
        if plot:
            ax = block_cluster.plot(column='cluster_labels',figsize=(20,20), alpha=.7,legend=True)
            scored_sites[scored_sites.idnum.isin(dropbox_facilities)].plot(ax=ax, color='red',markersize=60)
    else:
        dropbox_facilities = []
        

    desc = "11 - Set up the additional sites (10% more than 3-day sites), using FLP model"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # Note from DK: There was a request to be identify 10% more sites if a 
    # county had the resources and desire to open more than the minimum number 
    # of sites. Here we run the model with the already chosen sites fixed, 
    # but allowing for choosing an additional 10%. So the 3 day sites stay the 
    # same that were chosen above - but we add some more sites. 
    
    total_req_sites_plus10prc = np.ceil(total_required_vote_sites *1.10)
    print(f"Number of additional sites requested = {int(total_req_sites_plus10prc - total_required_vote_sites)}")

    additional_sites_result = execute_flp(I, J, d, 
                                    M_all_sites ,  # Assume lower capacity since more people in shorter time
                                    f_all_sites,  # Same opening cost as 10 day (center score)
                                    c, 
                                    total_req_sites_plus10prc, # for k
                                    "additional sites (superset)",
                                    req_sites = three_day_facilities  # Include the already identified 3 day sites
                                   )
    additional_sites = additional_sites_result['facilities']
    # Remove the already selected sites from the list so we just have the additional site(s).
    additional_sites = list(set(additional_sites) - set(three_day_facilities))
    print(f"Final list of additional sites = {additional_sites}")
    
    if plot:
        ax = block_cluster.plot(column='cluster_labels',figsize=(20,20), alpha=.7,legend=True)
        scored_sites[scored_sites.idnum.isin(three_day_facilities)].plot(ax=ax, 
                                                                     color='black',
                                                                     edgecolor='yellow',
                                                                     markersize=100
                                                                    )
        # Plot additional sites in blue
        scored_sites[scored_sites.idnum.isin(additional_sites)].plot(ax=ax, 
                                                                     color='blue',
                                                                     edgecolor='yellow',
                                                                     markersize=50
                                                                    )
        plt.title('3 Day Sites and Additional Sites')        

    desc = "12 - Prep for additional sites (to mitigate for > 15 mins travel time), using Distance method"
    print(f"{u.getTimeNowStr()} Run: {desc}")

    # Note from DK The distance method looks for sites that have a travel time 
    # greater than 15 minutes to their nearest vote site. It then searches to 
    # see if there is a potential vote site that would offer a lower travel time 
    # avaiable (within a threshold - must be at least 25% less time). So 30 min 
    # vs 31 min minutes wouldn't be selected because the time savings are neglibible. 
    
    # Identify the sites over 15 minutes
    cluster_centroids_df['lon'] = cluster_centroids_df.geometry.x
    cluster_centroids_df['lat'] = cluster_centroids_df.geometry.y
    cluster_centroids_df.to_csv(op_file_cluster_centroids, index=False)
    
    over_15 = []
    debug_df = pd.DataFrame(columns=['cluster', 'site', 'cost'])
    for edg in three_day_results['edges']:
        dist_val = np.round(distance_matrix_network[edg],2)
        debug_df = debug_df.append({'cluster':edg[0], 'site':edg[1], 'cost':dist_val}, ignore_index=True)
        if dist_val > 15:
            over_15.append([edg[0],np.round(distance_matrix_network[edg],2)])
    debug_df.to_csv(op_file_cluster_site_distances, index=False)
    if len(over_15) > 0:
        over_15 = pd.DataFrame(over_15,columns=['cluster_id','traveltime'])
        over_15 = over_15.groupby('cluster_id').mean().reset_index().sort_values('traveltime',ascending=False)    
        over_15 = over_15.merge(cluster_centroids_df[['cluster_id','lon','lat']], on='cluster_id',how='left')
        
        if plot:
            # This was commented by DK
            # ax = block_cluster.plot(column='cluster_labels',figsize=(20,20), alpha=.7,legend=True)
            ax = block_cluster.plot(color='gray',figsize=(20,20), alpha=.7,legend=True)
            scored_sites.plot(color='yellow',edgecolor='red',ax=ax,alpha=1,legend=True, markersize=20)        
            scored_sites[scored_sites.idnum.isin(three_day_facilities)].plot(ax=ax, 
                                                                         color='black',
                                                                         edgecolor='yellow',
                                                                         markersize=100
                                                                        )
            # Plot the over-15 sites
            cluster_centroids_df[cluster_centroids_df.cluster_id.isin(over_15.cluster_id)].plot(ax=ax,
                                                                                                color='red',
                                                                                               edgecolor='yellow',
                                                                                               markersize=100)        
    else:
        print("*** All sites are within 15 cost units of the cluster centroids. " + 
              "No additional sites by distance data will be generated")
    
    desc = "13 - Set up potential vote sites for 15 min distance mitigation"
    print(f"{u.getTimeNowStr()} Run: {desc}")

    selected_additional_sites = []

    if len(over_15)> 0:    
        # Note from DK: for each site first identify the 3 nearest
        
        # Save a list of coordinates for those sites
        valid_sites_coords = list(zip(scored_sites.lon, scored_sites.lat))    
        ## Load the KD tree with those coordinates. 
        tree = KDTree(valid_sites_coords)
        
        over_15_cords = list(zip(over_15.lon, over_15.lat))
        
        # Set up ID lookups 
        vs_index2id_lookup = dict(zip([i for i in range(len(scored_sites))],scored_sites.idnum))
        o15_index2id_lookup = dict(zip([i for i in range(len(over_15))],over_15.cluster_id))
        
        # Find potential additional sites    
        for idx_over15, site in enumerate(over_15_cords):
            # https://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.spatial.KDTree.query.html
            distances, indices = tree.query(site,k=5)
            current_travel_time = over_15[over_15.cluster_id == o15_index2id_lookup[idx_over15]].traveltime.values[0]
            for idx, nearby_site in enumerate(indices):
                near_site_travel_time = distance_matrix_network[(o15_index2id_lookup[idx_over15], 
                                                                    vs_index2id_lookup[nearby_site])]
                if current_travel_time * .75 > near_site_travel_time:
                    print('origin', o15_index2id_lookup[idx_over15],
                          '- dest', vs_index2id_lookup[nearby_site],\
                          '- current travel time (nearest vote site)', current_travel_time,\
                          '- near site travel time', near_site_travel_time) 
                    selected_additional_sites.append(vs_index2id_lookup[nearby_site])
                    break
        selected_additional_sites = list(set(selected_additional_sites))  

        if plot:
            # This was commented by DK        
            # ax = block_cluster.plot(column='cluster_labels',figsize=(20,20), alpha=.7,legend=True)
            # ax = block_cluster.plot(color='gray',figsize=(20,20), alpha=.7,legend=True)
    
            ax = scored_sites.plot(color='gray',figsize=(20,20), alpha=.7,legend=True)
            # Plot suggested sites
            scored_sites[scored_sites.idnum.isin(three_day_facilities)].plot(ax=ax, 
                                                                         color='black',
                                                                         edgecolor='yellow',
                                                                         markersize=100
                                                                        )
            # Plot over-15-min sites
            cluster_centroids_df[cluster_centroids_df.cluster_id.isin(over_15.cluster_id)].plot(ax=ax,
                                                                                                color='',
                                                                                               edgecolor='red',
                                                                                                linewidth=4,
                                                                                               markersize=300)
            # Plot potential vote sites
            if len(selected_additional_sites) > 0:
                scored_sites[scored_sites.idnum.isin(selected_additional_sites)].plot(ax=ax, 
                                                                             color='black',
                                                                             edgecolor='blue',
                                                                             markersize=100,
                                                                             linewidth=2      
                                                                            )        

    print(f"Potential vote sites for 15 min distance mitigation = {selected_additional_sites}")

    print("\n") # To declutter summary from all the previous logging
    desc = "14 - Collate all the various site variables created"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    print(f"3-day sites, from step 7 ({len(three_day_facilities)}) = {three_day_facilities}") # Exported
    print(f"10-day sites, from step 8 ({len(ten_day_facilities)}) = {ten_day_facilities}")  # NOT Exported  
    print(f"Dropbox sites, from step 10 ({len(dropbox_facilities)}) = {dropbox_facilities}") # Exported
    print(f"Additional 10-day sites from 3-day sites (off-model), from step 9 = {off_model_10day['idnum'].tolist()}") # Exported as 10-day
    print(f"Additional sites (10% more than 3-day sites), from step 11 = {additional_sites}") # Exported
    print(f"Potential voter sites for > 15 mins travel time, from step 13 = {selected_additional_sites}\n") # Exported

    desc = "15 - Export files"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    debug_df_all = pd.DataFrame(columns=['cluster', 'site', 'cost'])
    for k in distance_matrix_network.keys():    
        cluster = k[0]
        site = k[1]
        cost_val = distance_matrix_network.get(k)
        debug_df_all = debug_df_all.append({'cluster':cluster, 'site':site, 'cost':cost_val}, ignore_index=True)
    debug_df_all.to_csv(op_file_cluster_site_distances_all, index=False)
        
    # Note from DK: First Remove Columns That Cause Errors
    scored_sites = scored_sites.drop('center_score_qcut',axis=1)
    scored_sites = scored_sites.drop('dropbox_score_qcut',axis=1)

    # Export 3/4 day sites
    scored_sites[scored_sites.idnum.isin(three_day_facilities)].to_csv(op_file_3day,index=False)
    
    # Export 10/11 day sites
    scored_sites[scored_sites.idnum.isin(off_model_10day.idnum)].to_csv(op_file_10day,index=False)
    
    # Export dropbox sites
    scored_sites[scored_sites.idnum.isin(dropbox_facilities)].to_csv(op_file_dropbox,index=False)
    
    # Export additional sites (10% more than 3 day)
    scored_sites[scored_sites.idnum.isin(additional_sites)].to_csv(op_file_addnl_model,index=False)

    # Export potential voter sites, for > 15 mins travel time mitigation
    scored_sites[scored_sites.idnum.isin(selected_additional_sites)].to_csv(op_file_addnl_distance,index=False)
