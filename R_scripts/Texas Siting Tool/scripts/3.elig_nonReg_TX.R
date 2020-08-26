# # Harris County Voter Data - Eligible Non-Registered Population
# Note that I have all the necessary data at the precinct level, but I'm using the current precinct boundaries to calculate the proportional distribution of registered voters because I'm still waiting on precinct shapefiles.
# If the 2016 precinct shapefiles come in this can be re-run, but is probably not necessary. 

library(data.table)
library(dplyr)
library(rgeos)
library(rgdal) # load mapping libraries
library(raster)
library(sp)
library(sf)
library(lwgeom)

root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
TXroot ="C:/Users/lauradal/Box/CCEP Files/Siting Tool/Texas Siting Tool/data/"
genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"

#### Prepare Data ####
gen14 = read.csv(paste0(TXroot, "voter/11-4-2014 Official Landscape Rpts/All_Voting_2014General-LD.csv"), stringsAsFactors = FALSE, colClasses = c("PCT..NUM."="character"))
gen14$ELECTION = "2014 General"


gen16 = read.csv(paste0(TXroot, "voter/All_Voting_2016General-LD.csv"), stringsAsFactors = FALSE, colClasses = c("PCT..NUM."="character"))
gen16$ELECTION = "2016 General"


#### READ IN HERE COUNTIES INCLUDED IN THE SITING TOOL 
siteCounties = read.csv(paste0(root, "data/admin/Siting_Counties_MasterList.csv"), stringsAsFactors = FALSE)
siteCounties$FIPS = sprintf("%05d", siteCounties$FIPS)
site_tx = siteCounties[siteCounties$State=="Texas",]

# read in CVAP data
cvap = fread(paste0(genRoot, "CVAP/CVAP_2013_2017/Tract.csv"), data.table = FALSE)

# create county fips 
cvap$FIPS <- substr(cvap$geoid, 8, 12)
cvap$GEOID <- substr(cvap$geoid, 8, 18)
head(cvap)

# Grab tracts in the counties of interest
cvap = cvap[cvap$FIPS %in% siteCounties$FIPS & cvap$lntitle =="Total" & cvap$GEONAME %like% ", Texas", ]
dim(cvap)



## Read in the incarcerated population data from the 2010 census (TRACTS)
instPop <- read.csv(paste0(TXroot, "institutionalized_pop/DEC_10_SF1_P42_with_ann.csv"), header = TRUE, 
                    stringsAsFactors = FALSE, skip=1,colClasses = c('Id2'='character'))

instPop <- instPop[,c(2,4,6)]
colnames(instPop) <- c("GEOID", "TotalGroupQuarters", "Incarc_Adults")

head(instPop)

### non institutionalized pop data
totNonInstPop <- read.csv(paste0(TXroot, "institutionalized_pop/ACS_17_5YR_S1810_with_ann.csv"), header = TRUE, stringsAsFactors = FALSE, skip=1, colClasses = c('Id2'='character'))
totNonInstPop <- totNonInstPop[,c(2, 4:5)]
colnames(totNonInstPop) <- c("GEOID", "tract_TotNonInstPop", "tract_TotNonInstPop.MOE")
head(totNonInstPop)


### Prepare the registration data #####
# first average the registration rate for 2014 and 2016 general elections
colnames(gen14)[2] <- "Tot.Reg.14"
colnames(gen16)[2] <- "Tot.Reg.16"
reg = full_join(gen14[,c(1:2)], gen16[,c(1,2)])
head(reg)

reg$avg.Reg = rowMeans(reg[,c(2:3)], na.rm = T)
colnames(reg)[1] <- "PRECINCT"
head(reg)




##### CAlculate the proportion of each precinct that is in each block ####
## load precinct shapefile
# note this is what was posted online, but is not necessarily the same precinct as the 2016/2014 general elections
prec <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/Texas Siting Tool/data/voter", layer="Harris_County_Voting_Precincts")
head(prec)


# load census block geometry
blocksTX <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial", layer="blocksTX")

blocksTX = blocksTX[,c(5:6)]
head(blocksTX)

# check crs of geometries
crs(prec)
crs(blocksTX)



# project precincts and blocks # TX Albers Eq Area
precprj <- prec %>% st_transform(3083) 
precprj %>% st_crs() # check


blocksprj <-  blocksTX %>% st_transform(3083)
blocksprj %>% st_crs()


# Calculate area -- units are meters sq
precprj$PrecFull_area_m2 = st_area(precprj)
blocksprj$BlockFull_area_m2 = st_area(blocksprj)
head(blocksprj)


precprj = precprj[,c('PRECINCT', 'PrecFull_area_m2')]
head(precprj)

## Intersect two shps
intr = st_intersection(blocksprj, precprj)

# question: how much of the precinct is in each block? 
intr$Intrsct_area = st_area(intr)
head(intr)

# if the intersecting area is 100% of the original block area, then 100% of that block is within the precinct, 
# but we need to allocate data from the precincts to the blocks. 
# so what percent of the intersecting area is the original precinct size?
intr$prc_Intrsct_area = intr$Intrsct_area/intr$PrecFull_area_m2


# export the intersect shp here so that it can be used for the VBM rates conversion as well
setwd("C:/Users/lauradal/Box/CCEP Files/Siting Tool/Texas Siting Tool/data/")

# Export reduced shapefiles here:
write_sf(intr, "blocks_prec_conversion_TX.shp")


### multiply proportion by registered voters
# first join reg voters
intrReg = merge(intr, reg[,c(1,4)], by="PRECINCT", all=TRUE, duplicateGeoms=T)

# multiply to get proportional registration
intrReg$propReg = intrReg$prc_Intrsct_area * intrReg$avg.Reg

# summarize by block
blockReg =
intrReg %>%
  group_by(GEOID10, NAME10) %>%
  summarize(regBlockTot = sum(propReg, na.rm=T))

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


#### Export finished tract data files to output folder ###
outputRoot = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output/"

write.csv(regCVAP, paste0(outputRoot, "Elig_NonReg_Pop_TractsTX.csv"), row.names = FALSE)

# one for the visualization folder
write.csv(regCVAP, paste0(outputRoot, "visualize/Elig_NonReg_Pop_TractsTX.csv"), row.names = FALSE)

#

