import geopandas as gpd

# return de id of nodes near
def search_near_node_location (gdf_locations, gdf_nodes, search_radio):
    nodes_in = gdf_nodes.sjoin(gpd.GeoDataFrame(geometry=gdf_locations.buffer(search_radio)))
    nodes_in = nodes_in.drop_duplicates(subset='nodeID').reset_index(drop=True)
    node_list = list(nodes_in.node_id)

    return node_list

""" def add_locations_to_graph(gdf_locations, G_original, gdf_nodes, gdf_edges, mapping_original, cost_field, v_max_dist):

    list_locations_node_ids = []

    for origin_point_id in list(gdf_locations.id):

        if v_loc_type == 'point':
            G_updated, mapping_nodes_updated, v_conected = na.graph_manager.graph_add.insert_location_to_graph(gdf_locations, origin_point_id, G_original, gdf_nodes, gdf_edges, mapping_original, cost_field, v_max_dist)
        elif v_loc_type == 'polygon':
    
            gdf_locations_poly = gdf_locations.loc[gdf_locations.id == origin_point_id]
            gdf_locations_poly.reset_index(drop=True, inplace=True)
            G_updated, mapping_nodes_updated, v_conected = na.graph_manager.graph_add.insert_poly_location_to_graph(gdf_locations, 0, G_original, gdf_nodes, gdf_edges, mapping_original, cost_field, v_max_dist)

        if v_conected != 0:
            location_node_id = len(G_updated.nodes) - 1
            list_locations_node_ids.append(location_node_id)

    return G_updated, mapping_nodes_updated, list_locations_node_ids """