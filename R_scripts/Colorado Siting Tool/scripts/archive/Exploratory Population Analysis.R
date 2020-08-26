library(dplyr)
library(scales)
library(data.table)
library(sf)
library(tidycensus)
library(purrr)
library(tidyverse)
library(tidyr) 

# Set up root directory
if (paste(Sys.getenv('USER')) == "") {
  root <- "C:/Users/lauradal/Box/CCEP Files/Colorado Siting Tool/data/"
}

#using tidycensus 

# Census emailed me this api key:
census_api_key("45c000b06fce43fbd4e7631396229ca66612bc9c", install = TRUE, overwrite = TRUE)
readRenviron("~/.Renviron")

## Using tidycensus, load the variables for 2017 acs
v17 <- load_variables(2017, "acs5", cache = TRUE)

########  1. Race/Ethnicity Population #### 
popVarList <- c("B03002_012", "B03002_003", "B03002_004", "B03002_006")

# review variables
subset(v17, name %in% popVarList)


pop <- get_acs(geography = "county", state = "CO", variables = "B03002_001",  year=2017, survey = "acs5")
head(pop)

popRaceEth <- get_acs(geography = "county", state = "CO", variables = popVarList, summary_var = "B03002_001",  year=2017, survey = "acs5")
head(popRaceEth)

# categorize by race and ethniciy
popRaceEth$RaceEth = ifelse(grepl("_003", popRaceEth$variable), "White NHL", 
                                           ifelse(grepl("_004", popRaceEth$variable), "Black",
                                                  ifelse(grepl("_006", popRaceEth$variable), "Asian",
                                                         ifelse(grepl("_012", popRaceEth$variable), "Latino", NA))))

# recode NAs to zero because these are controlled estimates
pop$moe[is.na(pop$moe)] <- 0
popRaceEth$moe[is.na(popRaceEth$moe)] <- 0
popRaceEth$summary_moe[is.na(popRaceEth$summary_moe)] <- 0

### Quick look at population stats for the county ####

# race eth
popRaceEth_Sum =
  popRaceEth %>%
    mutate(prc = estimate/summary_est,
           moe_deriv=moe_prop(estimate, summary_est, moe, summary_moe),
           CV_prc= ((moe_deriv/1.645)/prc)*100)
popRaceEth_Sum


# 15 highest-population counties
bus_stateTop <-  bus_stateTop$NAICS.display.label[order(bus_stateTop$FIRMPDEMP.x, decreasing = TRUE)] # this isn't even referencing a column that exists anymore....

popTop = pop$NAME[order(pop$estimate, decreasing = TRUE)]
popTop = popTop[1:15]


popRaceEth_Sum = popRaceEth_Sum[popRaceEth_Sum$NAME %in% popTop, ]
table(popRaceEth_Sum$NAME)


#### Tract Analysis ####
popTract = get_acs(geography = "tract", state="CO", variables = "B03002_001",  year=2017, survey = "acs5")
head(popTract)

library(raster)

tracts = shapefile(paste0(root, "Census/tl_2017_08_tract.shp"))

test = tracts[tracts@data$GEOID]
plot(tracts)


