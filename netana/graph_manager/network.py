def create_walking_network(gdf_network, crs_calc):
    gdf_network = gdf_network.explode().reset_index(drop=True)
    gdf_network = gdf_network.to_crs(crs_calc)

    gdf_network['len_m'] = gdf_network.length
    gdf_network.len_m = round(gdf_network.len_m, 2)

    gdf_network['cost'] = gdf_network['len_m'] / 80
    gdf_network['id'] = list(gdf_network.index)

    gdf_network = gdf_network[['id', 'len_m', 'cost', 'geometry']]
    return gdf_network