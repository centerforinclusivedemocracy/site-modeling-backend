library(dplyr)
library(scales)
library(data.table)
library(sf)
library(tidycensus)
library(purrr)
library(tidyverse)
library(tidyr) 
library(viridis)
library(lwgeom)
library(rgdal)

# Set up root directory
root <- "C:/Users/lauradal/Box/CCEP Files/Colorado Siting Tool/data/"

# Load census api key to use tidycensus
census_api_key("45c000b06fce43fbd4e7631396229ca66612bc9c", install = TRUE, overwrite = TRUE)
readRenviron("~/.Renviron")

## Using tidycensus, load the variables for 2017 acs
v17 <- load_variables(2017, "acs5", cache = TRUE)



#####  1. Set up Data #### 
raceVarList <- c(Latino = "B03002_012", WhiteNHL = "B03002_003",  Black = "B03002_004", Asian = "B03002_006", NatAmerican = "B03002_005")
lepVars <- setNames(c(v17[v17$name %like% "B06007_" & v17$label %like% "less than very well", ]$name), c(rep("LEP", length(v17[v17$name %like% "B06007_" & v17$label %like% "less than very well", ]$name))))
carVars <- setNames(c(v17[v17$name %like% "B25044_" & v17$label %like% "No vehicle available", ]$name), c(rep("NoCar", length(v17[v17$name %like% "B25044_" & v17$label %like% "No vehicle available", ]$name))))
disabVars <- setNames(c(v17[v17$name %like% "B23024_" & (v17$label %like% "!!With a disability" & !v17$label %like% "!!With a disability!!"), ]$name), c(rep("disab", 2)))
povVars <- c(ByouthVar = setNames(c("B01001_007", "B01001_008", "B01001_009", "B01001_010", "B01001_031", "B01001_032", "B01001_033", "B01001_034"), c(rep("youth", 8)))
elowPoverty ="B17001_002")



#### County level ####
# total population (counties)
pop <- get_acs(geography = "county", state = "CO", variables = c(TotalPop = "B03002_001"),  year=2017, survey = "acs5", geometry = TRUE)

# population by race/eth
popRaceEth <- get_acs(geography = "county", state = "CO", variables = raceVarList, summary_var = "B03002_001",  year=2017, survey = "acs5")

# recode NAs to zero because these are controlled estimates
pop$moe[is.na(pop$moe)] <- 0
popRaceEth$moe[is.na(popRaceEth$moe)] <- 0
popRaceEth$summary_moe[is.na(popRaceEth$summary_moe)] <- 0


#### Tract Level #####

# total population 
popTract <- get_acs(geography = "tract", state = "CO", variables = c(TotalPop = "B01003_001"),  year=2017, survey = "acs5", geometry = TRUE)

####  diff characteristics ##
# population by race/eth
popRETract <- get_acs(geography = "tract", state = "CO", variables = raceVarList, summary_var = "B03002_001",  year=2017, survey = "acs5")

# population LEP
lepTract <- get_acs(geography = "tract", state = "CO", variables = lepVars, summary_var = "B06007_001",  year=2017, survey = "acs5")

# population cars
carsTract  <- get_acs(geography = "tract", state = "CO", variables = carVars, summary_var = "B25044_001",  year=2017, survey = "acs5")

# Disabled population
disabTract  <- get_acs(geography = "tract", state = "CO", variables = disabVars, summary_var = "B23024_001",  year=2017, survey = "acs5")

# population in poverty
povTract  <- get_acs(geography = "tract", state = "CO", variables = povVars, summary_var = "B17001_001",  year=2017, survey = "acs5")

# youth population
youthTract  <- get_acs(geography = "tract", state = "CO", variables = youthVar, summary_var = "B01001_001",  year=2017, survey = "acs5")


#### Combine all in long df 
coTract = rbind(popRETract, lepTract, carsTract, disabTract, povTract, youthTract)

# make fips identifier
coTract$GEOID_County = substr(coTract$GEOID, 1, 5) 

# merge county name
coTract = merge(coTract, as.data.frame(pop[,c(1,2)]), by.x="GEOID_County", by.y="GEOID", all=TRUE)

###### 2. Calculate the population density ######
pop <- st_transform(pop, "+init=epsg:26954")
popTract <- st_transform(popTract, "+init=epsg:26954")


# calc square meters
pop$areaM = st_area(pop$geometry)
popTract$areaM = st_area(popTract$geometry)


# calculate population density 
# for counties
pop$popDensM = pop$estimate/pop$areaM 
pop$popDensMile = as.numeric(pop$estimate/(pop$areaM/2589988.11)) # calculate density per sq mile

# for tracts
popTract$popDensM = popTract$estimate/popTract$areaM 
popTract$popDensMile = as.numeric(popTract$estimate/(popTract$areaM/2589988.11)) # calculate density per sq mile



##### 3. Grab the 15 most populous counties ####

# 15 highest-population counties (total population)
popTop = pop$GEOID[order(pop$estimate, decreasing = TRUE)]
popTop = popTop[1:15]
popTop

##### 4. Tract Analysis ####

### Calc the % for race/eth by tract ####

coTractSum = 
  coTract %>%
  filter(GEOID_County %in% popTop) %>%
  group_by(GEOID_County, GEOID, NAME.y, variable) %>%
  summarize(
    est = sum(estimate, na.rm=T),
    tot = mean(summary_est, na.rm = T),
    est.moe = moe_sum(moe, estimate),
    tot.moe = moe_sum(summary_moe, summary_est),
    prc = est/tot,
    prc.moe = moe_prop(est, tot, est.moe, tot.moe),
    prc.cv = ((prc.moe/1.645)/prc)*100)

head(coTractSum)


##  Look at which tracts (by county) and variabes have unreliable estimates

unreliableSum = 
coTractSum %>%
  filter(prc.cv > 40 | is.na(prc.cv)) %>%
  group_by(GEOID_County, NAME.y, variable) %>%
  summarize(
    unreliable = length(GEOID)
  ) %>% left_join(coTractSum %>%
                    group_by(GEOID_County, NAME.y, variable) %>%
                    summarize(
                      tot = length(GEOID)
                    )) %>% mutate(prc.Unreliable = unreliable/tot)

unreliableSumTable = 
unreliableSum[,-c(1,4,5)] %>% 
  spread(variable, prc.Unreliable)
unreliableSumTable

write.csv(unreliableSumTable, paste0(root, "output/Unreliability_Review_CensusTracts.csv"), row.names = FALSE)
#write.csv(unreliableSumTable, paste0(root, "output/Unreliability_Review_CensusTracts_AllCounties.csv"), row.names = FALSE) # for this version I removed the filter of CV >40%

# try including the tract counts 
View(unreliableSum %>%
       gather(type, value, -(GEOID_County:variable)) %>%
       unite(temp, variable, type) %>%
       spread(temp, value))


### look at rural counties

test = 
  coTractSum %>%
  group_by(GEOID_County, NAME.y, variable) %>%
  summarize(
    tractTot = length(GEOID)
  )

length(table(subset(test, tractTot <= 10)$NAME.y))
