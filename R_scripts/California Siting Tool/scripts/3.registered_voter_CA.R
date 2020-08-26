# Registered Voter Count (block level)
# .	Data sources: Statewide Database voter registration data (2014 General Election, 2016 General Election); American Community Survey 5-Year Estimate CVAP (2013-2017); Census 2010. 
# .	Calculation: Convert voter data to the block level and average voter registration totals for 2014 and 2016. 

library(dplyr)
library(data.table)
library(tidyr)
library(purrr)

############# SET UP DATA ############# 
# root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
root = "/Users/lauradaly/Documents/GreenInfo/Contract Work/Siting Tool/"

# output data folder
outputRoot = "/Users/lauradaly/Documents/GreenInfo/Contract Work/Siting Tool/data/output/"


###### READ IN HERE COUNTIES INCLUDED IN THE SITING TOOL ####
siteCounties = read.csv(paste0(root, "data/admin/Siting_Counties_MasterList.csv"), stringsAsFactors = FALSE)
siteCounties$FIPS = sprintf("%05d", siteCounties$FIPS)
site_ca = siteCounties[siteCounties$State=="California",]


## read in the SWDB registration data 
reg = list( 
gen14 = fread(paste0(root, "California Siting Tool/data/voter/state_g14_registration_by_g14_rgprec.csv"), data.table = FALSE, colClasses = c("fips"="character")),
gen16 = fread(paste0(root, "California Siting Tool/data/voter/state_g16_registration_by_g16_rgprec.csv"), data.table = FALSE, colClasses = c("FIPS"="character")),
gen18 = fread(paste0(root, "California Siting Tool/data/voter/state_g18_registration_by_g18_rgprec.csv"), data.table = FALSE, colClasses = c("FIPS"="character")))

# standardize key field names
reg[[1]] <- reg[[1]][,-3]  # remove county
reg[[3]] <-  reg[[3]][,-1] # remove COUNTY

# convert all column names from gen14 to uppercase
names(reg[[1]])[1:142] <- toupper(names(reg[[1]][1:142]))

# only need to keep the total registration numbers for the registrant pop
reg = lapply(reg, function(x) x[,1:6])

# conversion list
conver = list(
  gen14 = fread(paste0(root, "California Siting Tool/data/voter/conversion/state_g14_rg_blk_map.csv"), data.table = FALSE, colClasses = c("fips"="character", "block_key"="character")),
  gen16 = fread(paste0(root, "California Siting Tool/data/voter/conversion/state_g16_rg_blk_map.csv"), data.table = FALSE, colClasses = c("FIPS"="character", "BLOCK_KEY"="character")),
  gen18 = fread(paste0(root, "California Siting Tool/data/voter/conversion/state_g18_rg_blk_map.csv"), data.table = FALSE, colClasses = c("FIPS"="character", "BLOCK_KEY"="character")))

# standardize columns and col names between years
conver[[1]] <- conver[[1]][, -3] # remove county
conver[[3]] <- conver[[3]][, -1] # remove county

# convert all column names from gen14 to uppercase
names(conver[[1]])[1:13] <- toupper(names(conver[[1]][1:13]))


# extract only CA counties of interest
reg = lapply(reg, function(x) x[x$FIPS %in% site_ca$FIPS, ])

conver = lapply(conver, function(x) x[x$FIPS %in% site_ca$FIPS, ])
head(conver[[1]])

# remove the type col from the conversion list
conver = lapply(conver, function(x) x[!names(x) %in% c("TYPE")])

head(conver[[2]])


###### Convert to Blocks ####
# collapse lists
reg <- do.call("rbind", reg)
conver <- do.call("rbind", conver)

# join conversion df to registration
regConver = left_join(reg, conver)


## Distribute PCTRGPREC across the precinct data
### first convert the percentage to a fraction
regConver$pctrgprecFRAC = regConver$PCTRGPREC/100


###  Multiply each precinct value by the proportion PCTRGPREC
# Reg data
regConverPRODUCT <- 
  regConver %>% 
  mutate(TOTREG_R = TOTREG_R*pctrgprecFRAC)


# review
head(regConverPRODUCT); head(regConver) #

### Sum records by census block  

# aggregate
regConverPRODUCT_agg =
  regConverPRODUCT %>%    
    dplyr::group_by(ELECTION, TYPE, FIPS,  BLOCK_KEY, TRACT, BLOCK) %>%    # group recoreds by census block
    dplyr::summarize(TOTREG_R = sum(TOTREG_R, na.rm=TRUE))    # sum all records for all variables (by block) 

head(regConverPRODUCT_agg)
dim(regConverPRODUCT_agg)



# create a geoid for eventual? possible? tract join
# Add a block group id.  Note that the first digit in the 4-digit block number indicates the block group number 
# (e.g. block 1019 belongs to block group 1)
regConverPRODUCT_agg$GEOID = substr(regConverPRODUCT_agg$BLOCK_KEY, 1, 11)  # extract the first digit of the block id

### Sum records by block  to get the reg totals per block 
blockReg =
  regConverPRODUCT_agg %>%
  dplyr::group_by(BLOCK_KEY, ELECTION, TYPE, FIPS, TRACT) %>%   
  dplyr::summarize(TOTREG_R = sum(TOTREG_R, na.rm = T))



###### Calculate the Average Registrant Pop per Block ####

### Averge block registration numbers
head(blockReg)

blockReg <- split(blockReg, blockReg$ELECTION, drop = FALSE)
blockReg <- lapply(blockReg, function(x) x[,-2])
colnames(blockReg[[1]])[5] <- "TOTREG_R_G14"
colnames(blockReg[[2]])[5] <- "TOTREG_R_G16"
colnames(blockReg[[3]])[5] <- "TOTREG_R_G18"

# join and calculate mean of two registration years
blockRegAvg = 
  blockReg %>% reduce(full_join) %>%
  mutate(avgReg = rowMeans(cbind(TOTREG_R_G14, TOTREG_R_G16, TOTREG_R_G18), na.rm=T),
         year = "2018") %>%   
  select(-TYPE, -TRACT, -TOTREG_R_G14, -TOTREG_R_G16, -avgReg) %>%  
  # actually I think for the registration data we're just using the most recent year (it's like a population threshold), so take out 2014, 2016 and the average. but they can be added back in if needed.
  rename("GEOID" = BLOCK_KEY,
         "county" = FIPS,
         "R_totreg_r" = TOTREG_R_G18)

head(blockRegAvg)

#### Check against 2010 pop blocks ####
library(foreign)

blocksCA <- read.dbf(paste0(root, "data/decennialblocksCA.dbf"))
head(blocksCA)

# blocks in each county with at least some population
table(subset(blocksCA, value > 0)$COUNTYFP10)

# blocks in each county with at least some reg data
table(subset(blockRegAvg, !is.na(R_totreg_r) )$county)


dim(subset(blocksCA, COUNTYFP10 =="019" & value >0))

#### Export finished block data files to output folder ###

write.csv(blockRegAvg, paste0(outputRoot, "ca_Reg_2018.csv"), row.names = FALSE)


