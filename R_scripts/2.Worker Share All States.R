# Create the worker density data 
# from the origin-destination data from LODES

library(data.table)
library(spdep)
library(rgeos)
library(maptools)
library(rgdal) # load mapping libraries
library(raster)
library(sp)
library(RColorBrewer)
library(dplyr)

root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"

# Read in counties 
siteCounties = read.csv(paste0(root, "data/admin/Siting_Counties_MasterList.csv"), stringsAsFactors = FALSE)
siteCounties$FIPS = sprintf("%05d", siteCounties$FIPS)

head(siteCounties)

# 2015: Main (only CA residents)
# Downloaded LODES 7 OD Main
# https://lehd.ces.census.gov/data/#lodes

# w_geocode Char15 Workplace Census Block Code
# h_geocode Char15 Residence Census Block Code 

### load  files
lodesFiles <- list.files(path = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/lehd_lodes/", full.names=TRUE) 


# load csvs
lodes <- lapply(lodesFiles, function(i){
  fread(i, header=TRUE, stringsAsFactors = FALSE, colClasses = c("w_geocode"="character", "h_geocode" = "character"), data.table = FALSE)
}) 

head(lodes[[1]])



# create county id  to query
lodes = lapply(lodes, function(x) within(x, h_FIPS <- substr(x$h_geocode, 1, 5)))
lodes = lapply(lodes, function(x) within(x, w_FIPS <- substr(x$w_geocode, 1, 5)))

# grab only the home and work place within the same county
wrk = lapply(lodes, function(x) x[x$h_FIPS %in% siteCounties$FIPS & x$w_FIPS %in% siteCounties$FIPS, ])
wrk = lapply(wrk, function(x) x[x$h_FIPS == x$w_FIPS, ]) # home and work location has to be same county

head(wrk[[1]])


#### Aggregate on Block ID by county
# Now I know that every block group in this subset originates where it works, so I can just aggregate on work centers

wrkBlock = lapply(wrk, function(x) x %>%
               group_by(w_geocode, w_FIPS) %>%
               summarize(inCounty_JobSum= sum(S000, na.rm=T)))

head(wrkBlock[[1]])

# get in-county job sum
wrkCounty = lapply(wrk, function(x) x %>%
                    group_by(w_FIPS) %>%
                    summarize(tot = sum(S000, na.rm=T)))

wrkCounty = do.call("rbind", wrkCounty)
head(wrkCounty)


# join in county total and calculate the share of in-county jobs in each block
wrkBlock = lapply(wrkBlock, function(x) x %>% left_join(wrkCounty) %>%
                    mutate(jobShare = inCounty_JobSum/tot))

head(wrkBlock[[2]])

# name list elements
names(wrkBlock) <- c("blocksAZ", "blocksCA", "blocksCO", "blocksTX")


# Export finished block data files to output folder
setwd("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output")

for (i in seq_along(wrkBlock)) {
  filename = paste("JobShare_Block_", names(wrkBlock)[i], ".csv", sep = "")
  write.csv(wrkBlock[[i]], filename, row.names = FALSE)
}



#### Merge up to tracts (for visualization only) ####
head(wrkBlock[[4]])

wrkTract <- lapply(wrkBlock, function(x) within(x, GEOID_Tract <- substr(x$w_geocode, 1, 11)))
head(wrkTract$blocksAZ)

# Aggregate on block group id
wrkTract <- lapply(wrkTract, function(x) x %>%
                     group_by(GEOID_Tract, w_FIPS) %>%
                     summarize(inCounty_JobSum = sum(inCounty_JobSum, na.rm = T),
                               tot = mean(tot, na.rm=T),
                               jobShareTract = inCounty_JobSum/tot))
  
head(wrkTract[[1]])

# Export finished block data files to output folder
setwd("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output/visualize")

for (i in seq_along(wrkTract)) {
  filename = paste("JobShare_Tract_", names(wrkTract)[i], ".csv", sep = "")
  write.csv(wrkTract[[i]], filename, row.names = FALSE)
}

