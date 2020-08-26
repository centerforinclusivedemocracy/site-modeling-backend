# -*- coding: utf-8 -*-
"""
Created on Fri Nov 15 17:16:40 2019

@author: Gorgonio
"""

import time
import datetime
import geopandas as gpd
from shapely import wkb

# Provide t0 as a unit of time (time.time())
def getTimeDiffInMinutes(t0):
    t1 = time.time()
    minutes = round((t1 - t0) / 60, 1)
    return minutes

# Return current time
def getTimeNow():
    return datetime.datetime.now()

# Return current time as formatted string 
def getTimeNowStr():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Return current time as formatted string that works in directory names
def getTimeNowStrForDirs():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def run_query(description, db, query_text):
    t0 = time.time()
    print(f"{getTimeNowStr()} Run query: {description}") # add ,end =  " " to print finish on same line
    db.qry(query_text)
    minutes = getTimeDiffInMinutes(t0)
    print(f"... finished in {minutes} mins")

def make_gpd(df, srid, fromPostgis=True):
    """Converts Pandas Dataframes to GeoPandas GeoDataFrames """    
    if fromPostgis:
        geometry = df['geom'].apply(lambda x: wkb.loads(x, hex=True))
        df = df.drop('geom', axis=1)
        crs = {'init': f'epsg:{srid}'}
        return gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
    else:
        from shapely.geometry import Point
        # TODO: Confirm that this works for CCEP4/5/6 - i.e. no list() or dict() around zip()
        # It works fine for ccep3. Geometry is displayed in df variable, but does not 
        # get used in module.
        geometry = [Point(xy) for xy in zip(df.lon, df.lat)]
        crs = {'init': f'epsg:{srid}'}
        return gpd.GeoDataFrame(df, crs=crs, geometry=geometry)
