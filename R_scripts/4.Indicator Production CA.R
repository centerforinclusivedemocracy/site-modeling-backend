# Combine indicators to make one single data input for the model
library(data.table)
library(dplyr)
library(tidyverse)
library(rgeos)
library(rgdal) # load mapping libraries
library(raster)
library(sp)
library(sf)
library(lwgeom)
library(scales)
library(foreign)
library(geosphere)
library(purrr)

############# SET UP DATA ############# 
# root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
# genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"
root <- "/Users/lauradaly/Documents/GreenInfo/Contract Work/Siting Tool/"

# the goal is to merge everything to blocks for the block score/weighted average


############# CALIFORNIA #########
### Start with CA, because all data is present/completed

# ACS # note these were updated with 2018 data
dat = read.csv(paste0(root, "data/output/ACS_Indicators_TractsCA.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character", "FIPS"="character"))

# create reliability flag ### REMOVE, FLAG ADED IN 1.ACS DATA PREP ALL STATES.R
# dat$nonEngProf_flag =ifelse(dat$LEP.CV > 40 | dat$LEP.CV=="Inf" | is.na(dat$LEP.CV) , 1, 0)
# dat$CarAccess_flag =ifelse(dat$CarAccess.CV > 40 | dat$CarAccess.CV=="Inf" | is.na(dat$CarAccess.CV) ,1, 0)
# dat$disab_flag =ifelse(dat$disab.CV > 40 | dat$disab.CV=="Inf" | is.na(dat$disab.CV) ,1, 0)
# dat$pov_flag =ifelse(dat$BelowPoverty.CV > 40 | dat$BelowPoverty.CV=="Inf" | is.na(dat$BelowPoverty.CV) ,1, 0)
# dat$youth_flag =ifelse(dat$youth.CV > 40 | dat$youth.CV=="Inf" | is.na(dat$youth.CV) ,1, 0)
# dat$AsianNHL_flag =ifelse(dat$AsianNHL.CV > 40 | dat$AsianNHL.CV=="Inf" | is.na(dat$AsianNHL.CV) ,1, 0)
# dat$BlackNHL_flag =ifelse(dat$BlackNHL.CV > 40 | dat$BlackNHL.CV=="Inf" | is.na(dat$BlackNHL.CV) ,1, 0)
# dat$Latino_flag =ifelse(dat$Latino.CV > 40 | dat$Latino.CV=="Inf" | is.na(dat$Latino.CV) ,1, 0)
# dat$NatAmNHL_flag =ifelse(dat$NatAmNHL.CV > 40 | dat$NatAmNHL.CV=="Inf" | is.na(dat$NatAmNHL.CV) ,1, 0)
# dat$WhiteNHL_flag =ifelse(dat$WhiteNHL.CV > 40 | dat$WhiteNHL.CV=="Inf" | is.na(dat$WhiteNHL.CV) ,1, 0)
# dat$cvap_flag =ifelse(dat$cvapDens.CV > 40 | dat$cvapDens.CV=="Inf" | is.na(dat$cvapDens.CV) ,1, 0)
# head(dat)

# # create list of cols to drop (now that we have the flag column we don't need the CVS)
# drops = c("LEP.CV" , "CarAccess.CV", "disab.CV", "BelowPoverty.CV", "youth.CV", "AsianNHL.CV", "BlackNHL.CV", 
#            "Latino.CV", "NatAmNHL.CV", "WhiteNHL.CV", "cvapDens.CV")
# 
# dat = dat[, !(names(dat) %in% drops)]
head(dat)

# job
job = read.csv(paste0(root, "data/output/JobShare_Block_blocksCA.csv"), stringsAsFactors = FALSE, colClasses = c("w_geocode"="character", "w_FIPS"="character"))
colnames(job)[1:2] <- c("GEOID10", "FIPS")
job = job[,c(1,2,5)]
head(job)

# pop dens
pop = read.csv(paste0(root, "data/output/PopDensity_Block_blocksCA.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID10"="character", "TRACTCE10"="character", 
                                                                                                                   "COUNTYFP10"="character"))
pop = pop[,c(5, 2, 20, 21,23, 24)]
colnames(pop)[2:3] <- c("FIPS", "pop2010")
pop$FIPS = paste0("06", pop$FIPS)
head(pop)


# elig # This was also updated with 2018 DATA
elig = read.csv(paste0(root, "data/output/Elig_NonReg_Pop_TractsCA.csv"), stringsAsFactors = FALSE, 
                colClasses = c("GEOID"="character", "FIPS"="character"))
