# -*- coding: utf-8 -*-
"""
Created on Wed Jan  8 13:07:43 2020

@author: Gorgonio

# Note from DK

This script is used to build Geospatial Clusters

We take the census blocks that have registered voters present in the block, 
and then create clusters of blocks to use as our origin site for voting. 
These clusters will be used in the FLP model. 
 
There are too many blocks to run the FLP with them as the origin, therefore we 
# need to perform some sort of spatial aggregation to cut down on complexity; 
the geospatial clustering is how we do that. 

Assumptions
1 - Due to computational constraints, Census Blocks are too numerous to use as a baseline 
"origin" geography. Therefore we must find a way to create a smaller number of 
geographic origins for potential voters (based on registered voter totals). 
We use a K-means algorithm to spatially aggregate adjacent/nearby blocks (using centroids) 
thus allowing a for less spatial complexity. 
2 - Assumes centroids (of blocks) are a good proxy for voter location within blocks
3 - Assumes the K-means aggregation is reasonable and not compromised by true boundaries 
(uncrossable rivers, mountain ranges etc) 
4 - Choice of number of clusters is based off judgment and computation constraints, 
no established method for determining optimal number of clusters. 

"""

import pandas as pd
import numpy as np
from sklearn.externals import joblib
import ccep_utils as u
import ccep_datavars as dv


def run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, ip_path, state_code, plot=False): 
    
    # Input registered voter data
    ip_path_regvoter = f"{ip_path}\RegisteredVoters"
    ip_regvoter_file = f"{ip_path_regvoter}\{state}_Reg_2016.csv"   
    # Prior file was f"{ip_path_regvoter}\{state}_Reg_{county_code}.2016.csv"   
    
    # Output of this CCEP2 script
    op_path_ccep2 = f"{op_path}\CCEP2_Master_County_FLP_Files" 
    op_file_pkl = f"{op_path_ccep2}\{state}_{county_code}_clusters.pkl"
    # CSV used only for examing data and debugging
    op_file_csv = f"{op_path_ccep2}\{state}_{county_code}_clusters_temp.csv"
    
    desc = "01 - Read in blocks data for county"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    df = db.table2df(ssl,f"{county_name}_blocks")    
    print(f"Initial Shape of Blocks Data: {df.shape}")
    # Rename blockid field to geoid for later join to voters
    df['GEOID'] = [int(i) for i in df.blockid10]

    desc = "02 - Read in registered voter data for county"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    # Read state-wide voter data
    voters = pd.read_csv(ip_regvoter_file)
    # Drop any rows where GEOID, county, or R_totreg_r are NA
    voters = voters.dropna(subset=['GEOID', 'county', 'R_totreg_r'])    
    # Extract voter data for this county
    selection_code = f"{state_code}{county_code}"
    voters = voters[voters.county == int(selection_code)]    
    print(f"Shape of Voters Data: {voters.shape}")

    desc = "03 - Join blocks and voters on geoid, and make a geodataframe"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    
    # Join blocks and voters on block id
    df = df.merge(voters, on='GEOID')
    # Num rows will be the smaller of the two. Num cols will be the sum.
    print(f"Shape of Blocks with Voters Data: {df.shape}")
    df = u.make_gpd(df,srid)
    df['geometry'] = df.geometry.centroid
    df['X'] = df.geometry.x
    df['Y'] = df.geometry.y
    X = df[['X','Y']].values
    # Originally was 
    # X = df[['X','Y']].as_matrix()
    # Changed because of warning: 
    # Method .as_matrix will be removed in a future version. Use .values instead.

    desc = "04 - Create clusters - K means"
    print(f"{u.getTimeNowStr()} Run: {desc}")

    # Note from DK: We always want a certain amount of variation in the clusters, 
    # so even if the voting population onlys supports a low number - we set a minimum of 30
    # E.g. if derived = 11 , then we pick 30. If derived = 79 then we pick 79.
    if state == "ca" and county_name == "los_angeles":
        population_threshold = 15000 # To reduce size of distance matrix for LA
        print("Using higher population threshold for LA to reduce size of distance matrix")
    else:
        population_threshold = 10000    
    min_clusters = 30

    # Take sum of all total registered voters and divide by pop threshold, multiply by 2
    num_clusters = int(np.floor((df.R_totreg_r.sum() / population_threshold) * 2))
    # Take higher of this value or 30
    K = max(num_clusters,min_clusters) 
    print(f"Num clusters = {num_clusters}, min = {min_clusters}. Target number of clusters is {K}")

    from sklearn.cluster import KMeans
    # Number of clusters
    kmeans = KMeans(n_clusters=K)
    # Fitting the input data
    kmeans = kmeans.fit(X)
    # Getting the cluster labels
    labels = kmeans.predict(X)
    df['cluster_labels'] = labels
    
    # Centroid values - centroids of new clusters - apprently never used
    # CCEP4 uses centroids, but creates them
    #centroids = kmeans.cluster_centers_ 

    
    # Note: Output cluster file contains centroids of all blocks that did have reg voter data,
    # and the cluster_label column identifies which cluster they belong to
    # There are less rows than the original blocks file, since registered voter data
    # did not exist for all blocks
    # The values of registered voter totals carry forward into the new data as-is,
    # since each point effectively represents the source block it was derived from
    
    if plot:
        df.plot(column='cluster_labels',figsize=(16,16), alpha=.7,legend=True)
        
    desc = "05 - Export clusters as .pkl files, and for internal review also as .csv files"
    print(f"{u.getTimeNowStr()} Run: {desc}")
    # Overwrite if it already exists
    joblib.dump(df, op_file_pkl)
    df.to_csv(op_file_csv,index=False)