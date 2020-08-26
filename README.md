# ccep-dk-modeling
Code base for doing majority of ccep modeling and creation of files for website.

# History
The CCEP python notebook files as well as the postgispandas code and corresponding .pkl files were inherited from CCEP and DataKind. They have been modified and converted to GreenInfo scripts, to make the execution simpler and more efficient, but leaving the logic unchanged.  The original files have been moved to /archive. 

# Setup

<!-- TOC -->

- [How to get going...](#how-to-get-going)
- [Tools and Technologies used](#tools-and-technologies-used)
    - [Required](#required)
    - [Optional](#optional)
- [Development Enviroment (for Conda, Python)](#development-enviroment-for-conda-python)
    - [1. Set up scip (on Windows)](#1-set-up-scip-on-windows)
    - [2. Set up Conda environment and required packages](#2-set-up-conda-environment-and-required-packages)
    - [3. Install Spyder (IDE)](#3-install-spyder-ide)
- [CCEPScriptInput Data Paths](#ccepscriptinput-data-paths)
- [Postgres database](#postgres-database)
- [Data processing](#data-processing)
    - [1. Census (CCEP1)](#1-census-ccep1)
    - [2. OSM (CCEP1)](#2-osm-ccep1)
    - [3. Census county blocks (R)](#3-census-county-blocks-r)
- [Misc. System and Processing Information](#misc-system-and-processing-information)

<!-- /TOC -->

## How to get going...
- Set up Postgres and PostGIS. Within this, create a database for the project, and the schemas listed below.
- Set up the development environment, i.e the packages listed below. We recommend using the same package versions listed here. Using a higher version might change other dependent versions, and introduce installation challenges. The code hasn't been executed or tested against a different set of versions than what is listed below.
- Get code editors or IDEs set up for Python and R (for Python, it needs to have access to the package installed)
- Copy Census and OSM data into Postgres as described below
- Set up other input data in `CCEPScriptInputs` directory, as required for the python scripts, and R num. 5 script
- Set up empty output directories under `CCEPScriptOutputs`
- In `ccep_datavars.py`, comment any states and counties you do not want to execute (we recommend running just 1 county when first starting out)
- In `ccep_processing.py`, 
   - Add your database access credentials
   - Set up `modules_to_run` to the module you would like to run (we recommending just 1 module at a time when first starting out). You can provide a comma separated list here if you'd like to run multiple modules in sequence.
   - Set up the input and output path (`ip_path` and `op_path`) to point to your directories. All individual scripts will reference this same root path.
- In `5.FinalIndicatorData.R` uncomment the state and county code you'd like to run, and comment the rest
- Execute the python script `ccep_processing.py` either from your IDE or the command line. 
   - It will automatically run for the states and counties in `ccep_datavars.py` and for the modules selected in `ccep_processing.py`. i.e. you do not need to execute the various module scripts independently. 
   - To run a different set of states and counties, or a different module, edit these values and re-run `ccep_processing.py`.
- Order in which to run the scripts:
   - CCEP1 -> CCEP2 - > R num. 5 -> CCEP3 -> CCEP4 -> CCEP5 -> CCEP6
   - The only R script that needs to be run is `5.FinalIndicatorData.R`. It has to be run independently from an R IDE, it cannot currently be called from within the Python scripts.
   - Each individual script, at the top of the code, has variables for all the input (*ip*) paths it will read from. Before running any script, make sure that all the inputs are present.
   - Each individual script, at the top of the code, has variables for all the output (*op*) paths it will write to. Before running the script, make sure that these directories exist in the paths specified.

## Tools and Technologies used
### Required
- PostgreSQL - database management system
- PostGIS - database extension and spatial querying support
- Python, R - programming languages
- Data formats used in project: `.csv` files, `.pkl` files, `.shp` shapefiles, Postgres tables

### Optional
- Anaconda - Package management environment. We used this to install all required packages, and keep the environment (and software) separate from other projects.
- Spyder - IDE (integrated development environment) for Python. This was used to develop, test, and run the code. Any IDE of choice can be used.
- RStudio - IDE for R. Any IDE of choice can be used.
- pgAdmin - User interface to set up schemas in Postgres and examine data for debugging. Other alternate command line interfaces can also be used.
- PostGIS 2.0 Shapefile and DBF Loader Exporter - tool to copy shapefiles from local directories to Postgres. Other alternate command line interfaces can also be used.
- ArcGIS Pro and ArcPy - for any one-off manual processing needed on files, e.g. changing projections, extracting census blocks by county. Any alternate GIS software can be used.
- QGIS - helpful to view spatial data in Postgres

## Development Enviroment (for Conda, Python)

### 1. Set up scip (on Windows)
This is a pre-requisite to installing pyscipopt below
- Download https://scip.zib.de/download.php?fname=SCIPOptSuite-6.0.2-win64-VS15.exe
- Install. Don't check "Add to path", otherwise it may not work
- Update Control Panel - Environment Variables - Path. Add `C:\Program Files\SCIPOptSuite 6.0.2\bin` (or your equivalent directory) to the Path variable.
- Under Environment Variables, also set a new environment variable `SCIPOPTDIR` set to `C:\Program Files\SCIPOptSuite 6.0.2` (or your equivalent directory)
- On a command prompt, try running `scip`, Windows should find and run this command

### 2. Set up Conda environment and required packages
```
conda create -n ccep python=3.6.6
conda activate ccep
conda list                         # Confirm versions
conda install pandas               # Make sure it does not change python version
conda install sqlalchemy
conda install psycopg2
conda install geopandas
conda install matplotlib
conda install pysal
conda install scikit-learn
conda install osmnx
conda install pandana
pip install pyscipopt               # Do this only after scip is installed. Use pip if conda install doesn't work.
conda install -c anaconda openpyxl  # This was added for Expansion, to support configs in Excel files
```
### 3. Install Spyder (IDE) 
If using Spyder as the Python IDE,
```
conda install spyder
```
Spyder 3.3.5 or 3.3.6 might pull in a new version of jupyter_client (5.3.x) that causes Spyder itself not to run. Uninstall jupyter_client and reinstall it specifying a lower version (5.2.4), if Anaconda version permits this.

If uninstalling jupyter client requires uninstalling Spyder as well (on new version of Anaconda), instead install a higher versions of Spyder (4.0.0rc1) which works with a higher version of jupyter_client (5.3.4)

## CCEPScriptInput Data Paths
- `P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptInputs` - All data inputs to scripts that GreenInfo provides will be saved here
   - Data that is loaded into Postgres
      - `\Census` - County (ACS), tract (ACS), and block (decennial 2010) data, for loading into postgres. Note that blocks need to include population. (CCEP1, CCEP2)
      - `\OSM` - OSM POI and road files (CCEP1)
   - Data that is used by pipeline
      - `\Census_County_Blocks` - blocks split out by county (R num. 5)
      - `\FixedSites` - fixed sites for Colorado only (CCEP3, CCEP6)
      - `\GTFS` - transit data, to be generated using scripts and configs in GTFS code directory (R num. 5 and CCEP6)
      - `\Indicator_Layer_Blocks` - indicator blocks that were provided by Laura D. (R num. 5)
      - `\Indicator_Layer_Tracts` - indicator blocks that were provided by Laura D. (CCEP6)
      - `\LKS` - Local knowledge sites (CCEP3, CCEP6) provided by CCEP
      - `\RegisteredVoters` - registered voters provided by Laura D. (CCEP2)

## Postgres database
Using pgAdmin,
- On server `localhost`, create a new database `ccep`
- Create the following schemas:
   - `admin_bounds` (will contain census county, tract, and block data)
   - `osm` (will contain osm roads and points of interest)
   - `suitable_site_layers_xx` (for script output, where 'xx' is the state code, e.g. _ca or _co)
   - `final_suitable_sites_xx` (for script output, where 'xx' is the state code, e.g. _ca or _co)
- Connection information for Gorgonio: host `localhost`, port `5433` (note, not the default 5432), database `ccep`, username `postgres`, password - usual greeninfo password

## Data processing

### 1. Census (CCEP1)

_Note: Years used (2017 or later) may change_

**For counties and tracts:**
- Use national ACS 2017 data (from N drive, or download from here: https://www2.census.gov/geo/tiger/TIGER_DP/2017ACS/)
- Check spatial reference (was 4269). Project all files to EPSG 4326 (WGS 84)
   - Note: Geographic transformation selected was WGS_1984_(ITRF00)_To_NAD_1983
- Extract county and tract files for 4 states (codes 04, 06, 08, 48)
- Using `PostGIS 2.0 Shapefile and DBF Loader Exporter` tool on Windows, copy over the files to the `ccep` database, in `admin_bounds` schema, using `SRID 4326`
   - Leave all options at default. Specifically, don’t check to preserve case of column name, because queries in the inherited scripts use lowercase names

**For blocks:**
- Use decennial census data, updated in 2017 (not the latest, which is 2019). Download from here: https://www.census.gov/cgi-bin/geo/shapefiles/index.php?year=2017&layergroup=Blocks+%282010%29
- Clean up columns (using `Feature Class to Feature Class`). Retain state, county, tract columns. Rename BLOCKCE10 to BLOCKCE and GEOID10 to BLOCKID10 to match prior data and scripts. 
- Download per-block populations from 2010 decennial census
   - Originally we used Laura's intermediate file from `P:\proj_a_d\CCEP\Vote Center Siting Tool\data\02_SitingToolsData_fromLaura\data\output\PopDensity_Block_blocksXX.csv`, but this only had the initial list of counties, not new counties added
   - Later, we generated this data using internal census data script (only for new counties added to scope, in CA and CO), and population is available in `P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptInputs\Census_BlockPop`
- Join blocks data to population on geoid. Note that in different data sources, geoid may be in different field types, and numeric fields won't have leading 0s. This will have to be made consistent before joining.
   - Text to numeric (to strip leading 0s) was throwing errors, instead used text by stripping leading 0 (`!BLOCKID10![1:]`), and numeric-> text conversion in joining data
- New column should be called `pop10` and be of type `Double`
- Join blocks data to population data on the new geoid fields (using `Add Join`, if `Join Field` throws errors)
- Check spatial reference (was 4269). Project all files to EPSG 4326 (WGS 84)
   - Note: Geographic transformation selected was WGS_1984_(ITRF00)_To_NAD_1983
- Using `PostGIS 2.0 Shapefile and DBF Loader Exporter` tool on Windows, copy over the files to the `ccep` database, in `admin_bounds` schema, using `SRID 4326`
   - Leave all options at default. Specifically, don’t check to preserve case of column name, because queries in the inherited scripts use lowercase names
- Verify that pop10 is of type double precision. If not, convert it in pgAdmin - right click on table - properties - columns - select double precision in drop down - save. Re-open and verify again (otherwise step21 of CCEP1 fails)

### 2. OSM (CCEP1)
- Download _extracts_ for all 4 states as shapefiles from [geofabrik](https://download.geofabrik.de/) ([CA](https://download.geofabrik.de/north-america/us/california.html), [AZ](https://download.geofabrik.de/north-america/us/arizona.html), [TX](https://download.geofabrik.de/north-america/us/texas.html), [CO](https://download.geofabrik.de/north-america/us/colorado.html)) 
- Unzip these files. The unzipped directory contains individual shapefiles for Roads (gis_osm_roads_free_1.shp - lines) and POIs (gis_osm_pois_free_1.shp - points).
- Verify all spatial references are EPSG 4326
- Merge northern and southern CA roads into one file, and same with POIs (`Merge` tool in ArcGIS Pro)
- Rename to match what the scripts need (`<state abbreviation>_pois` and `<state abbreviation>_roads`)
- Copy files to `P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptInputs\OSM`
- Using `PostGIS 2.0 Shapefile and DBF Loader Exporter` tool on Windows, copy over the files to the `ccep` database, in `osm` schema, using `SRID 4326`

The QuickOSM plugin was tried but abandoned because it is not intended to be used for large extents, it gives timeout and memory errors. It would also require combining multiple key-value pair combinations into one dataset, which has already been done in pre-processing the extracts above. 

### 3. Census county blocks (R)
- Run the script `ccep_arcpy_datagen_bycounty.py`
- The script uses processed decennial Blocks files from `P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptInputs\Census`, splits them up by County (for the counties being processed for this project, in `ccep_datavars.py`), and deletes the field `pop10` that had been joined to the state-wide Blocks files for CCEP1. 
- Output files by county are written to `P:\proj_a_d\CCEP\Vote Center Siting Tool\data\CCEPScriptInputs\Census_County_Blocks`

## Misc. System and Processing Information
- Data
   - States processed: CA, AZ, TX, CO
   - SRID used: EPSG 4326 (WGS 84)
   - ACS (counties and tracts): 2013-2017 (is the latest 5 yr data available at time of processing, and matches the ACS data used in Laura's new scripts)
   - Blocks (from 2010 decennial census): from 2017 (not the latest, which is 2019)
- Software versions   
   - Postgres server: 9.6.5
   - pgAdmin 4: 3.0
   - Spyder: 3.3.5
   - Conda environment setup was on
      - conda: 4.6.3
      - anaconda-navigator: 1.9.2
   - Development was done on
      - conda: 4.7.12
      - anaconda-navigator: 1.9.7
- Package versions (may be needed if on updated versions of packages, the scripts don't function as intended)
   - python: 3.6.6
   - pip: 19.3.1 (to install pyscipopt)
   - pandas: 0.25.2
   - sqlalchemy: 1.3.10
   - psycopg2: 2.8.4
   - geopandas: 0.6.1
   - matplotlib: 3.1.1
   - pysal: 2.1.0
   - scikit-learn: 0.21.3
   - osmnx: 0.10
   - pandana: 0.4.4
   - pyscipopt: 2.2.1 
   - openpyxl: 3.0.4

