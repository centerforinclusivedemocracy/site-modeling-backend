# Gather Data For All Versions of the Siting Tool, 2020 Election Cycle

# California = VCA Counties
# Colorado = 15 most populous counties
# Texas = 1 most populous county 
# Arizona = 1 most populous county
library(dplyr)
library(scales)
library(data.table)
library(tidycensus)
library(purrr)
library(tidyverse)
library(spdep)
library(rgeos)
library(maptools)
library(rgdal) # load mapping libraries
library(raster)
library(sp)
library(sf)

############# SET UP DATA ############# 
# root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
root = "/Users/lauradaly/Documents/GreenInfo/Contract Work/Siting Tool/" # revised with home computer path

# genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"  # I no longer have access to this folder


# Census api key:
census_api_key("45c000b06fce43fbd4e7631396229ca66612bc9c", install = TRUE, overwrite = TRUE)
readRenviron("~/.Renviron")

#### READ IN HERE COUNTIES INCLUDED IN THE SITING TOOL 
siteCounties = read.csv(paste0(root, "data/admin/Siting_Counties_MasterList.csv"), stringsAsFactors = FALSE)
siteCounties$FIPS = sprintf("%05d", siteCounties$FIPS)

head(siteCounties)


## Using tidycensus, load the variables for 2014-2018 acs
v18 <- load_variables(2018, "acs5", cache = TRUE)

mystates = c("CA", "CO", "AZ", "TX")

# Create a df that can interact with tidycensus
siteCounties$county_code = substr(siteCounties$FIPS, 3, 5)

my_counties <- fips_codes %>%
  filter(state %in% mystates) 

my_counties$FIPS <- paste0(my_counties$state_code, my_counties$county_code)
my_counties = my_counties %>% filter(FIPS %in% siteCounties$FIPS)

#

############# 1. Calculate CVAP Population Share ############# 

# read in CVAP data
cvap = fread(paste0(root, "data/acs/source/CVAP_2014-2018_ACS_csv_files/Tract.csv"), data.table = FALSE)

# review
head(cvap)

# create county fips 
cvap$FIPS <- substr(cvap$geoid, 8, 12)
cvap$GEOID <- substr(cvap$geoid, 8, 18)
head(cvap)

# Grab tracts in the counties of interest
cvap = cvap[cvap$FIPS %in% siteCounties$FIPS & cvap$lntitle =="Total", ]

# split into list by county
cvapDens <- split(cvap, cvap$FIPS, drop = FALSE)

# calculate the share of the county's cvap population that is within the census tract
cvapDens <- lapply(cvapDens, function(x) within(x, cvapDens <- x$cvap_est/sum(x$cvap_est, na.rm=T))) # out of the county's total CVAP, this tract has X% 

# Calculate the margin of error and CV for this derived estimate
cvapDens <- lapply(cvapDens, function(x) within(x, cvapTot.MOE <- moe_sum(x$cvap_moe, x$cvap_est)))
cvapDens <- lapply(cvapDens, function(x) within(x, cvapDens.MOE <- moe_prop(x$cvap_est, sum(x$cvap_est), x$cvap_moe, x$cvapTot.MOE)))
cvapDens <- lapply(cvapDens, function(x) within(x, cvapDens.CV <- ((x$cvapDens.MOE/1.645)/x$cvapDens)*100))

cvapDensDF <- do.call("rbind", cvapDens)

cvapDensDF <- cvapDensDF[,c(10, 1, 9, 7,8, 11:14)]

head(cvapDensDF)
colnames(cvapDensDF)[2] <- "NAME"

dim(subset(cvapDensDF, cvapDens.CV > 40)) # there are 48 unreliable estimates for this indicator

# EXPORT
write.csv(cvapDensDF, paste0(root, "data/acs/CVAP_ShareOfCVAPPopulation.csv"), row.names = FALSE)


############# 2. % Limited English Proficient ############# 
# create list of variables
lepVars <- setNames(c(v18[v18$name %in% c("B06007_005", "B06007_008"), ]$name), 
                    c(rep("LEP", length(v18[v18$name %in% c("B06007_005", "B06007_008"), ]$name))))

# Get the LEP vars for al counties
lepTract <- map2_dfr(
  my_counties$state_code, my_counties$county_code,
  ~ get_acs(
    geography = "tract",
    variables = lepVars,
    state = .x,
    county = .y,
    summary_var = "B06007_001",
    year = 2018,
    survey = "acs5",
    geometry = FALSE
  )
)

# export acs data
write.csv(lepTract, paste0(root, "data/acs/LEP.csv"), row.names = FALSE)



