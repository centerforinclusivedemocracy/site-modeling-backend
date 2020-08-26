# Calculate Eligible Non-Registered Voter Rates, Colorado

library(data.table)
library(dplyr)
library(rgeos)
library(rgdal) # load mapping libraries
library(raster)
library(sp)
library(sf)
library(lwgeom)

root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
COroot ="C:/Users/lauradal/Box/CCEP Files/Siting Tool/Colorado Siting Tool/data/"
genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"

#### Prepare Data ####
gen14 = read.csv(paste0(COroot, "voter/2014GeneralPrecinctTurnout.csv"), stringsAsFactors = FALSE, colClasses = c("Precinct"="character"))
head(gen14)

gen16 = read.csv(paste0(COroot, "voter/2016GeneralTurnoutPrecinctLevel.csv"), stringsAsFactors = FALSE, colClasses = c("Precinct"="character"))

head(gen16)

# temp: get number of voters in our counties of interest
test = gen16[gen16$NAME %in% site_co$CountyName, ]
head(test)
sum(test$Ballots.Cast, na.rm = T)

#### READ IN HERE COUNTIES INCLUDED IN THE SITING TOOL 
siteCounties = read.csv(paste0(root, "data/admin/Siting_Counties_MasterList.csv"), stringsAsFactors = FALSE)
siteCounties$FIPS = sprintf("%05d", siteCounties$FIPS)
site_co = siteCounties[siteCounties$State=="Colorado",]

# read in CVAP data
cvap = fread(paste0(genRoot, "CVAP/CVAP_2013_2017/Tract.csv"), data.table = FALSE, colClasses = c("geoid"="character"))

# create county fips 
cvap$FIPS <- substr(cvap$geoid, 8, 12)
cvap$GEOID <- substr(cvap$geoid, 8, 18)
head(cvap)

# Grab tracts in the counties of interest
cvap = cvap[cvap$FIPS %in% siteCounties$FIPS & cvap$lntitle =="Total" & cvap$GEONAME %like% ", Colorado", ]
dim(cvap)



## Read in the incarcerated population data from the 2010 census (TRACTS)
instPop <- read.csv(paste0(COroot, "institutionalized_pop/DEC_10_SF1_P42_with_ann.csv"), header = TRUE, 
                    stringsAsFactors = FALSE, skip=1,colClasses = c(Id2='character'))

instPop <- instPop[,c(2,4,6)]
colnames(instPop) <- c("GEOID", "TotalGroupQuarters", "Incarc_Adults")

head(instPop)

### non institutionalized pop data
totNonInstPop <- read.csv(paste0(COroot, "institutionalized_pop/ACS_17_5YR_S1810_with_ann.csv"), header = TRUE, stringsAsFactors = FALSE, skip=1, colClasses = c(Id2='character'))
totNonInstPop <- totNonInstPop[,c(2, 4:5)]
colnames(totNonInstPop) <- c("GEOID", "tract_TotNonInstPop", "tract_TotNonInstPop.MOE")
head(totNonInstPop)


### Prepare the registration data #####
# first average the registration rate for 2014 and 2016 general elections
colnames(gen14)[8] <- "Tot.Reg.14"
colnames(gen16)[8] <- "Tot.Reg.16"
reg = full_join(gen14[,c(1,5,10, 8)], gen16[,c(1,5, 10, 8)])
head(reg)

reg$avg.Reg = rowMeans(reg[,c(4:5)], na.rm = T)
colnames(reg)[2:3] <- c("PRECINCT", "County")
head(reg)


##### CAlculate the proportion of each precinct that is in each block ####
## load precinct shapefile
# note this is what was posted online, but is not necessarily the same precinct as the 2016/2014 general elections

### load  files
preclist = list(
  Denver = read_sf(dsn=paste0(COroot, "voter/precincts/Denver County"), layer="DENVER_PRECINCTS_CLEAN_2018"),
  Arapahoe = read_sf(dsn=paste0(COroot, "voter/precincts/Arapahoe County"), layer="2017_Precinct_Boundaries"),
  ElPaso = read_sf(dsn=paste0(COroot, "voter/precincts/El Paso County"), layer="EPC_Precincts"),
  Jefferson = read_sf(dsn=paste0(COroot, "voter/precincts/Jefferson County"), layer="County_Precinct"),
  Adams = read_sf(dsn=paste0(COroot, "voter/precincts/Adams County"), layer="Adams_Precincts"),
  Boulder = read_sf(dsn=paste0(COroot, "voter/precincts/Boulder County"), layer="Precincts"),
  Larimer = read_sf(dsn=paste0(COroot, "voter/precincts/Larimer County"), layer="VoterPrecinct"),
  Weld = read_sf(dsn=paste0(COroot, "voter/precincts/Weld County"), layer="Elections_Precincts"),
  Douglas = read_sf(dsn=paste0(COroot, "voter/precincts/Douglas County"), layer="precinct"),
  Mesa = read_sf(dsn=paste0(COroot, "voter/precincts/Mesa County"), layer="Precinct"),
  Pueblo = read_sf(dsn=paste0(COroot, "voter/precincts/Pueblo County"), layer="Precincts_180313"),
  Garfield = read_sf(dsn=paste0(COroot, "voter/precincts/Garfield County"), layer="VoterPrecincts022118"),
  LaPlata = read_sf(dsn=paste0(COroot, "voter/precincts/La Plata County"), layer="LPC_Voting_Precincts"),
  Broomfield = read_sf(dsn=paste0(COroot, "voter/precincts/Broomfield County"), layer="Precincts"),
  Eagle = read_sf(dsn=paste0(COroot, "voter/precincts/Eagle County"), layer="VoterPrecincts022018")
)

