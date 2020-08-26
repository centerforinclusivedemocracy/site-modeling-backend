# Read in voter data - 2016 gen - for vbm rates by race/eth, age and total

library(data.table)
library(dplyr)


root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
COroot ="C:/Users/lauradal/Box/CCEP Files/Siting Tool/Colorado Siting Tool/data/"
genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"


# Read in voter file
dat = fread(paste0(COroot, "voter/CE-068_Voters_With_Ballots_List_Public_Statewide_2016_General.txt"), data.table = FALSE,  fill = TRUE) # note that the original data had a line break I needed to edit manually in notepad++

#### READ IN HERE COUNTIES INCLUDED IN THE SITING TOOL 
siteCounties = read.csv(paste0(root, "data/admin/Siting_Counties_MasterList.csv"), stringsAsFactors = FALSE)
siteCounties$FIPS = sprintf("%05d", siteCounties$FIPS)
site_co = siteCounties[siteCounties$State=="Colorado",]
site_co$COUNTY = toupper(site_co$CountyName)

# first thing, only look at counties of interst
dat = dat[dat$COUNTY %in% site_co$COUNTY, ]

head(dat)
dim(dat)
table(dat$VOTE_METHOD) # verify that this is the correct number of voters
table(dat$COUNTY)

###### THE PRECINCT DATA IS MESSY. CHECK VOTE METHOD DEFINITIONS AND TOTALS #####

# look at mesa - check
mesa = subset(dat, COUNTY=="MESA")
head(mesa)

mesaprec = preclist$Mesa
head(mesaprec)


# check garfield
garf = subset(dat, COUNTY=="GARFIELD")
head(garf)

garfprec = preclist$Garfield
head(garfprec)