colnames(elig)[4] <- "ElNonReg_flag"
head(elig)
summary(elig)


# poll  # This was updated with 2018 data
poll = read.csv(paste0(root, "data/output/PollShare_BlocksCA.csv"), stringsAsFactors = FALSE, colClasses = c("BLOCK_KEY"="character", "FIPS"="character"))
colnames(poll)[1] <-"GEOID10"
head(poll)
summary(poll)

# vbm rate # This was updated with 2018 data
vbm = read.csv(paste0(root, "data/output/VBM_Use_Rate_BlocksCA.csv"), stringsAsFactors = FALSE, colClasses = c("BLOCK_KEY"="character", "FIPS"="character"))
colnames(vbm)[1] <-"GEOID10"
head(vbm)
summary(vbm)

# merge block layers
blockdat = list(job, pop, poll, vbm) %>% reduce(full_join)

# make a tract id
blockdat$GEOID = substr(blockdat$GEOID10, 1, 11)

head(blockdat)

# join tract-based data
tractdat = full_join(dat, elig)

# join block data to tract data
dat = full_join(tractdat, blockdat)
head(dat)

table(dat$FIPS)
summary(dat)

# check on NAs
check = subset(dat, is.na(Latino.prc))
table(check$FIPS) # most NAs have no fips code attached--likely legacy tract ids merged in from 2010 blocks or SWDB conversion files
summary(check) # note the tot pop (pop2010) is pretty low, prob na reason

## remove NA rows that aren't real blocks/tracts
dat = dat[!is.na(dat$Latino.prc) & !is.na(dat$CarAccess.prc) & !is.na(dat$NAME) & !is.na(dat$pop2010), ]

summary(dat)


## investigate the NA blocks from the job
naz = subset(dat, is.na(jobShare))
summary(naz)
head(naz)


# change NAs to zero where the blocks don't have data--can't have missing informatino for the model
dat$jobShare[is.na(dat$jobShare)] <- 0
dat$pollShare[is.na(dat$pollShare)] <- 0
dat$TotVBM[is.na(dat$TotVBM)] <- 0
dat$AsnVBM[is.na(dat$AsnVBM)] <- 0
dat$LatVBM[is.na(dat$LatVBM)] <- 0
dat$YouthVBM[is.na(dat$YouthVBM)] <- 0

summary(dat)


##### Standardize the variables #####
# need to be standardized BY/within county

# split into list by county
dat_list <- split(dat, dat$FIPS, drop = FALSE)
head(dat_list[[11]])

# rescale from 0 to 1
# ACS Variables
dat_list <- lapply(dat_list, function(x) within(x, prc.latino.std <- (percent_rank(x$Latino.prc))))
dat_list <- lapply(dat_list, function(x) within(x, dens.cvap.std <- (percent_rank(x$cvapDens))))
dat_list <- lapply(dat_list, function(x) within(x, prc.youth.std <- (percent_rank(x$youth.prc))))
dat_list <- lapply(dat_list, function(x) within(x, prc.nonEngProf.std <- (percent_rank(x$LEP.prc))))
dat_list <- lapply(dat_list, function(x) within(x, prc.pov.std <- (percent_rank(x$BelowPoverty.prc))))
dat_list <- lapply(dat_list, function(x) within(x, prc.disabled.std <- (percent_rank(x$disab.prc))))
dat_list <- lapply(dat_list, function(x) within(x, prc.CarAccess.std <- 1 - (percent_rank(x$CarAccess.prc)))) # note this is the % of people who DO have access to a vehicle, should be inverted

# dat$prc.latino.std = percent_rank(dat$Latino.prc)
# dat$dens.cvap.std = percent_rank(dat$cvapDens)
# dat$prc.youth.std = percent_rank(dat$youth.prc)
# dat$prc.nonEngProf.std = percent_rank(dat$LEP.prc)
# dat$prc.pov.std = percent_rank(dat$BelowPoverty.prc)
# dat$prc.disabled.std = percent_rank(dat$disab.prc)
# dat$prc.CarAccess.std = 1 - percent_rank(dat$CarAccess.prc) # note this is the % of people who DO have access to a vehicle, should be inverted

# census variables
dat_list <- lapply(dat_list, function(x) within(x, dens.work.std <- (percent_rank(x$jobShare))))
dat_list <- lapply(dat_list, function(x) within(x, popDens.std <- (percent_rank(x$popDensKM2))))

