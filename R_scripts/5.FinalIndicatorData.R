# What this script does:
# - Set up file and path names
# - Generate 3 nearest blocks and block groups
# - Generate transit scores
# - Join suitables sites to indicator data (provided by Laura)
# - Calculate weighted averages


# Some of these have carried forward from Laura's indicator scripts, 
# and may not be needed in code below
library(data.table)
library(dplyr) # left_join
library(tidyverse)
library(rgeos)
library(rgdal) # load mapping libraries
library(raster)
library(sp) # required for rgeos, geosphere
library(sf) # read_sf
library(lwgeom)
library(scales)
library(foreign) # read.dbf
library(geosphere) # distCosine
library(SearchTrees) # createTree


# Keep any one state and corresponding list of counties uncommented at a time
# The for loop currently handles one state only
state_code <- "ca"
state_counties <- c('081', '085', '039', '055', '057', '067','037', '005', '007', '017', '019', '043', '059', '109', '009')
#state_code <- "tx"
#state_counties <- c('201')
#state_code <- "az" 
#state_counties <- c('013')
#state_code <- "co"
#state_counties <- c('001', '005', '013', '014', '031', '035','037', '041', '043', '045', '059', '067', '069', '077', '101', '123')


for (county_code in state_counties) {

  # ----------------------------------------------------------------------
  #  0) Set up input and output file paths and names
  # ----------------------------------------------------------------------
  root <- "P:/proj_a_d/CCEP/Vote Center Siting Tool/data/"
  
  # Suitable site points by county, from CCEP1
  ccep1_op_path <- "CCEPScriptOutputs/CCEP1_Master_County_Suitable_Sites/"
  ccep1_op_suitablesites_file <- paste0(root, ccep1_op_path, state_code, "_", county_code, "_suitable_site_raw_centroids.csv")

  # Census blocks by county, pre-generated
  county_blockspoly_path <- paste0(root, "CCEPScriptInputs/Census_County_Blocks")
  county_blockspoly_file <- paste0(state_code, "_c", county_code, "_blocks") # Don't append root and path here, used separately
  
  # Block data and indicator files by state, that Laura has provided
  LD_data_path <- paste0(root, "CCEPScriptInputs/Indicator_Layers_Blocks/")  
  LD_blocksdata_file <- paste0(LD_data_path, "Decennial_Blocks/blocks", toupper(state_code), ".dbf") # Exists for all 4 states
  LD_indicator_file <- paste0(LD_data_path, "indicators_Stand_Final_", toupper(state_code), ".csv") 
  
  # Transit files by county, pre-generated  
  transit_path <- paste0(root, "CCEPScriptInputs/GTFS/")
  # This is a pattern to pick out all transit files for the county being processed
  transit_file_name <- paste0(state_code, "_", county_code, ".*.csv")
  # All transit files for the county, to be combined into one
  transit_file_list <- list.files(path = transit_path, pattern = transit_file_name, full.names = T)
  
  # Path for temporary intermediate files
  debug_op_path <- paste0(root, "CCEPScriptOutputs/R_IntermediateFiles/")
  
  # Path for final output files
  final_op_path <- paste0(root, "CCEPScriptOutputs/R_Master_County_Scored_Sites/")
  final_op_file <- paste0(final_op_path, state_code, "_", county_code, "_scored_sites_raw.csv")
  
  # Note: Data variables used below are as follows:
  #  test.points - suitable sites from CCEP1, by county
  #  poly.bg.df - block data that Laura provided, by state
  #  county_blocks_sp - census blocks for the county
  #  transit.dat.std - transit data for the county
  #  indicator.dat - indicator data that Laura provided, by state

  # ----------------------------------------------------------------------
  #  1) Read in suitable sites from CCEP1
  # ----------------------------------------------------------------------
  
  # [NEW] Read in suitable site centroids, instead of generating grid here (which was for testing)
  test.points<-read.csv(ccep1_op_suitablesites_file)
  # Temp file, for testing / validation
  write.csv(test.points, paste0(debug_op_path, "test01_original_suitablesitecentroids.csv"))
  
  # Make spatial object, using lat long fields
  tmp.test.points = test.points
  coordinates(tmp.test.points) <- ~lon+lat 
  
  # ----------------------------------------------------------------------
  #  2) Read in Laura's block data, prep columns to use in step 5
  # ----------------------------------------------------------------------
  poly.bg.df= read.dbf(LD_blocksdata_file, as.is = TRUE)
  poly.bg.df$geocode.t = substr(poly.bg.df$GEOID10, 1, 11) # create tract ID
  poly.bg.df$INTPTLAT10 = as.numeric(poly.bg.df$INTPTLAT10)
  poly.bg.df$INTPTLON10 = as.numeric(poly.bg.df$INTPTLON10)

  # [NEW] Add column geocode.b (blocks), since this is needed later
  poly.bg.df$geocode.b = poly.bg.df$GEOID10
  # Example GEOID10 from file 060050003032016
  # since the logic for geocode.t extracts 1-11, i.e. retains leading 0, have this retain 0 too

  # ----------------------------------------------------------------------
  #  3) Combine county columns with suitable site points
  # ----------------------------------------------------------------------
  # [NEW] Read in block polygons for the county 
  county_blocks_sf <- read_sf(dsn=county_blockspoly_path, layer=county_blockspoly_file)
  county_blocks_sp <- as(county_blocks_sf, "Spatial")
  
  # Apply projection of county blocks to suitable site points
  proj4string(tmp.test.points) <- proj4string(county_blocks_sp)  
  
  # Combine census columns with suitable site columns
  # test.points <- cbind(test.points, over(tmp.test.points, sacramento_poly_bg))
  # This original code was split up below for clarity / debugging
  
  tmp2.test.points <- over(tmp.test.points, county_blocks_sp)
  # over(pt,poly) creates intersection of points (in same projection) with county polygon
  # It retains all points, but only columns from the polygon, no columns from points 
  # Points are in the same order as input, hence can be used in cbind() below
  # After ovr(), no points were dropped, but many have NA in census columns. 
  # These are suitable sites whose grids intersected the county, but their centroids fell outside the county boundary
  
  test.points <- cbind(test.points, tmp2.test.points)
  # cbind() will combine columns from both inputs, retaining order of rows. 
  # Make sure both inputs have the same order of rows (verified)
  # One of the inputs has to be df. if both are spatial objects, use cbind(data.frame(A, B))
  
  rm(tmp.test.points)
  rm(tmp2.test.points)
  
  # Temp file, for testing / validation
  write.csv(test.points, paste0(debug_op_path, "test02_sites_with_censusblockdata.csv"))
  
  # Remove points that didn't match to a census block polygon (these will be points right outside
  # county boundary, i.e. the suitable sites grid overlapped the county but its centroid did not)
  test.points = test.points[!is.na(test.points$BLOCKID10),] 

  # Temp file, for testing / validation
  write.csv(test.points, paste0(debug_op_path, "test02_sites_with_censusblockdata_remove_na.csv"))
  
  # ----------------------------------------------------------------------
  #  4) Set up columns for geocode.b/bg/t in suitable sites data
  # ----------------------------------------------------------------------
  
  # [NEW] In some places, the leading 0 is dropped. But since TX county codes don't
  # start with 0, the leading digit has to be retained.
  if (state_code == "tx") {
    leading_digit <- 1
  } else {
    leading_digit <- 2
  }

  # [NEW] Sample code used GEOID10, but suitable sites data contained BLOCKID10. Replaced below.

  # Remove leading zero from block code (won't matter for TX)
  test.points$BLOCKID10 = as.character(test.points$BLOCKID10) 
  test.points$geocode.b = substr(test.points$BLOCKID10,leading_digit,nchar(test.points$BLOCKID10))
  
  # Remove last 3 digits to get block group
  test.points$geocode.bg = substr(test.points$BLOCKID10,leading_digit,nchar(test.points$BLOCKID10)-3)
  
  # Remove last 4 digits to get tract
  test.points$geocode.t = substr(test.points$BLOCKID10,leading_digit,nchar(test.points$BLOCKID10)-4)
  
  # Note: These 3 fields will contain NA for points where census columns = NA, i.e. they lie right
  # outside the county boundary
  
  # Temp file, for testing / validation
  write.csv(test.points, paste0(debug_op_path, "test03_sites_with_newgeocolumns.csv"))
  
  # [QUESTION] This was commented in original code, do we still need it?
  #test.points = subset(test.points, selec = c("lon","lat","","",""))

  # ----------------------------------------------------------------------
  #  5) Generate 3 nearest blocks and block groups in suitable sites data
  # ----------------------------------------------------------------------
  
  # Find 3 nearest neighboring census block centroids
  CBG.tree <- createTree(cbind(poly.bg.df$INTPTLON10,poly.bg.df$INTPTLAT10))
  CBG.nei <- knnLookup(CBG.tree,  newx=test.points$lon,newy=test.points$lat, k=3)
  # Find distance to nearest neighbors
  dist.CBG.nei = CBG.nei
  for(i in 1:dim(CBG.nei)[1]){
    for(j in 1:dim(CBG.nei)[2]){
      tmp = CBG.nei[i,j]
      # Split out var1 and var2 below for clarity and debugging
      var1 <- test.points[i,c("lon","lat")]
      var2 <- c(poly.bg.df$INTPTLON10[tmp],poly.bg.df$INTPTLAT10[tmp])
      # The multiplier is to convert meters to miles. 1 met = 0.000621371 miles
      dist.CBG.nei[i,j] = distCosine(var1,var2)*0.000621371 
      # [QUESTION] Where is dist.CBG.nei[] used again? 
    }
  }

  # [QUESTION] How is distance used to determine nearest 3 blocks here?
  test.points$geocode.b1 = poly.bg.df$geocode.b[CBG.nei[,1]] 
  test.points$geocode.b2 = poly.bg.df$geocode.b[CBG.nei[,2]]
  test.points$geocode.b3 = poly.bg.df$geocode.b[CBG.nei[,3]]
  # Note: These columns contain legit values even for points where census columns are NA
  
  # Nearest 3 block groups (may not be unique) - extracted from nearest 3 blocks
  test.points$geocode.bg1 = substr(test.points$geocode.b1,1,nchar(test.points$geocode.b1)-3)
  test.points$geocode.bg2 = substr(test.points$geocode.b2,1,nchar(test.points$geocode.b2)-3)
  test.points$geocode.bg3 = substr(test.points$geocode.b3,1,nchar(test.points$geocode.b3)-3)
  
  # Temp file, for testing / validation
  write.csv(test.points, paste0(debug_op_path, "test04_sites_with_3nearestBsBGs.csv"))
  

  # ----------------------------------------------------------------------
  #  6) Generate transit scores
  # ----------------------------------------------------------------------
  
  # [NEW] Read in transit data
  # Read in all transit files into one
  #
  # San Mateo has one provider with numeric stop ids (read as int), and others with strings (read as factor) 
  # This causes an error in Reduce(). Force stop_id to be a consistent type to avoid this
  transit_df_list <- lapply(transit_file_list, function(x) read.csv(x, colClasses=c("stop_id"="factor")))
  transit.dat.std <- Reduce(rbind, transit_df_list)
  # Temp file, for testing / validation
  write.csv(transit.dat.std, paste0(debug_op_path, "test05_transitstops_combined.csv"))
  
  transit.dat.std$stop_lat = as.numeric(transit.dat.std$stop_lat)
  transit.dat.std$stop_lon = as.numeric(transit.dat.std$stop_lon)
  transit.dat.std$score = as.numeric(transit.dat.std$score)
  
  # If transit data is missing (i.e. file is present with empty header), 
  # set transit score to 0 to eliminate it from weighted avg calculation
  if (is.data.frame(transit.dat.std) && nrow(transit.dat.std)==0) {
    test.points$transit.score.std = 0
  } else {
    
    # Find distance to 3 nearest transit stops
    tran.tree <- createTree(cbind(transit.dat.std$stop_lon, transit.dat.std$stop_lat))
    tran.nei <- knnLookup(tran.tree,  newx=test.points$lon,newy=test.points$lat, k=3)
    # Find distance to nearest neighbors
    dist.tran.nei = as.data.frame(tran.nei)
    for(i in 1:dim(tran.nei)[1]){
      for(j in 1:dim(tran.nei)[2]){
        tmp = tran.nei[i,j]
        # Split out var1 and var2 below for clarity and debugging
        var1 <- test.points[i,c("lon","lat")]
        var2 <- c(transit.dat.std$stop_lon[tmp],transit.dat.std$stop_lat[tmp])
        # The multiplier is to convert meters to miles. 1 met = 0.000621371 miles
        dist.tran.nei[i,j] = distCosine(var1,var2)*0.000621371
      }
    }
    
    names(dist.tran.nei) = c("transit.dist.1","transit.dist.2","transit.dist.3")
    
    test.points = cbind(test.points,dist.tran.nei)
    
    # Score of transit neighbors
    test.points$transit.score1 = NA
    test.points$transit.score2 = NA
    test.points$transit.score3 = NA
    
    for(i in 1:dim(tran.nei)[1]){
      test.points$transit.score1[i] = transit.dat.std$score[tran.nei[i,1]]
      test.points$transit.score2[i] = transit.dat.std$score[tran.nei[i,2]]
      test.points$transit.score3[i] = transit.dat.std$score[tran.nei[i,3]]
    }
    
    # Generate transit variable
    test.points$transit.score.std = NA
    
    for(i in 1:dim(test.points)[1]){
      
      # if the closest stop to a site is > 0.7 distance away, the overall score is 0
      # this was originally 0.5 miles, but was increased to 0.7 miles to pick up stops in the gaps between 0.5-mi-radius circles,
      # i.e. stops that fall into the 1-mi square grid instead of the circle will be picked up
      if(min(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i]) > 0.7) test.points$transit.score.std[i] = 0
      # else store in tmp which transit stops are less than 0.7 mile away (the length of tmp will tell us how many stops - 1, 2, or 3)
      else{
        tmp = which(c(test.points$transit.dist.1[i],test.points$transit.dist.2[i],test.points$transit.dist.3[i]) <= 0.7)
        
        # For each transit stop, 
        # -- subtract from 0.8 (since distance is inversely proportional to score, i.e. for higher distance we want lower score)
        # -- multiply by the stop frequency score, so that higehr frequency results in a higher score
        # 
        # Also, since less stops to a site should score lower than more stops,
        # -- if there is just 1 stop, tmp = 1, reduce the score by 50%  (multiply by 0.5)
        # -- if there are 2 stops, tmp = 2, reduce the score by 75%
        # -- if there are 3 stops, tmp = 3, leave the score as-is
        
        # if there is only 1 value in tmp (i.e. length(tmp) == 1), 
        if(length(tmp) == 1) test.points$transit.score.std[i] =  0.5*c((0.8 - test.points$transit.dist.1[i])*test.points$transit.score1[i],
                                                                        (0.8 - test.points$transit.dist.2[i])*test.points$transit.score2[i],
                                                                        (0.8 - test.points$transit.dist.3[i])*test.points$transit.score3[i])[tmp]
        
        # if there are 2 values in tmp (2 values under 0.7) then the score is the sum of 0.75 * the distances 
        if(length(tmp) == 2) test.points$transit.score.std[i] =  sum(0.75*c((0.8 - test.points$transit.dist.1[i])*test.points$transit.score1[i],
                                                                           (0.8 - test.points$transit.dist.2[i])*test.points$transit.score2[i],
                                                                           (0.8 - test.points$transit.dist.3[i])*test.points$transit.score3[i])[tmp])
        
        # if there are 3 values in tmp (3 values under 0.7) then the score is the sum of the 3 distances
        if(length(tmp) == 3) test.points$transit.score.std[i] =  sum(c((0.8 - test.points$transit.dist.1[i])*test.points$transit.score1[i],
                                                                       (0.8 - test.points$transit.dist.2[i])*test.points$transit.score2[i],
                                                                       (0.8 - test.points$transit.dist.3[i])*test.points$transit.score3[i])[tmp])
        
      }
    }
  
  } # end else for whether transit exists
  
  # In theory, the transit score for a vote center can be as high as 9.6 (0.8*4 + 0.8*4  + 0.8*4)
  # We don't want transit to overly influence the overall vote center score more than other indicator variables, which are all <= 1
  # So we rescale transit score from 0 to 1
  
  # This code scales it linearly, so we decided not to use it
  #test.points <- 
  #  test.points %>% 
  #  group_by(COUNTYFP10) %>% 
  #  mutate(transit.score.std_scaled = percent_rank(transit.score.std))
  
  # This code normalizes so the trend of the scaled values matches that of the input data values
  min_score = min(test.points$transit.score.std)
  max_score = max(test.points$transit.score.std)
  denom = max_score - min_score
  test.points$transit.score.std = (test.points$transit.score.std - min_score) / denom
    
  # Temp file, for testing / validation
  write.csv(test.points, paste0(debug_op_path, "test06_sites_with_transitscores.csv"))

  # ----------------------------------------------------------------------
  #  7) Combine provided indicator data columns with suitable sites
  # ----------------------------------------------------------------------
  
  # [NEW] Read in indicator data that Laura provided, as df
  indicator.dat <- read.csv(LD_indicator_file)
  # Change field name to match what we obtained from CCEP1 scored sites
  # NOTE: This automatically strips leading 0s in conversion (for non-TX states)
  indicator.dat$BLOCKID10 = as.character(indicator.dat$GEOID10) 
  
  # Strip out commas from name, to prevent issues in testing data on CLI
  indicator.dat$NAME = gsub(',', '', indicator.dat$NAME)
  
  # [NEW] Join indicator data to suitable sites
  test.points <- left_join(test.points, indicator.dat, by = c("geocode.b"="BLOCKID10"), copy = FALSE, keep = TRUE, suffix = c(".ss", ".ind"))
  
  # Temp file, for testing / validation
  write.csv(test.points, paste0(debug_op_path, "test07_sites_with_indicatordata.csv"))

  # ----------------------------------------------------------------------
  #  8) Update center and drop off scores
  # ----------------------------------------------------------------------
  
  # If transit data is missing (i.e. file is present with empty header), 
  # set the denominator to 2, since we're removing the transit variable from the wtd avg calculation
  if (is.data.frame(transit.dat.std) && nrow(transit.dat.std)==0) {
    highest_wt_denominator <- 2
  } else {
    highest_wt_denominator <- 3
  }
  
  # center score (weighted average)
  test.points$center_score = 
    # First tier: Asian American vote-by-mail rate, vehicle accessibility, Latino population, polling place voter, poverty, youth population. 
    # These 6 variables should compose 30% of the total score.
    (((test.points$rate.aisvbm.std + test.points$prc.CarAccess.std + test.points$prc.latino.std + 
         test.points$dens.poll.std + test.points$prc.pov.std + test.points$prc.youth.std)/6) * 0.3) +
    
    # Weighted tier: Latino vote-by-mail rate, youth vote-by-mail rate, county workers, disabled population, limited English proficient population, 
    # eligible non-registered voter population. 
    # These 6 variables should compose 40% of the total score. # NOTE I MADE THIS 45% TO ADD UP TO 100%
    (((test.points$rate.hisvbm.std + test.points$rate.yousvbm.std + test.points$dens.work.std + 
         test.points$prc.disabled.std + test.points$prc.nonEngProf.std + test.points$prc.ElNonReg.std)/6) * 0.45) +
    
    # Highest-weighted tier: Total vote-by-mail rate, transit score, population density. These 3 variables should compose 25% of the total score.
    (((test.points$rate.vbm.std + test.points$popDens.std + test.points$transit.score.std)/highest_wt_denominator) * 0.25)  
  
  # drop box score (weighted average)
  test.points$droppoff_score = 
    # Lowest weighted tier: Asian American vote-by-mail rate, vehicle accessibility, Latino population, polling place voter, poverty, youth population, eligible non-registered voter population. 
    # These 7 variables should compose 30% of the total score.
    ((test.points$rate.aisvbm.std + test.points$prc.CarAccess.std + test.points$prc.latino.std + 
        test.points$dens.poll.std + test.points$prc.pov.std + test.points$prc.youth.std + test.points$prc.ElNonReg.std)/7) * 0.3 +
    
    # Middle weighted tier: Latino vote-by-mail rate, youth vote-by-mail rate, county workers, disabled population, limited English proficient population. 
    # These 5 variables should compose 40% of the total score. # NOTE I MADE THIS 45% TO ADD UP TO 100%
    ((test.points$rate.hisvbm.std + test.points$rate.yousvbm.std + test.points$dens.work.std + 
        test.points$prc.disabled.std + test.points$prc.nonEngProf.std)/5 * 0.45) +
    
    # Highest weighted tier: Total vote-by-mail rate, transit score, population density. 
    # These 3 variable should compose 25% of the total score
    ((test.points$rate.vbm.std + test.points$popDens.std + test.points$transit.score.std)/highest_wt_denominator * 0.25) 
  
  write.csv(test.points, paste0(debug_op_path, "test08_sites_with_weightedaverages.csv"))
  
  # If transit data is missing (i.e. file is present with empty header), 
  # drop the column before writing final output, since it's been set to 0
  if (is.data.frame(transit.dat.std) && nrow(transit.dat.std)==0) {
    test.points <- subset(test.points, select = -c(transit.score.std))
  }
  
  # ----------------------------------------------------------------------
  #  9) Write out final output file
  # ----------------------------------------------------------------------
  
  write.csv(test.points, final_op_file)

}