head(preclist[[2]])


# isolate fields, only the precinct number so I can standardize the field names and combine
preclist[[1]] = preclist[[1]][,c(2, 1)]
preclist[[2]] = preclist[[2]][,c(7, 8)]
preclist[[3]] = preclist[[3]][,c(6, 2)]
preclist[[4]] = preclist[[4]][,c(2, 1)]
preclist[[5]] = preclist[[5]][,c(2, 1)]
preclist[[6]] = preclist[[6]][,c(3, 4)]
preclist[[7]] = preclist[[7]][,c(3, 1)]
preclist[[8]] = preclist[[8]][,c(6, 4)]
preclist[[9]] = preclist[[9]][,c(6, 5)]
preclist[[10]] = preclist[[10]][,c(2,1)]
preclist[[11]] = preclist[[11]][,c(11, 10)]
preclist[[12]] = preclist[[12]][,c(1, 2)]
preclist[[13]] = preclist[[13]][,c(5, 1)]
preclist[[14]] = preclist[[14]][,c(4, 6)]
preclist[[15]] = preclist[[15]][,c(11, 7)]

# rename columns
clnames = c("PRECINCT", "precNum", "geometry")

preclist = lapply(preclist, setNames, nm= clnames)

head(preclist[[5]])

# add county name as id
countylist = site_co$CountyName
fips = site_co$FIPS

preclist = mapply(cbind, preclist, "County" = countylist, SIMPLIFY=FALSE)
preclist = mapply(cbind, preclist, "FIPS" = fips, SIMPLIFY=FALSE)

head(preclist[[3]])


# load census block geometry
blocksCO <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="blocksCO")

blocksCO = blocksCO[,c(2,5:6)]
blocksCO$FIPS = paste0("08", blocksCO$COUNTYFP10)
blocksCO = blocksCO[blocksCO$FIPS %in% site_co$FIPS, ]
head(blocksCO)


# Project 
# project precincts and blocks # colorado pcs
precprj = lapply(preclist, function(x) x %>% st_transform(6427))
# lapply(precprj, function(x) x %>% st_crs()) # check


# prj blocks
blocksprj <-  blocksCO %>% st_transform(6427)
blocksprj %>% st_crs()


# Calculate area -- units are meters sq
precprj = lapply(precprj, function(x) within(x, PrecFull_area_m2 <- st_area(x)))


blocksprj$BlockFull_area_m2 = st_area(blocksprj)
head(blocksprj)


## Combine all the precinct data
precAll = do.call("rbind", precprj)


## Intersect two shps
intr = st_intersection(blocksprj, precAll)


# question: how much of the precinct is in each block? 
intr$Intrsct_area = st_area(intr)
head(intr)

# if the intersecting area is 100% of the original block area, then 100% of that block is within the precinct, 
# but we need to allocate data from the precincts to the blocks. 
# so what percent of the intersecting area is the original precinct size?
intr$prc_Intrsct_area = intr$Intrsct_area/intr$PrecFull_area_m2



# export the intersect shp here so that it can be used for the VBM rates conversion as well
setwd("C:/Users/lauradal/Box/CCEP Files/Siting Tool/Colorado Siting Tool/data/")


#### NOTE, YOU CAN JUST LOAD THIS CONVERSION FILE HERE AND SKIP THE PRECEDING STEPS--THE INTERSECT TAKES A WHILE ####
# Export reduced shapefiles here:
write_sf(intr, "blocks_prec_conversion_CO.shp")



### multiply proportion by registered voters
# first join reg voters
intrReg = merge(intr, reg[,c(2, 3, 6)], by=c("PRECINCT", "County"), all=TRUE, duplicateGeoms=T)

dim(intrReg); dim(intr); dim(reg)

# multiply to get proportional registration
intrReg$propReg = intrReg$prc_Intrsct_area * intrReg$avg.Reg

# summarize by block
blockReg =
  intrReg %>%
  dplyr::group_by(GEOID10, NAME10, County, FIPS) %>%
  dplyr::summarize(regBlockTot = sum(propReg, na.rm=T))

blockReg$regBlockTotNum = as.numeric(blockReg$regBlockTot)
head(blockReg)

class(blockReg)
head(subset(blockReg, regBlockTotNum > 100))


