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

############# SET UP DATA ############# 
root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"

# the goal is to merge everything to blocks


############# COLORADO #########

# load data

# ACS
dat = read.csv(paste0(root, "data/output/ACS_Indicators_TractsCO.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character", "FIPS"="character"))

# create reliability flag
dat$nonEngProf_flag =ifelse(dat$LEP.CV > 40 | dat$LEP.CV=="Inf" | is.na(dat$LEP.CV) , 1, 0)
dat$NoCar_flag =ifelse(dat$NoCar.CV > 40 | dat$NoCar.CV=="Inf" | is.na(dat$NoCar.CV) ,1, 0)
dat$disab_flag =ifelse(dat$disab.CV > 40 | dat$disab.CV=="Inf" | is.na(dat$disab.CV) ,1, 0)
dat$pov_flag =ifelse(dat$BelowPoverty.CV > 40 | dat$BelowPoverty.CV=="Inf" | is.na(dat$BelowPoverty.CV) ,1, 0)
dat$youth_flag =ifelse(dat$youth.CV > 40 | dat$youth.CV=="Inf" | is.na(dat$youth.CV) ,1, 0)
dat$AsianNHL_flag =ifelse(dat$AsianNHL.CV > 40 | dat$AsianNHL.CV=="Inf" | is.na(dat$AsianNHL.CV) ,1, 0)
dat$BlackNHL_flag =ifelse(dat$BlackNHL.CV > 40 | dat$BlackNHL.CV=="Inf" | is.na(dat$BlackNHL.CV) ,1, 0)
dat$Latino_flag =ifelse(dat$Latino.CV > 40 | dat$Latino.CV=="Inf" | is.na(dat$Latino.CV) ,1, 0)
dat$NatAmNHL_flag =ifelse(dat$NatAmNHL.CV > 40 | dat$NatAmNHL.CV=="Inf" | is.na(dat$NatAmNHL.CV) ,1, 0)
dat$WhiteNHL_flag =ifelse(dat$WhiteNHL.CV > 40 | dat$WhiteNHL.CV=="Inf" | is.na(dat$WhiteNHL.CV) ,1, 0)
dat$cvap_flag =ifelse(dat$cvapDens.CV > 40 | dat$cvapDens.CV=="Inf" | is.na(dat$cvapDens.CV) ,1, 0)
head(dat)


# grab only percentages and the flags

drops = c("LEP.CV" , "NoCar.CV", "disab.CV", "BelowPoverty.CV", "youth.CV", "AsianNHL.CV", "BlackNHL.CV", 
          "Latino.CV", "NatAmNHL.CV", "WhiteNHL.CV", "cvapDens.CV")

dat = dat[, !(names(dat) %in% drops)]
head(dat)

# job
job = read.csv(paste0(root, "data/output/JobShare_Block_blocksCO.csv"), stringsAsFactors = FALSE, colClasses = c("w_geocode"="character", "w_FIPS"="character"))
colnames(job)[1:2] <- c("GEOID10", "FIPS")
job = job[,c(1,2,5)]
head(job)

# pop dens
pop = read.csv(paste0(root, "data/output/PopDensity_Block_blocksCO.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID10"="character", "TRACTCE10"="character", 
                                                                                                                   "COUNTYFP10"="character"))
pop = pop[,c(5, 2, 19, 20, 22, 23)]
colnames(pop)[2:3] <- c("FIPS", "pop2010")
pop$FIPS = paste0("08", pop$FIPS)
head(pop)


# elig
elig = read.csv(paste0(root, "data/output/Elig_NonReg_Pop_TractsCO.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID"="character", "FIPS"="character"))
elig = elig[,c(1, 3, 6, 15, 8)]
colnames(elig)[5] <- "ElNonReg_flag"
head(elig)
summary(elig)


# poll ## THIS DATA DOESN'T EXIST YET, WE JUST RECEIVED CO'S VOTER DATA YESTERDAY
# poll = read.csv(paste0(root, "data/output/PollShare_BlocksCO.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID10"="character", "FIPS"="character"))
# colnames(poll)[1] <-"GEOID10"
# head(poll)
# summary(poll)



# # vbm rate  ## THIS DATA DOESN'T EXIST YET, WE JUST RECEIVED CO'S VOTER DATA YESTERDAY
# vbm = read.csv(paste0(root, "data/output/VBM_Use_Rate_BlocksCO.csv"), stringsAsFactors = FALSE, colClasses = c("GEOID10"="character", "FIPS"="character"))
# colnames(vbm)[1] <-"GEOID10"
# head(vbm)
# summary(vbm)



# merge block layers
blockdat = list(job, pop) %>% reduce(full_join) # poll, vbm   <<- these should be added in once the data exists

# make a tract id
blockdat$GEOID = substr(blockdat$GEOID10, 1, 11)

head(blockdat)

# join tract-based data
tractdat = full_join(dat, elig)

