# Harris County Voter Data
# Note that I have all the necessary data at the precinct level, but we'll have to convert to block and tract geometry ourselves (simple proportional distribution)--but still waiting on precinct shapefiles.
# for now, I'll calculate everything to the precinct level and will pause until the precinct shapefiles come in.

library(data.table)
library(dplyr)

root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
TXroot ="C:/Users/lauradal/Box/CCEP Files/Siting Tool/Texas Siting Tool/data/"
genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"

#### Prepare Data ####
gen14 = read.csv(paste0(TXroot, "voter/11-4-2014 Official Landscape Rpts/All_Voting_2014General-LD.csv"), stringsAsFactors = FALSE, colClasses = c("PCT..NUM."="character"))
gen14$ELECTION = "2014 General"


gen16 = read.csv(paste0(TXroot, "voter/All_Voting_2016General-LD.csv"), stringsAsFactors = FALSE, colClasses = c("PCT..NUM."="character"))
gen16$ELECTION = "2016 General"


gen16RaceEth = read.csv(paste0(TXroot, "voter/All Voting Combined-RaceEth-2016-LD.csv"), stringsAsFactors = FALSE, colClasses = c("PCT"="character"))
gen16RaceEth$ELECTION = "2016 General"



head(gen16)
