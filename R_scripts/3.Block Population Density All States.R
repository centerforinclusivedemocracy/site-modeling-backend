rm(list=ls())
library(dplyr)
library(scales)
library(data.table)
library(tidycensus)
library(purrr)
library(tidyverse)
library(rgeos)
library(rgdal) # load mapping libraries
library(raster)
library(sp)
library(sf)
library(lwgeom)
library(foreign)
root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"

# Read in counties 
siteCounties = read.csv(paste0(root, "data/admin/Siting_Counties_MasterList.csv"), stringsAsFactors = FALSE, colClasses = c("FIPS"="character"))
siteCounties$COUNTYFP10 = substr(siteCounties$FIPS, 3, 5)

### PREPARE BLOCK DATA -- reduce to only counties of interest, export reduced shapefiles #####
# read in original block data
# blocksCA <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="tl_2010_06_tabblock10")
# 
# blocksCO <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="tl_2010_08_tabblock10")
# blocksAZ <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="tl_2010_04013_tabblock10")
# blocksTX <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="tl_2010_48201_tabblock10")
# 
# # Grab only the counties we want
# blocksCA = blocksCA[blocksCA$COUNTYFP10 %in% siteCounties[siteCounties$State=="California", 4], ]
# blocksCO = blocksCO[blocksCO$COUNTYFP10 %in% siteCounties[siteCounties$State=="Colorado", 4], ]
# 
# # for these two states I only downloaded a block shapefile with the one subject county
# head(blocksAZ)
# 
# head(blocksTX)
# 
# 
# ## Calculate area -- units are meters sq
# crs(blocksCA)
# head(blocksCA)
# blocksCA$area_m2 = st_geod_area(blocksCA)
# 
# head(blocksCO)
# blocksCO$area_m2 = st_geod_area(blocksCO)
# 
# blocksAZ$area_m2 = st_geod_area(blocksAZ)
# blocksTX$area_m2 = st_geod_area(blocksTX)
# 
# 
# head(blocksCA)
# 
# setwd("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial")
# 
# # Export reduced shapefiles here:
# write_sf(blocksCA, "blocksCA.shp")
# write_sf(blocksCO, "blocksCO.shp")
# write_sf(blocksAZ, "blocksAZ.shp")
# write_sf(blocksTX, "blocksTX.shp")
# 
# crs(blocksCO)
# head(blocksCO)

##### READ IN BLOCK dbfs HERE ####
blocksCA <- read.dbf("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial/blocksCA.dbf", as.is = TRUE)
blocksCO <- read.dbf("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial/blocksCO.dbf", as.is = TRUE)
blocksAZ <- read.dbf("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial/blocksAZ.dbf", as.is = TRUE)
blocksTX <- read.dbf("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial/blocksTX.dbf", as.is = TRUE)

# revised block shapefiles
# blocksCA <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="blocksCA")
# blocksCO <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="blocksCO")
# blocksAZ <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="blocksAZ")
# blocksTX <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="blocksTX")


### read in block pop data
popBlock = read.csv(paste0(root, "data/decennial/population_Block_2010_Decennial.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character"))
colnames(popBlock)[1] <- "GEOID10"
head(popBlock)

# join block to block pop data 
blocksCA = left_join(blocksCA, popBlock)
blocksCO = left_join(blocksCO, popBlock)
blocksAZ = left_join(blocksAZ, popBlock)
blocksTX = left_join(blocksTX, popBlock)

# Create list
blocks = list("blocksCA" = blocksCA,
              "blocksCO" = blocksCO,
              "blocksAZ" = blocksAZ,
              "blocksTX" = blocksTX)

blocks = lapply(blocks, function(x) within(x, area_km2 <- x$area_m2/1000000))
blocks = lapply(blocks, function(x) within(x, popDensM2  <- x$value/x$area_m2))
blocks = lapply(blocks, function(x) within(x, popDensKM2 <- x$value/x$area_km2))

head(blocks[[1]])

# calculate the share of the county's block population that is in each block
blocks = lapply(blocks, function(x) x %>% 
  group_by(COUNTYFP10) %>%
  mutate(popPrcCounty = value/sum(value)) %>%
    as.data.frame())

head(blocks$blocksCA)


# export revised block dbfs
dencennialRoot = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial"

for (i in seq_along(blocks)) {
  filename = paste(names(blocks)[i], ".dbf", sep = "")
  write.dbf(blocks[[i]], paste0(dencennialRoot, filename))
}

# Export finished block data files to output folder
outputRoot = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output/"

for (i in seq_along(blocks)) {
  filename = paste("PopDensity_Block_", names(blocks)[i], ".csv", sep = "")
  write.csv(blocks[[i]], paste0(outputRoot, filename), row.names = FALSE)
}




### Aggregate to tract (for display purposes only)
head(blocks$blocksCO)

blocksTract = lapply(blocks, function(x) within(x, GEOID_Tract <- substr(x$GEOID10, 1, 11)))
head(blocksTract$blocksTX)

# Aggregate values
blocksTract = lapply(blocksTract, function(x) x %>%
                       group_by(GEOID_Tract, COUNTYFP10) %>%
                       summarize(pop = sum(value),
                                 area_m2 = sum(area_m2),
                                 area_km2 = sum(area_km2),
                                 popDensM2 = pop/area_m2,
                                 popDensKM2 = pop/area_km2))

head(blocksTract$blocksCA)

# calculate the share of the county's block population that is in each block
blocksTract = lapply(blocksTract, function(x) x %>% 
                  group_by(COUNTYFP10) %>%
                  mutate(popPrcCounty = pop/sum(pop)) %>%
                  as.data.frame())

head(blocksTract$blocksAZ)


#### Export as CSV ####
# export revised block dbfs


for (i in seq_along(blocksTract)) {filename = paste("PopDensity_Tract_", names(blocksTract)[i], ".csv", sep = "")
write.csv(blocksTract[[i]], paste0(outputRoot, "visualize/", filename), row.names = FALSE)}