# dat$dens.work.std = percent_rank(dat$jobShare)
# dat$popDens.std = percent_rank(dat$popDensKM2)

# voting variables
# VBM rates need to be inverted, because we want to site VCs and DBs where there are not VBM voters
dat_list <- lapply(dat_list, function(x) within(x, rate.vbm.std <- 1 - (percent_rank(x$TotVBM))))
dat_list <- lapply(dat_list, function(x) within(x, rate.hisvbm.std <- 1 - (percent_rank(x$LatVBM))))
dat_list <- lapply(dat_list, function(x) within(x, rate.aisvbm.std <- 1 - (percent_rank(x$AsnVBM))))
dat_list <- lapply(dat_list, function(x) within(x, rate.yousvbm.std <- 1 - (percent_rank(x$YouthVBM))))

dat_list <- lapply(dat_list, function(x) within(x, prc.ElNonReg.std <- 1 - (percent_rank(x$Tot_EligNonReg_prc_FINAL))))
dat_list <- lapply(dat_list, function(x) within(x, dens.poll.std <- 1 - (percent_rank(x$pollShare))))

# dat$rate.vbm.std = 1 - percent_rank(dat$TotVBM)
# dat$rate.hisvbm.std = 1 - percent_rank(dat$LatVBM)
# dat$rate.aisvbm.std = 1 - percent_rank(dat$AsnVBM)
# dat$rate.yousvbm.std = 1 - percent_rank(dat$YouthVBM)
# 
# dat$prc.ElNonReg.std = percent_rank(dat$Tot_EligNonReg_prc_FINAL)
# dat$dens.poll.std = percent_rank(dat$pollShare)

# collapse list
dat <- do.call("rbind", dat_list)
table(dat$FIPS)
head(dat)


# Grab only variables used by the model (standardized) and the reliability flags
dat <- 
dat %>% dplyr::select(GEOID10, GEOID, NAME, FIPS, popACS, State, pop2010, area_km2, popPrcCounty, 
                      prc.latino.std, dens.cvap.std , prc.youth.std,  prc.nonEngProf.std, prc.pov.std,
                      prc.disabled.std, prc.CarAccess.std, dens.work.std,  popDens.std, rate.vbm.std,
                      rate.hisvbm.std, rate.aisvbm.std, rate.yousvbm.std, prc.ElNonReg.std, dens.poll.std,
                      LEP_flag, CarAccess_flag, disab_flag, BelowPoverty_flag, youth_flag, Latino_flag, cvapDens_flag, ElNonReg_flag)

head(dat)
# finalNames = names(dat)

#### Export the standardized model data ####
# outputRoot = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output/"
outputRoot = "/Users/lauradaly/Documents/GreenInfo/Contract Work/Siting Tool/data/output/"

write.csv(dat, paste0(outputRoot, "model data/indicators_Stand_Final_CA.csv"), row.names = FALSE)

#### ALSO NEED TO INCLUDE AND STANDARDIZE THE TRANSIT SCORE--BUT THAT WILL BE CALCULATED BY CONTRACTOR

## test weighted average (doesn't include transit score--maybe I just pass this sample script on to Jayita?)
head(dat)

# center score (weighted average)
dat$vc_score = 
# First tier: Asian American vote-by-mail rate, vehicle accessibility, Latino population, polling place voter, poverty, youth population. 
# These 6 variables should compose 30% of the total score.
((dat$rate.aisvbm.std + dat$prc.CarAccess.std + dat$prc.latino.std + dat$dens.poll.std + dat$prc.pov.std + dat$prc.youth.std)/6) * 0.3 +


# Weighted tier: Latino vote-by-mail rate, youth vote-by-mail rate, county workers, disabled population, limited English proficient population, 
# eligible non-registered voter population. 
# These 6 variables should compose 40% of the total score. # NOTE I MADE THIS 45% TO ADD UP TO 100%
((dat$rate.hisvbm.std + dat$rate.yousvbm.std + dat$dens.work.std + dat$prc.disabled.std + dat$prc.nonEngProf.std + dat$prc.ElNonReg.std)/6 * 0.45) +

# Highest-weighted tier: Total vote-by-mail rate, transit score, population density. These 3 variables should compose 25% of the total score.
((dat$rate.vbm.std + dat$popDens.std)/2 * 0.25)  # MISSING TRANSIT SCORE - WHEN INCLUDED DIVIDE BY 3

