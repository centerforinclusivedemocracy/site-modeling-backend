# Calculate VBM Rates and Poll Share Rates for Harris County, TX

root = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/"
genRoot = "C:/Users/lauradal/Box/CCEP Files/Data/"
TXroot ="C:/Users/lauradal/Box/CCEP Files/Siting Tool/Texas Siting Tool/data/"

library(foreign) # load libraries
library(rgdal)
library(plyr)
library(dplyr)
library(purrr)
library(sf)

### Prepare Data ####
gen16 = read.csv(paste0(TXroot, "voter/All_Voting_2016General-LD.csv"), stringsAsFactors = FALSE, colClasses = c("PCT..NUM."="character"))
colnames(gen16)[1] <- "PRECINC"

gen16RaceEth = read.csv(paste0(TXroot, "voter/All Voting Combined-RaceEth-2016-LD.csv"), stringsAsFactors = FALSE, colClasses = c("PCT"="character"))
colnames(gen16RaceEth)[1] <- "PRECINC"
head(gen16)
head(gen16RaceEth)

gen16youth = read.csv(paste0(TXroot, "voter/All Voting Combined-Youth-2016-LD.csv"),stringsAsFactors = FALSE, colClasses = c("precinct"="character"))
gen16youth = gen16youth[,c(1, 4:5)]
colnames(gen16youth) <- c("PRECINC", "Youth.VBM", "Youth.Vote")
head(gen16youth)


# merge the two election shapefiles and clean up 
gen16$Tot.Poll = gen16$Early.Voting + gen16$Election.Day.Ballots.Cast
colnames(gen16)[5] <- c("Tot.VBM")

elec = list(gen16RaceEth, gen16[,c(1, 5, 9)], gen16youth) %>% reduce(full_join)
head(elec)


#### Convert Precinct Geometry to Block ####
# load the blocks-precinct converstion geomtry
conver <- read_sf(dsn="C:/Users/lauradal/Box/CCEP Files/Siting Tool/Texas Siting Tool/data", layer="blocks_prec_conversion_TX")
head(conver)

# merge conversion file wiht election file

block = merge(conver[,-c(2, 3, 5, 6)], elec, by="PRECINC", all=TRUE)
block = as.data.frame(block)
head(block)


###  Multiply each precinct value by the proportion 

# Reg data
blockPRODUCT <- 
  block %>%
  dplyr::group_by(PRECINC, GEOID10) %>%
  mutate_at(.funs=funs(. *prc_In_), 
            .vars=vars(Tot.Reg, Tot.Vote, Latino.Reg, Latino.Poll, Latino.VBM, Latino.Vote, Asn.Reg, Asn.Poll, Asn.VBM ,Asn.Vote ,Tot.VBM, Tot.Poll, Youth.VBM, Youth.Vote )) %>%  # multiply
  as.data.frame()

head(blockPRODUCT)


#### SUm records by block 
blockPRODUCT_agg = 
blockPRODUCT %>%
  dplyr::select(-PRECINC, -prc_In_, -geometry) %>%
  dplyr::group_by(GEOID10) %>%
  dplyr::summarise_all(sum, na.rm=TRUE) %>%
  mutate(FIPS = "48201")

head(blockPRODUCT_agg)


#### Calculate VBM rates for Youth, Asian Am, Latino, and Total ####

vbmrate =
  blockPRODUCT_agg %>%
  dplyr::group_by(GEOID10, FIPS) %>%
  dplyr::mutate(
    TotVBM = Tot.VBM/Tot.Vote,
    AsnVBM = Asn.VBM/Asn.Vote,
    LatVBM = Latino.VBM/Latino.Vote,
    YouthVBM = Youth.VBM/Youth.Vote # don't have the voter file to be able to calculate youth rates yet
  ) %>%
  as.data.frame()

head(vbmrate)


## Calculate polling place share

