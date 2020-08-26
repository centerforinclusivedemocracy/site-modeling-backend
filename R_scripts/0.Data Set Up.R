# Set up data

library(usmap)
library(ggplot2)
library(dplyr)
library(scales)
library(data.table)

# dir
root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"


#### Create list of Counties included in the siting tool ####
# read in list of VCA counties
site_ca = read.csv(paste0(root, "California Siting Tool/data/admin/CA_VCA_Counties.csv"), stringsAsFactors = FALSE)
site_ca = site_ca[,c(1, 3, 4)]
site_ca$FIPS = sprintf("%05d", site_ca$FIPS)
head(site_ca)

# Get list of CO counties with FIPS
COCounties = c('Denver',	'Arapahoe',	'El Paso',	'Jefferson',	'Adams',	'Boulder',	'Larimer',	'Weld',	'Douglas',	'Mesa',	'Pueblo',	'Garfield',	'La Plata',	'Broomfield',	'Eagle')

# create list with fips codes
site_co = data.frame(FIPS = fips(state = "CO", county = COCounties), CountyName = COCounties, State="Colorado")
head(site_co)

# create df with AZ county
site_az = data.frame(FIPS = fips(state = "AZ", county = "Maricopa"), CountyName = "Maricopa", State = "Arizona" )

# create df with TX county
site_tx = data.frame(FIPS = fips(state = "TX", county = "Harris"), CountyName = "Harris", State="Texas" )

# combine all lists of siting counties
siteCounties = bind_rows(site_ca, site_co, site_az, site_tx)


# export list to use as source list of counties going forward
write.csv(siteCounties, paste0(root, "data/admin/Siting_Counties_MasterList.csv"), row.names = FALSE)