head(dat)

# spot check distribution
hist(dat[dat$FIPS == "06037",]$vc_score)
hist(dat[dat$FIPS == "06085",]$vc_score)
hist(dat[dat$FIPS == "06067",]$vc_score)


# drop box score (weighted average)
dat$db_score = 
  # Lowest weighted tier: Asian American vote-by-mail rate, vehicle accessibility, Latino population, polling place voter, poverty, youth population, eligible non-registered voter population. 
  # These 7 variables should compose 30% of the total score.
  ((dat$rate.aisvbm.std + dat$prc.CarAccess.std + dat$prc.latino.std + dat$dens.poll.std + dat$prc.pov.std + dat$prc.youth.std + dat$prc.ElNonReg.std)/7) * 0.3 +
  
  # Middle weighted tier: Latino vote-by-mail rate, youth vote-by-mail rate, county workers, disabled population, limited English proficient population. 
  # These 5 variables should compose 40% of the total score. # NOTE I MADE THIS 45% TO ADD UP TO 100%
  ((dat$rate.hisvbm.std + dat$rate.yousvbm.std + dat$dens.work.std + dat$prc.disabled.std + dat$prc.nonEngProf.std)/5 * 0.45) +
  
  # Highest weighted tier: Total vote-by-mail rate, transit score, population density. 
  # These 3 variable should compose 25% of the total score
  ((dat$rate.vbm.std + dat$popDens.std)/2 * 0.25)  # MISSING TRANSIT SCORE - WHEN INCLUDED DIVIDE BY 3

head(dat)

hist(dat[dat$FIPS == "06039",]$db_score)
hist(dat[dat$FIPS == "06067",]$db_score)


############# MODIFY THIS SCRIPT TO COMPLETE #######

# all this code below was developed by DK. I've made some modifications where possible (e.g. the first chunk), but the transit scores and the suitable sites are 
# needed to complete this script as it was done in the previous version. HOWEVER, if the new contractors go for different technology/methodology, then it may not be
# necessary to complete this script exactly as-is. I've left it here for reference.

###### Generate grid of test points (1 mile apart) that are within county boundary w/ buffer of 0.5 miles #####


# Use county data on centroids for each census block to find approximate county geographic centroid
# load blocks 
poly.bg.df = read.dbf(paste0(root, "data/decennial/blocksCA.dbf"), as.is = TRUE)

poly.bg.df$geocode.t = substr(poly.bg.df$GEOID10, 1, 11)
poly.bg.df$INTPTLAT10 = as.numeric(poly.bg.df$INTPTLAT10)
poly.bg.df$INTPTLON10 = as.numeric(poly.bg.df$INTPTLON10)

#S coord
s.coord = min(poly.bg.df$INTPTLAT10)
#N coord
n.coord = max(poly.bg.df$INTPTLAT10)
#E coord
e.coord = min(poly.bg.df$INTPTLON10)
#W coord
w.coord = max(poly.bg.df$INTPTLON10)

#Center point will be center of grid w/ points 1 mile apart
center.y = mean(c(s.coord,n.coord))
center.x = mean(c(e.coord,w.coord))

y.dist = floor(distCosine(c(center.x, s.coord),c(center.x, n.coord))*0.000621372) # 0.000310686 is the number DataKind used, but that seems to generate points that are 2 miles apart instead of 1. Revert if there's a reason for it, otherwise...stick with this one 
x.dist = floor(distCosine(c(e.coord, center.y),c(w.coord, center.y))*0.000621372)

y.seq = seq(s.coord, n.coord, length.out = y.dist)
x.seq = seq(e.coord, w.coord, length.out = x.dist)

#Generate grid of points that are one mile apart
test.points = expand.grid(lon = x.seq,lat = y.seq)
write.csv(test.points,"test.csv")

# these "suitable sites" were generated by DataKind, taking into account population, road density, points of interest.
# test.points<-read.csv("c081_suitable_site_centroids.csv") # exmaple csv for san mateo from last version



########## Generate data inputs for model ###########
#### this is where you read in the suitable sites generated by the 1/2 mile grid points, taking into account population, road density, points of interest
#Check if points in a census block polygon
tmp.test.points = test.points
coordinates(tmp.test.points) <- ~lon+lat

test_poly.bg.df= read.dbf(paste0(root, "data/decennial/blocksCA.dbf"), as.is = TRUE)