pollShareTot =
  blockPRODUCT_agg %>% 
  dplyr::group_by(FIPS) %>%
  dplyr::summarize(pollCountyTot = sum(Tot.Poll , na.rm=T))
head(pollShareTot)

pollShare =
  blockPRODUCT_agg %>%
  dplyr::full_join(pollShareTot) %>%
  dplyr::mutate(
    pollShare = Tot.Poll/pollCountyTot
  ) %>%
  as.data.frame()
head(pollShare)

#
### Export block-level data for model ###
outputRoot = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output/"


write.csv(vbmrate[,c(1, 16:20)], paste0(outputRoot, "VBM_Use_Rate_BlocksTX.csv"), row.names = FALSE)

write.csv(pollShare[,c(1, 16, 18)], paste0(outputRoot, "PollShare_BlocksTX.csv"), row.names = FALSE)




##### Aggregate to Tracts for visualization ####
blockPRODUCT_agg$GEOID = substr(blockPRODUCT_agg$GEOID10, 1, 11)
head(blockPRODUCT_agg)

#### Calculate VBM rates for Youth, Asian Am, Latino, and Total ####
vbmrateTract = 
  blockPRODUCT_agg %>%
  dplyr::group_by(GEOID, FIPS) %>%
  dplyr::summarize(
    V_TOTREG_R = sum(Tot.Vote, na.rm=T),
    V_TotHisp = sum(Latino.Vote, na.rm=T),
    V_TotAsian = sum(Asn.Vote, na.rm=T),
    V_TotYouth = sum(Youth.Vote, na.rm=T),
    M_TOTREG_R = sum(Tot.VBM, na.rm=T),
    M_TotHisp = sum(Latino.VBM, na.rm=T),
    M_TotAsian = sum(Asn.VBM, na.rm=T),
    M_TotYouth = sum(Youth.VBM, na.rm=T)
  )


head(vbmrateTract)
table(vbmrateTract$FIPS)

vbmrateTract =
  vbmrateTract %>%
  dplyr::group_by(GEOID, FIPS) %>%
  dplyr::mutate(
    TotVBM = M_TOTREG_R/V_TOTREG_R,
    AsnVBM = M_TotAsian/V_TotAsian,
    LatVBM = M_TotHisp/V_TotHisp,
    YouthVBM = M_TotYouth/V_TotYouth
  ) %>%
  as.data.frame()

head(vbmrateTract)
table(vbmrateTract$FIPS)


## Calculate polling place share
pollTract = 
  blockPRODUCT_agg %>%
  dplyr::group_by(GEOID, FIPS) %>%
  dplyr::summarize(
    P_TOTREG_R = sum(Tot.Poll, na.rm=T),
    P_TotHisp = sum(Latino.Poll, na.rm=T),
    P_TotAsian = sum(Asn.Poll, na.rm=T)
    #P_TotYouth = sum(P_TotYouth, na.rm=T)
  )
head(pollTract)

# calc share
pollShareTotTract =
  blockPRODUCT_agg %>% 
  dplyr::group_by(FIPS) %>%
  dplyr::summarize(pollCountyTot = sum(Tot.Poll, na.rm=T))
head(pollShareTot)

pollShareTract =
  pollTract %>%
  dplyr::full_join(pollShareTotTract) %>%
  dplyr::mutate(
    pollShare = P_TOTREG_R/pollCountyTot
  ) %>%
  as.data.frame()
head(pollShareTract)



### Export Tract data for visualization ###
outputRoot = "C:/Users/lauradal/Box/CCEP Files/Siting Tool/data/output/"


write.csv(vbmrateTract[,c(1, 2, 11:14)], paste0(outputRoot, "visualize/VBM_Use_Rate_Tracts_PrecinctsTX.csv"), row.names = FALSE)

write.csv(pollShareTract[,c(1, 2, 7)], paste0(outputRoot, "visualize/PollShare_PrecinctsTractsTX.csv"), row.names = FALSE)
