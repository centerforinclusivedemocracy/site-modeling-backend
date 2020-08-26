# Bulk GTFS Processing Script

This script prepares the `transit_stops.csv` files as described in https://github.com/GreenInfo-Network/ccep-dk-modeling/issues/24


## Setup and Processing

Place GTFS-compliant folders into the `inputs/` folder. No specific naming convention is necessary, though you may find some naming conventions useful for keeping track of what's what.

Edit the *process_gtfs.py* script, and set up `COUNTY_SETS` with the list of counties and GTFS folders to be processed.

The `STATE_PREFIX` is the state's two-letter code. This will be prepended to the FIPS code to make the CSV filename, e.g. *ca_051.csv*

Each entry of `COUNTY_SETS` is:
* `name` -- a human-readable name for the dataset, just for display
* `outfolder` -- the name of a folder where generated `transit_stops.csv` files will be placed, under the `outputs/` directory
* `gtfsfolders` -- a list of folder names to be processed, located under the `inputs/` directory, full of GTFS-compliant transit CSV files

Then simply run it: `python3 process_gtfs.py`

The generated `transit_stops.csv` files will be placed under the `outputs/` directory, into their specified folders.