##### Convert to Tract #####
## Create Tract ID
blockReg$GEOID = substr(blockReg$GEOID10, 1, 11)  # extract the first digit of the block id


### Sum records by block group to get the voter totals per block group
tractReg =
  blockReg %>%
  dplyr::group_by(GEOID) %>%   
  dplyr::summarize(reg = sum(regBlockTotNum, na.rm = T)) %>%
  as.data.frame()
tractReg = tractReg[,c('GEOID', 'reg')]
head(tractReg); dim(tractReg)
#




##### CAlculate the Eligible non reg voter pop #####
### Merge CVAP with the averaged tract registration file in order to calculate the number of people who are eligible to vote but are not registered
regCVAP <- full_join(tractReg, cvap[,c(1, 7:10)])

head(as.data.frame(regCVAP))
dim(regCVAP)

### calculate % of the eligible population that is eligible and non-registered 
regCVAP$Tot_EligNonReg_prc  <- (regCVAP$CVAP_EST - regCVAP$reg)/regCVAP$CVAP_EST  # CVAP Total - Total Registered (2014-2016 average) divided by CVAP total

# where cvap is zero, change the infinity (from the divide by zero) to NA
regCVAP$Tot_EligNonReg_prc <- ifelse(regCVAP$CVAP_EST==0, NA, regCVAP$Tot_EligNonReg_prc)


# negative values recode to NA
# but first flag as unreliable
regCVAP$TotElig_flag <- 0

regCVAP$TotElig_flag[regCVAP$Tot_EligNonReg_prc < 0] <- 1 

### Calculate sampling error for CVAP : CV calculation (coefficient of variation). We don't have MOE for the numerator, just calculate the standard CV
# CV= [(MOE/1.645)/ESTIMATE] * 100%
regCVAP$CV_Tot <- ((regCVAP$CVAP_MOE/1.645)/regCVAP$CVAP_EST)*100

# if the CV is over 40%, flag as unreliable
regCVAP$TotElig_flag[regCVAP$CV_Tot > 40] <- 1 

### Join the incarcerated & noninstitutionalized population to the CVAP data
regCVAP <- full_join(regCVAP, instPop)
dim(regCVAP)

regCVAP <- full_join(regCVAP, totNonInstPop)

head(regCVAP)
dim(regCVAP)

#### Calculate the percent of the tract CVAP that is the incarcerated adult population 
regCVAP$incarcPop_prc <- regCVAP$Incarc_Adults/regCVAP$CVAP_EST


### Create a 'final' column, where the % eligible is used EXCEPT if the value is negative or the CV is over 40% and the incarcerated population is > 25%
regCVAP$Tot_EligNonReg_prc_FINAL <- ifelse(regCVAP$incarcPop_prc > 0.25, 
                                           NA, regCVAP$Tot_EligNonReg_prc)

summary(regCVAP$Tot_EligNonReg_prc_FINAL)

regCVAP$Tot_EligNonReg_prc_FINAL <- ifelse(regCVAP$Tot_EligNonReg_prc < 0, 0, regCVAP$Tot_EligNonReg_prc)


# Now where the incarcerated population is greater than 25%, use the bg estimate for non institutionalized populations (as a replacement for cvap)
# we have no estimate for latino or asian, so those data will have to be reomved.
# if incarcerated pop is over 25%, calculate a new eligible non-registered percentage, otherwise use the same final prc
regCVAP$Tot_EligNonReg_prc_FINAL <- ifelse(regCVAP$incarcPop_prc > 0.25, (regCVAP$tract_TotNonInstPop - regCVAP$avgReg)/regCVAP$tract_TotNonInstPop,
                                           regCVAP$Tot_EligNonReg_prc_FINAL)

# flag the unreliable estimate here
regCVAP$TotElig_flag[regCVAP$Tot_EligNonReg_prc_FINAL < 0] <- 1
regCVAP$Tot_EligNonReg_prc_FINAL[regCVAP$Tot_EligNonReg_prc_FINAL < 0] <- 0

# if the estimate is NA or the CV is NA or INF, flag as unreliable
regCVAP$TotElig_flag[is.na(regCVAP$Tot_EligNonReg_prc_FINAL) | is.na(regCVAP$CV_Tot) | regCVAP$CV_Tot=="Inf"] <- 1
regCVAP$Tot_EligNonReg_prc_FINAL[is.na(regCVAP$Tot_EligNonReg_prc_FINAL)] <- 0 # the model needs values, can't have NAs. Convert NAs to zero and make sure reliability flag is on it


regCVAP = as.data.frame(regCVAP)
head(regCVAP)
summary(regCVAP)

#### Export finished tract data files to output folder ###
outputRoot = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output/"

write.csv(regCVAP, paste0(outputRoot, "Elig_NonReg_Pop_TractsCO.csv"), row.names = FALSE)

# one for the visualization folder
write.csv(regCVAP, paste0(outputRoot, "visualize/Elig_NonReg_Pop_TractsCO.csv"), row.names = FALSE)

#