dat = full_join(tractdat, blockdat)
head(dat)

table(dat$FIPS)
summary(dat)

# check on NAs
check = subset(dat, is.na(Latino.prc))
table(check$FIPS) 
summary(check)
head(check)

## remove NA rows that aren't real blocks/tracts
dim(dat)
dat = dat[!is.na(dat$Latino.prc) & !is.na(dat$NoCar.prc) & !is.na(dat$NAME) , ]
dim(dat)
summary(dat)


## investigate the NA blocks from the job
naz = subset(dat, is.na(TotVBM))
summary(naz)
head(naz)


# change NAs to zero where the blocks don't have data--can't have missing informatino for the model
dat$jobShare[is.na(dat$jobShare)] <- 0

### uncomment and run these lines if necessary once the voter data is ready
# dat$pollShare[is.na(dat$pollShare)] <- 0
# dat$TotVBM[is.na(dat$TotVBM)] <- 0
# dat$AsnVBM[is.na(dat$AsnVBM)] <- 0
# dat$LatVBM[is.na(dat$LatVBM)] <- 0
# dat$YouthVBM[is.na(dat$YouthVBM)] <- 0

summary(dat)


##### Standardize the variables #####

# rescale from 0 to 1

# ACS Variables
dat$prc.latino.std = percent_rank(dat$Latino.prc)
dat$dens.cvap.std = percent_rank(dat$cvapDens)
dat$prc.youth.std = percent_rank(dat$youth.prc)
dat$prc.nonEngProf.std = percent_rank(dat$LEP.prc)
dat$prc.pov.std = percent_rank(dat$BelowPoverty.prc)
dat$prc.disabled.std = percent_rank(dat$disab.prc)
dat$prc.NoCarAccess.std = percent_rank(dat$NoCar.prc) # note this is the % of people who do NOT have access to a vehicle

# census variables
dat$dens.work.std = percent_rank(dat$jobShare)
dat$popDens.std = percent_rank(dat$popDensKM2)

# voting variables
# # VBM rates need to be inverted, because we want to site VCs and DBs where there are not VBM voters
# dat$rate.vbm.std = 1 - percent_rank(dat$TotVBM)
# dat$rate.hisvbm.std = 1 - percent_rank(dat$AsnVBM)
# dat$rate.aisvbm.std = 1 - percent_rank(dat$LatVBM)
# dat$rate.yousvbm.std = 1 - percent_rank(dat$YouthVBM)

dat$prc.ElNonReg.std = percent_rank(dat$Tot_EligNonReg_prc_FINAL)
# dat$dens.poll.std = percent_rank(dat$pollShare)


# Grab only variables used by the model and the reliability flags
head(dat)

finalcols = c("GEOID10", "GEOID", "NAME" , "FIPS", "popACS", "State", "pop2010", "prc.latino.std" ,   
"dens.cvap.std","prc.youth.std","prc.nonEngProf.std" , "prc.pov.std","prc.disabled.std","prc.NoCarAccess.std", "dens.work.std","popDens.std",   
"rate.vbm.std","rate.hisvbm.std","rate.aisvbm.std","rate.yousvbm.std","prc.ElNonReg.std","dens.poll.std","nonEngProf_flag","NoCar_flag",    
"disab_flag","pov_flag","youth_flag","Latino_flag","cvap_flag", "ElNonReg_flag")

#### NOTE THIS IS STILL MISSING VBM AND POLLING PLACE SHARE VARIABLES ####
dat = dat[, (names(dat) %in% finalcols)]
head(dat)

#### Export the standardized model data ####
outputRoot = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output/"

write.csv(dat, paste0(outputRoot, "model data/indicators_Stand_Final_CO.csv"), row.names = FALSE)

#### ALSO NEED TO INCLUDE AND STANDARDIZE THE TRANSIT SCORE--BUT THAT WILL BE CALCULATED BY CONTRACTOR


############# MODIFY THIS SCRIPT TO COMPLETE #######

# all this code below was developed by DK. I've made some modifications where possible (e.g. the first chunk), but the transit scores and the suitable sites are 
# needed to complete this script as it was done in the previous version. HOWEVER, if the new contractors go for different technology/methodology, then it may not be
# necessary to complete this script exactly as-is. I've left it here for reference.

###### Generate grid of test points (1 mile apart) that are within county boundary w/ buffer of 0.5 miles #####


# Use county data on centroids for each census block to find approximate county geographic centroid
# load blocks 
poly.bg.df = read.dbf("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial/blocksCO.dbf", as.is = TRUE)

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

