# OSM data download?

library(osmdata)

# Define bounding box
getbb("colorado usa")
q <- opq(getbb("colorado usa"))


# 
q <- opq("colorado usa") %>%
  add_osm_feature(key="building", value="civic") %>%
  osmdata_sf()

q
