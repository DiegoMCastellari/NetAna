import geopandas as gpd

# create a sources
def create_sources_from_gdf(gdf_sources, v_crs_proj):
    
    gdf_sources = gdf_sources.to_crs(v_crs_proj)
    gdf_sources = gdf_sources.explode(index_parts=True).reset_index(drop=True)
    gdf_sources['id'] = list(gdf_sources.index +1)
    v_loc_type = gdf_sources.geom_type[0]

    return gdf_sources, v_loc_type

# return de id of nodes near
def search_near_node_sources (gdf_sources, gdf_nodes, search_radio):
    nodes_in = gdf_nodes.sjoin(gpd.GeoDataFrame(geometry=gdf_sources.buffer(search_radio)))
    nodes_in = nodes_in.drop_duplicates(subset='node_id').reset_index(drop=True)
    node_list = list(nodes_in.node_id)

    return node_list

""" def add_sources_to_graph(gdf_sources, G_original, gdf_nodes, gdf_edges, mapping_original, cost_field, v_max_dist):

    list_sources_node_ids = []

    for origin_point_id in list(gdf_sources.id):

        if v_loc_type == 'point':
            G_updated, mapping_nodes_updated, v_conected = na.graph_manager.graph_add.insert_source_to_graph(gdf_sources, origin_point_id, G_original, gdf_nodes, gdf_edges, mapping_original, cost_field, v_max_dist)
        elif v_loc_type == 'polygon':
    
            gdf_sources_poly = gdf_sources.loc[gdf_sources.id == origin_point_id]
            gdf_sources_poly.reset_index(drop=True, inplace=True)
            G_updated, mapping_nodes_updated, v_conected = na.graph_manager.graph_add.insert_poly_source_to_graph(gdf_sources, 0, G_original, gdf_nodes, gdf_edges, mapping_original, cost_field, v_max_dist)

        if v_conected != 0:
            source_node_id = len(G_updated.nodes) - 1
            list_sources_node_ids.append(source_node_id)

    return G_updated, mapping_nodes_updated, list_sources_node_ids """