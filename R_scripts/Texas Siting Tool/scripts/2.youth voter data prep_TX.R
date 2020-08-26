# Prepare Youth Data
# take the Harris County voter file (2016) and create the youth (18-24) flag

root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"
TXroot ="C:/Users/lauradal/Box/CCEP Files/Siting Tool/Texas Siting Tool/data/"

library(foreign) # load libraries
library(rgdal)
library(plyr)
library(dplyr)
library(lubridate)
library(eeptools)
library(data.table)

### Prepare Data ####
gen = fread(paste0(TXroot, "voter/voterfile2016/Hector de Leon - 1116_All_Voters.txt"), data.table = FALSE, colClasses = c("precinct"="character"))
gen = gen[!is.na(gen$birthdate),-c(33:82)]

head(gen)


# calc the age based on election date 11/08/2019
# no day or month available, just assume roughly the middle of the year for everyone 
gen$dob_est = ymd(paste0(gen$birthdate, "-06-15"))
gen$elecDate = ymd("2016-11-08")

# estimate the age on election day
gen$age2016Gen = as.period(interval(start = gen$dob_est, end=gen$elecDate))
gen$ageEst = gen$age2016Gen@year

# recode age into age groups
gen$ageGroupEst = ifelse(gen$ageEst <= 24, "18-24", 
                         ifelse(gen$ageEst >100, NA, "other age"))

table(gen$ageGroupEst)
head(gen)


## All we need is youth voters, I don't need other voter age groups. Just summarize by precinct and get out of here
table(gen$vote_type)

gen$method = ifelse(gen$vote_type %in% c("M", "A"), "mail", "in person")


###  IM P SURE EVERYONE HERE VOTED...ALL HAVE A VOTE TYPE...call hector to confirm
# IF everyone here voted, then fine move ahead. If not, need to filter out. 
# Call Hector tomorrow 7/17 if he doesn't email bakc

require(dplyr)
youthVBM =
left_join(
gen %>%
  dplyr::select(-age2016Gen) %>%
  dplyr::filter(ageGroupEst =="18-24" & method=="mail") %>%
  dplyr::group_by(precinct, method, ageGroupEst) %>%
  dplyr::summarize( countVBM = length(SOS_VoterID)),

gen %>%
  dplyr::select(-age2016Gen) %>%
  dplyr::filter(ageGroupEst =="18-24") %>%
  dplyr::group_by(precinct, ageGroupEst) %>%
  dplyr::summarize( totVote = length(SOS_VoterID))) %>%
  mutate(vbm = countVBM/totVote)


# export for use in the script VBM_Rates_Poll_Share_TX
write.csv(youthVBM, paste0(TXroot, "voter/All Voting Combined-Youth-2016-LD.csv"), row.names = FALSE)