############# 3. % Vehicle Access #############
# NOTE I revised this 02/2020 to match the 2018 Siting Tool--Make variable "Car Access" and then invert in the index.

carVars <- setNames(c(v18[v18$name %like% "B25044_" & !v18$label %like% "No vehicle available" & 
                            !v18$name %in% c("B25044_001", "B25044_002", "B25044_009"), ]$name), 
                    c(rep("CarAccess", length(v18[v18$name %like% "B25044_" & !v18$label %like% "No vehicle available" & 
                                                !v18$name %in% c("B25044_001", "B25044_002", "B25044_009"), ]$name))))

# carVars <- setNames(c(v18[v18$name %like% "B25044_" & v18$label %like% "No vehicle available", ]$name), 
#                     c(rep("NoCar", length(v18[v18$name %like% "B25044_" & v18$label %like% "No vehicle available", ]$name))))

# get lack of car data
carTract <- map2_dfr(
  my_counties$state_code, my_counties$county_code,
  ~ get_acs(
    geography = "tract",
    variables = carVars,
    state = .x,
    county = .y,
    summary_var = "B25044_001",
    year = 2018,
    survey = "acs5",
    geometry = FALSE
  )
)


# export acs data
write.csv(carTract, paste0(root, "data/acs/NoCarAccess.csv"), row.names = FALSE)


############# 4. % Disabled Population ############# 
disabVars <- setNames(c(v18[v18$name %like% "B23024_" & (v18$label %like% "!!With a disability" & !v18$label %like% "!!With a disability!!"), ]$name), 
                      c(rep("disab", 2)))


# get disabled population data
disabTract <- map2_dfr(
  my_counties$state_code, my_counties$county_code,
  ~ get_acs(
    geography = "tract",
    variables = disabVars,
    state = .x,
    county = .y,
    summary_var = "B23024_001",
    year = 2018,
    survey = "acs5",
    geometry = FALSE
  )
)


# export acs data
write.csv(disabTract, paste0(root, "data/acs/DisabledPop.csv"), row.names = FALSE)

############# 5. % Population in Poverty #############
povVars <- c(BelowPoverty ="B17001_002")


# get poverty population data
povTract <- map2_dfr(
  my_counties$state_code, my_counties$county_code,
  ~ get_acs(
    geography = "tract",
    variables = povVars,
    state = .x,
    county = .y,
    summary_var = "B17001_001",
    year = 2018,
    survey = "acs5",
    geometry = FALSE
  )
)


# export acs data
write.csv(povTract, paste0(root, "data/acs/PovertyPop.csv"), row.names = FALSE)


############# 6. % Youth Population #############
youthVar = setNames(c("B01001_007", "B01001_008", "B01001_009", "B01001_010", "B01001_031", "B01001_032", "B01001_033", "B01001_034"), c(rep("youth", 8)))

# get youth population data
youthTract <- map2_dfr(
  my_counties$state_code, my_counties$county_code,
  ~ get_acs(
    geography = "tract",
    variables = youthVar,
    state = .x,
    county = .y,
    summary_var = "B01001_001",
    year = 2018,
    survey = "acs5",
    geometry = FALSE
  )
)


# export acs data
write.csv(youthTract, paste0(root, "data/acs/YouthPop.csv"), row.names = FALSE)

############# 7. % Race and Ethnicity by Tract #####
raceVarList <- c(Latino = "B03002_012", WhiteNHL = "B03002_003",  BlackNHL = "B03002_004", AsianNHL = "B03002_006", NatAmNHL = "B03002_005", Total="B03001_001")


# get race/eth population data
raceEthTract <- map2_dfr(
  my_counties$state_code, my_counties$county_code,
  ~ get_acs(
    geography = "tract",
    variables = raceVarList,
    state = .x,
    county = .y,
    summary_var = "B03002_001",
    year = 2018,
    survey = "acs5",
    geometry = FALSE
  )
)


# export acs data
write.csv(raceEthTract, paste0(root, "data/acs/RaceEthPop.csv"), row.names = FALSE)


# split into list by variable
raceEthTractList <- split(raceEthTract, raceEthTract$variable, drop = FALSE)
head(raceEthTractList[[1]])


############# CALCULATE ALL ACS INDICATORS #####