# 
# 
# ########## Generate data inputs for model ###########
# #### this is where you read in the suitable sites generated by the 1/2 mile grid points, taking into account population, road density, points of interest
# #Check if points in a census block polygon
# tmp.test.points = test.points
# coordinates(tmp.test.points) <- ~lon+lat
# 
# test_poly.bg.df= read.dbf("C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/decennial/blocksCO.dbf", as.is = TRUE)
# 
# test_poly.bg.df$geocode.t = substr(test_poly.bg.df$GEOID10, 1, 11) # create tract ID
# 
# proj4string(tmp.test.points) <- proj4string(sacramento_poly_bg)  
# test.points <- cbind(test.points, over(tmp.test.points, sacramento_poly_bg))
# rm(tmp.test.points)
# #
# 
# 
# #Remove points that didn't match to a census block polygon (these will be points right on border)
# #test.points = test.points[!is.na(test.points$GEOID10),]
# 
# #Fix geocodes to match other data
# #Remove leading zero from block code
# test.points$GEOID10 = as.character(test.points$GEOID10)
# test.points$geocode.b = substr(test.points$GEOID10,2,nchar(test.points$GEOID10))
# 
# #Remove last 3 digits to get block group
# test.points$geocode.bg = substr(test.points$GEOID10,2,nchar(test.points$GEOID10)-3)
# 
# #Remove last 4 digits to get tract
# test.points$geocode.t = substr(test.points$GEOID10,2,nchar(test.points$GEOID10)-4)
# 
# 
# #test.points = subset(test.points, selec = c("lon","lat","","",""))
# 
# 
# #Find 3 nearest neighboring census block centroids
# CBG.tree <- createTree(cbind(poly.bg.df$INTPTLON10,poly.bg.df$INTPTLAT10))
# CBG.nei <- knnLookup(CBG.tree,  newx=test.points$lon,newy=test.points$lat, k=3)
# #Find distance to nearest neighbors
# dist.CBG.nei = CBG.nei
# for(i in 1:dim(CBG.nei)[1]){
#   for(j in 1:dim(CBG.nei)[2]){
#     tmp = CBG.nei[i,j]
#     dist.CBG.nei[i,j] = distCosine(test.points[i,c("lon","lat")],c(poly.bg.df$INTPTLON10[tmp],poly.bg.df$INTPTLAT10[tmp]))*0.000621371
#   }
# }
# 
# test.points$geocode.b1 = poly.bg.df$geocode.b[CBG.nei[,1]]
# test.points$geocode.b2 = poly.bg.df$geocode.b[CBG.nei[,2]]
# test.points$geocode.b3 = poly.bg.df$geocode.b[CBG.nei[,3]]
# 
# 
# #Nearest 3 block groups (may not be unique) - remove block code 
# test.points$geocode.bg1 = substr(test.points$geocode.b1,1,nchar(test.points$geocode.b1)-3)
# test.points$geocode.bg2 = substr(test.points$geocode.b2,1,nchar(test.points$geocode.b2)-3)
# test.points$geocode.bg3 = substr(test.points$geocode.b3,1,nchar(test.points$geocode.b3)-3)
# 
# 
# 
# 
# #Find distance to 3 nearest transit stop
# tran.tree <- createTree(cbind(transit.dat.std$stop_long, transit.dat.std$stop_lat))
# tran.nei <- knnLookup(tran.tree,  newx=test.points$lon,newy=test.points$lat, k=3)
# #Find distance to nearest neighbors
# dist.tran.nei = as.data.frame(tran.nei)
# for(i in 1:dim(tran.nei)[1]){
#   for(j in 1:dim(tran.nei)[2]){
#     tmp = tran.nei[i,j]
#     dist.tran.nei[i,j] = distCosine(test.points[i,c("lon","lat")],c(transit.dat.std$stop_long[tmp],transit.dat.std$stop_lat[tmp]))*0.000621371
#   }
# }
# 
# names(dist.tran.nei) = c("transit.dist.1","transit.dist.2","transit.dist.3")
# 
# test.points = cbind(test.points,dist.tran.nei)
# 
# #Score of transit neighbors
# test.points$transit.score1 = NA
# test.points$transit.score2 = NA
# test.points$transit.score3 = NA
# 
# for(i in 1:dim(tran.nei)[1]){
#   test.points$transit.score1[i] = transit.dat.std$score[tran.nei[i,1]]
#   test.points$transit.score2[i] = transit.dat.std$score[tran.nei[i,2]]
#   test.points$transit.score3[i] = transit.dat.std$score[tran.nei[i,3]]
# }
# 
# #Generate transit variable
# test.points$transit.score.std = NA
# 
# for(i in 1:dim(test.points)[1]){
#   
#   if(min(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i]) > 0.5) test.points$transit.score.std[i] = 0
#   else{
#     tmp = which(c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i]) <= 0.5)
#     
#     if(length(tmp) == 1) test.points$transit.score.std[i] =  0.5*c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i])[tmp]
#     if(length(tmp) == 2) test.points$transit.score.std[i] =  sum(0.75*c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i])[tmp])
#     if(length(tmp) == 3) test.points$transit.score.std[i] =  sum(c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i])[tmp])
#   }
# }