test_poly.bg.df$geocode.t = substr(test_poly.bg.df$GEOID10, 1, 11) # create tract ID

proj4string(tmp.test.points) <- proj4string(sacramento_poly_bg)  
test.points <- cbind(test.points, over(tmp.test.points, sacramento_poly_bg))
rm(tmp.test.points)
#


#Remove points that didn't match to a census block polygon (these will be points right on border)
#test.points = test.points[!is.na(test.points$GEOID10),]

#Fix geocodes to match other data
#Remove leading zero from block code
test.points$GEOID10 = as.character(test.points$GEOID10)
test.points$geocode.b = substr(test.points$GEOID10,2,nchar(test.points$GEOID10))

#Remove last 3 digits to get block group
test.points$geocode.bg = substr(test.points$GEOID10,2,nchar(test.points$GEOID10)-3)

#Remove last 4 digits to get tract
test.points$geocode.t = substr(test.points$GEOID10,2,nchar(test.points$GEOID10)-4)


#test.points = subset(test.points, selec = c("lon","lat","","",""))


#Find 3 nearest neighboring census block centroids
CBG.tree <- createTree(cbind(poly.bg.df$INTPTLON10,poly.bg.df$INTPTLAT10))
CBG.nei <- knnLookup(CBG.tree,  newx=test.points$lon,newy=test.points$lat, k=3)
#Find distance to nearest neighbors
dist.CBG.nei = CBG.nei
for(i in 1:dim(CBG.nei)[1]){
  for(j in 1:dim(CBG.nei)[2]){
    tmp = CBG.nei[i,j]
    dist.CBG.nei[i,j] = distCosine(test.points[i,c("lon","lat")],c(poly.bg.df$INTPTLON10[tmp],poly.bg.df$INTPTLAT10[tmp]))*0.000621371
  }
}

test.points$geocode.b1 = poly.bg.df$geocode.b[CBG.nei[,1]]
test.points$geocode.b2 = poly.bg.df$geocode.b[CBG.nei[,2]]
test.points$geocode.b3 = poly.bg.df$geocode.b[CBG.nei[,3]]


#Nearest 3 block groups (may not be unique) - remove block code 
test.points$geocode.bg1 = substr(test.points$geocode.b1,1,nchar(test.points$geocode.b1)-3)
test.points$geocode.bg2 = substr(test.points$geocode.b2,1,nchar(test.points$geocode.b2)-3)
test.points$geocode.bg3 = substr(test.points$geocode.b3,1,nchar(test.points$geocode.b3)-3)




#Find distance to 3 nearest transit stop
tran.tree <- createTree(cbind(transit.dat.std$stop_long, transit.dat.std$stop_lat))
tran.nei <- knnLookup(tran.tree,  newx=test.points$lon,newy=test.points$lat, k=3)
#Find distance to nearest neighbors
dist.tran.nei = as.data.frame(tran.nei)
for(i in 1:dim(tran.nei)[1]){
  for(j in 1:dim(tran.nei)[2]){
    tmp = tran.nei[i,j]
    dist.tran.nei[i,j] = distCosine(test.points[i,c("lon","lat")],c(transit.dat.std$stop_long[tmp],transit.dat.std$stop_lat[tmp]))*0.000621371
  }
}

names(dist.tran.nei) = c("transit.dist.1","transit.dist.2","transit.dist.3")

test.points = cbind(test.points,dist.tran.nei)

#Score of transit neighbors
test.points$transit.score1 = NA
test.points$transit.score2 = NA
test.points$transit.score3 = NA

for(i in 1:dim(tran.nei)[1]){
  test.points$transit.score1[i] = transit.dat.std$score[tran.nei[i,1]]
  test.points$transit.score2[i] = transit.dat.std$score[tran.nei[i,2]]
  test.points$transit.score3[i] = transit.dat.std$score[tran.nei[i,3]]
}

#Generate transit variable
test.points$transit.score.std = NA

for(i in 1:dim(test.points)[1]){
  
  if(min(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i]) > 0.5) test.points$transit.score.std[i] = 0
  else{
    tmp = which(c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i]) <= 0.5)
    
    if(length(tmp) == 1) test.points$transit.score.std[i] =  0.5*c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i])[tmp]
    if(length(tmp) == 2) test.points$transit.score.std[i] =  sum(0.75*c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i])[tmp])
    if(length(tmp) == 3) test.points$transit.score.std[i] =  sum(c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i])[tmp])
  }
}