# read in all the ACS tract variable here--time-consuming to reload the data from tidycensus
cvapDensDF = read.csv(paste0(root, "data/acs/CVAP_ShareOfCVAPPopulation.csv"), stringsAsFactors = FALSE, colClasses = c("FIPS"="character", "GEOID"="character"))
lepTract = read.csv(paste0(root, "data/acs/LEP.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character"))
carTract = read.csv(paste0(root,"data/acs/NoCarAccess.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character"))
disabTract = read.csv(paste0(root,"data/acs/DisabledPop.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character"))
povTract = read.csv(paste0(root,"data/acs/PovertyPop.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character"))
youthTract = read.csv(paste0(root,"data/acs/YouthPop.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character"))
raceEthTract = read.csv(paste0(root, "data/acs/RaceEthPop.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character"))


# grab the total pop
totPopACS = raceEthTract[raceEthTract$variable=="Total", ]

# remove total pop from race/eth df because total pop/total pop doesn't make sense
raceEthTract = raceEthTract[raceEthTract$variable != "Total", ]

# split into list by variable
raceEthTractList <- split(raceEthTract, raceEthTract$variable, drop = FALSE)



# create list with all vars
acsVars = list(
  lep = lepTract, 
  car = carTract,
  disab = disabTract,
  pov = povTract,
  youth = youthTract
)

acsVars = append(acsVars, raceEthTractList)

# get county fips
acsVars = lapply(acsVars, function(x) within(x, FIPS <- substr(x$GEOID, 1, 5)))

## MODEL DATA
# suummarize by indicator by tract
acsVarsSum_mod <-  lapply(acsVars, function(x) x %>%
                   dplyr::group_by(GEOID, NAME, FIPS, variable) %>%
                   dplyr::summarize(
                   count = sum(estimate, na.rm = T),
                   count.MOE = moe_sum(moe, estimate),
                   univ   = mean(summary_est),
                   univ.MOE = mean(summary_moe),
                   prc   = count/univ,
                   prc.MOE = moe_prop(count, univ, count.MOE, univ.MOE),
                   prc.CV  = ((prc.MOE/1.645)/prc)*100) %>% 
                     mutate(flag = ifelse(prc.CV > 40 | is.na(prc.CV), 1, 0),
                            prc = ifelse(count == 0 | univ == 0, 0, prc)))  # THERE CAN BE NO NAs, REPLACE WITH ZERO
# if numerator = 0, then let the data show 0, if univ is 0 make NA. Either way the flag is most likely to be unreliable, but I want to show estimated (unreliable) 0% vs. NA (no universe est)
head(acsVarsSum_mod[[1]])


## WEB DATA--LET THERE BE NA
acsVarsSum_viz <-  lapply(acsVars, function(x) x %>%
                        dplyr::group_by(GEOID, NAME, FIPS, variable) %>%
                        dplyr::summarize(
                          count = sum(estimate, na.rm = T),
                          count.MOE = moe_sum(moe, estimate),
                          univ   = mean(summary_est),
                          univ.MOE = mean(summary_moe),
                          prc   = count/univ,
                          prc.MOE = moe_prop(count, univ, count.MOE, univ.MOE),
                          prc.CV  = ((prc.MOE/1.645)/prc)*100) %>% 
                        mutate(flag = ifelse(prc.CV > 40 | is.na(prc.CV), 1, 0),
                               prc = ifelse(count == 0 & univ !=0, 0,
                                            ifelse(univ == 0, NA, prc))))

head(acsVarsSum_viz[[1]])

## MODEL DATA -- THERE CAN BE NO NAs, REPLACE WITH ZERO
# if numerator = 0, then let the data show 0, if univ is 0 make NA. Either way the flag is most likely to be unreliable, but I want to show estimated (unreliable) 0% vs. NA (no universe est)
# acsVarsSum_m <-  lapply(acsVarsSum_m, function(x) within(x, 
#                                                    prc <- ifelse(x$count ==0 | x$univ == 0, 0, x$prc )))

summary(acsVarsSum_mod[[4]])
summary(acsVarsSum_viz[[4]])


#### Prepare ACS Data -- Make wide, one record per tract : MODEL DATA #####
acsVarsSum_mod <-  lapply(acsVarsSum_mod, function(x) 
  setnames(x, old=c('prc', 'prc.CV', 'flag'), 
           new = c(paste0(x$variable[1], '.prc'), paste0(x$variable[1],'.CV'), paste0(x$variable[1], '_flag'))))

#### Prepare ACS Data -- Make wide, one record per tract : WEB VIZ DATA #####
acsVarsSum_viz <-  lapply(acsVarsSum_viz, function(x) 
  setnames(x, old=c('prc', 'prc.CV', 'flag'), 
           new = c(paste0(x$variable[1], '.prc'), paste0(x$variable[1],'.CV'), paste0(x$variable[1], '_flag'))))


