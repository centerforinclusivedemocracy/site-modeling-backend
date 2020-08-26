# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 15:25:01 2019

@author: Gorgonio

This script calls the individual CCEP scripts, as specified in modules_to_run

It loops through the state and county dictionaries in ccep_datavars, and runs 
the CCEP scripts for one county at a time, passing through any variables for that
state/county that were specified in ccep_datavars

"""

#=====================
# Import modules
#=====================
import time
import ccep_utils as u
import ccep_datavars as dv # for dict of states and counties
import ccep01
import ccep02
import ccep03
import ccep04
import ccep05
import ccep06

#============================
# Choosing modules to run
#============================
# At this time, all modules cannot be run successively, until the R scripts 
# are called from in here. Until then, use this list to execute in the right order
# CCEP1 -> R (offline, requires ccep1) -> CCEP3 -> CCEP 4 -> CCEP5 -> CCEP6
# CCEP2 -> CCEP4 -> CCEP5 -> CCEP6
modules_to_run = ["CCEP1"]

# Whether or not to display plots
displayPlot = False


#============================
# Set up paths and variables
#============================

op_path = r"P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptOutputs"
ip_path = r"P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptInputs"

# Input data is in this SRID (census, OSM)
# If this changes, re-run the R scripts as well (SRID picked up from county blocks for scored sites)
srid = "4326"
mts_in_pt05mile = "800"

#=========================
# DB access and connection
#=========================

db_config_file = "ccep_postgispandas.py"

#TODO: Take password from user, don't hardcode it here
db_info = {
    "dbname": "ccep",
    "host": "localhost", 
    "port": "5433",
    "user": "postgres",
    "pwd": "" # Enter password here before running
    }

# Open connection to DB
with open(db_config_file) as f:
    code = compile(f.read(), db_config_file, 'exec')
    exec(code, globals(), locals())    
db = postgis_pandas(db_info,do_echo=False) # class in ccep_postgispandas.py, via db_config_file

#=====================
# Functions
#=====================

def db_setup():
    print()
    # Create db ccep
    # Create schema admin bounds
    # --- Load data counties, tracts, blocks
    # Create schema osm
    # --- Load data roads, pois
    # Create schema suitable_site_layers
    
#=====================
# Execution
#=====================
if __name__ == '__main__':
    start_time = time.time()
    #op_time = u.getTimeNowStr()
    print(f"\n{u.getTimeNowStr()} CCEP processing started...")
    
    for state in dv.states:
        counties = dv.states.get(state)[0]
        state_srid = dv.states.get(state)[1]
        state_code = dv.states.get(state)[2]
        for county_name in counties:
            county_code = counties.get(county_name)[0]
            county_bbox = counties.get(county_name)[1] # For CCEP4
            county_capacity = counties.get(county_name)[2] # For CCEP5
            county_site_override = counties.get(county_name)[3] # For CCEP5
            
            ssl = f"{dv.ssl}_{state}"
            fssl = f"{dv.fssl}_{state}"
            
            for module in modules_to_run:
                print(f"\n{u.getTimeNowStr()} Running {module} with {state.upper()}, {county_name}, {county_code}...")
                t0 = time.time()
                
                if module == "CCEP1":
                    ccep01.run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, state_srid, mts_in_pt05mile)
                elif module == "CCEP2":
                    ccep02.run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, ip_path, state_code, plot=displayPlot) 
                elif module == "CCEP3":
                    ccep03.run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, ip_path, plot=displayPlot) 
                elif module == "CCEP4":
                    ccep04.run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, ip_path, county_bbox, plot=displayPlot) 
                elif module == "CCEP5":
                    ccep05.run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, ip_path, county_capacity, county_site_override, plot=displayPlot) 
                elif module == "CCEP6":
                    ccep06.run_module(db, state, county_name, county_code, op_path, srid, ssl, fssl, state_srid, ip_path, state_code, plot=displayPlot)
                else:
                    print("Unsupported module specified. Please set 'modules_to_run' to be one or more of CCEP1 - CCEP6")

                minutes = u.getTimeDiffInMinutes(t0)
                print(f"\n{u.getTimeNowStr()} {module} for {state.upper()}, {county_name}, {county_code} finished in {minutes} mins")

        # End for loop on counties    
    # End for loop on states
    
    minutes = u.getTimeDiffInMinutes(start_time)
    print(f"\n{u.getTimeNowStr()} CCEP processing completed. Total time taken = {minutes} minutes")
# End if __name__ == __main__
