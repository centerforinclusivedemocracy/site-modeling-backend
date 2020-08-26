# -*- coding: utf-8 -*-
"""
Created on Mon Dec 23 09:54:45 2019

@author: Gorgonio

This script is for 1-time data generation of census block files by county, 
to be used in the R scripts.

It needs to be run in a conda environment that includes arcpy
It requires github repo 'gin-gis-shared' to be checked out and available

May require pandas/shapely related imports and functions in ccep_utils to be
temporarily commented before running, if they don't exist in the arcpy environment
"""

import os
import sys
import time
import arcpy
import ccep_datavars as dv # for dict of states and counties


#=====================================================
# Import shared utils from different git repository...
#=====================================================


# Currently supports value as string, or list of numbers
def subsetFileByAttribute(ip, field, value, op_path, op_file):  
    
    # Quit if unsupported type is passed, requires code update to handle additional data types
    if (type(value) is not str and type(value) is not list) or \
        (type(value) is list and type(value[0]) is not int):
        print("Value passed to subsetFileByAttribute() is of unsupported Type. " + 
              "Please update the code to support this data type")
        sys.exit()
    
    if type(value) is str:
        query = f"{field} = '{value}'"
    elif type(value) is list:
        query = "suid_nma in ("
        i = 0
        for v in value:
            if i > 0:
                query = query + ", "
            query = query + str(v)
            i += 1
        query = query + ")"

    print(f"\nInput: {ip}")
    #print(f"Query: {query}") # For debugging
    
    result = arcpy.management.SelectLayerByAttribute(ip, "NEW_SELECTION", query)
    lyr = result.getOutput(0)
    lyr_featurecount = len(lyr.getSelectionSet()) # use this instead of arcpy.management.GetCount(), 
                                                  #  to handle the case of 0 matches
    print(f"Number of features in selection = {lyr_featurecount}")
    
    # The query selection can be done directly in FCtoFC thereby eliminating the code above,
    # but it has been split out to get the count back, and for ease of debugging
    if lyr_featurecount > 0:
        arcpy.conversion.FeatureClassToFeatureClass(lyr, op_path, op_file)
    print(f"Output: {op_path}\{op_file}")
    


if __name__ == '__main__':
    print(f"\nScript processing started...")
    ip_path = r"P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptInputs\Census"
    op_path = r"P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptInputs\Census_County_Blocks"

    for state in dv.states:
        ip_file_path = f"{ip_path}\{state.upper()}_blocks.shp"
        counties = dv.states.get(state)[0]        
        
        for county_name in counties:
            t0 = time.time()
            county_code = counties.get(county_name)[0]
            op_file = f"{state}_c{county_code}_blocks.shp"
            op_file_path = f"{op_path}\{op_file}"
            print(f"\nRunning with {state}, {county_name}, {county_code}...")
            
            subsetFileByAttribute(ip_file_path, "COUNTYFP10", county_code, op_path, op_file)
            # pop10 causes a conflict in the R script, since it already exists in the suitable sites data
            # so delete it
            arcpy.management.DeleteField(op_file_path, "pop10")
            
            print(f"Finished.")
    # End for loop on states
    
    print(f"\nScript processing completed.")
# End if __name__ == __main__