head(acsVarsSum_mod[[4]])
head(acsVarsSum_viz[[4]])

# review--make sure that the _m (model) version has no NAs and the _v (visual) version can have NAs
summary(acsVarsSum_mod[[4]])
summary(acsVarsSum_viz[[4]])


#just keep tract ID columns and the final prc and cv flag (don't keep cv col tho..no need)
acsVarsSum_mod <- lapply(acsVarsSum_mod, function(x) x[,c(1, 2, 3, 9, 12)])
acsVarsSum_viz <- lapply(acsVarsSum_viz, function(x) x[,c(1, 2, 3, 9,  12)])

# join all tracts together
acsVarsDF_mod  <- 
  acsVarsSum_mod %>% 
  reduce(full_join) %>%
  as.data.frame()

head(acsVarsDF_mod)

acsVarsDF_viz  <- 
  acsVarsSum_viz %>% 
  reduce(full_join) %>%
  as.data.frame()

head(acsVarsDF_viz)

# review
summary(acsVarsDF_mod)
summary(acsVarsDF_viz)
# Join in the tract-based CVAP density data
head(cvapDensDF)

acsVarsDFFinal_mod = full_join(acsVarsDF_mod, cvapDensDF[,c(1:3, 6, 9)])
acsVarsDFFinal_viz = full_join(acsVarsDF_viz, cvapDensDF[,c(1:3, 6, 9)])

tail(acsVarsDFFinal_mod)
head(acsVarsDFFinal_viz)

# join in total population data. This will be used when the block population isn't availalbe(new tracts?)
colnames(totPopACS)[4] <- "popACS"

acsVarsDFFinal_mod  = left_join(acsVarsDFFinal_mod, totPopACS[,c(1, 2, 4)])
acsVarsDFFinal_viz  = left_join(acsVarsDFFinal_viz, totPopACS[,c(1, 2, 4)])

# split by state in order to export 1 per state
# create short label
acsVarsDFFinal_mod$State = ifelse(acsVarsDFFinal_mod$NAME %like% ", Arizona", "AZ", 
                              ifelse(acsVarsDFFinal_mod$NAME %like% ", California", "CA",
                                     ifelse(acsVarsDFFinal_mod$NAME %like% ", Colorado", "CO",
                                            ifelse(acsVarsDFFinal_mod$NAME %like% ", Texas", "TX", "check"))))

acsVarsDFFinal_viz$State = ifelse(acsVarsDFFinal_viz$NAME %like% ", Arizona", "AZ", 
                                  ifelse(acsVarsDFFinal_viz$NAME %like% ", California", "CA",
                                         ifelse(acsVarsDFFinal_viz$NAME %like% ", Colorado", "CO",
                                                ifelse(acsVarsDFFinal_viz$NAME %like% ", Texas", "TX", "check"))))

# split
acsVarsFinal_mod <- split(acsVarsDFFinal_mod, acsVarsDFFinal_mod$State, drop = FALSE)
acsVarsFinal_viz <- split(acsVarsDFFinal_viz, acsVarsDFFinal_viz$State, drop = FALSE)


# Export finished tract data files to output folder
# set root
outputRoot = "/Users/lauradaly/Documents/GreenInfo/Contract Work/Siting Tool/data/output/"

# export loop 
for (i in seq_along(acsVarsFinal_mod)) {
  filename = paste("ACS_Indicators_Tracts", names(acsVarsFinal_mod)[i], ".csv", sep = "")
  write.csv(acsVarsFinal_mod[[i]], paste0(outputRoot, filename), row.names = FALSE)
}

# one for the visualize folder
for (i in seq_along(acsVarsFinal_viz)) {
  filename = paste("ACS_Indicators_Tracts", names(acsVarsFinal_viz)[i], ".csv", sep = "")
  write.csv(acsVarsFinal_viz[[i]], paste0(outputRoot,"visualize/", filename), row.names = FALSE)
}




######## Block Population Density (2010 Census) ####
# prepare block 2010 population data
dec <- load_variables(2010, "sf1", cache = TRUE)

options(tigris_use_cache = TRUE)

# just hte data
popBlock <- map2_dfr(
  my_counties$state_code, my_counties$county_code,
  ~ get_decennial(
    geography = "block",
    variables = "P001001", # total pouplation
    state = .x,
    county = .y,
    year = 2010,
    geometry = FALSE
  )
)

head(popBlock)

# export
write.csv(popBlock, paste0(root, "data/decennial/population_Block_2010_Decennial.csv"), row.names = FALSE)


