import pandas as pd

# create the field node_id in the node gdf, with its mapping id
# create the fields node_start_id and node_end_id in the edges gdf, with mapping ids of the starting and ending point of the each edge
def map_node_ids_in_graph_gdfs(gdf_nodes, gdf_edges, mapping):
    gdf_nodes['node_id'] = 'x'
    gdf_nodes['node_id'] = gdf_nodes['geometry'].map(lambda row: mapping['map_geom'][row][0])
    map_nodes_to_edges = pd.Series(gdf_nodes.node_id.values, index=gdf_nodes.coords).to_dict()

    gdf_edges['node_start_id'] = 'x'
    gdf_edges['node_end_id'] = 'x'
    gdf_edges['node_start_id'] = gdf_edges['geometry'].map(lambda row: map_nodes_to_edges[row.coords[0]])
    gdf_edges['node_end_id'] = gdf_edges['geometry'].map(lambda row: map_nodes_to_edges[row.coords[-1]])

    return [gdf_nodes, gdf_edges]

# create a dictionary of the nodes in the graph = {id: [node, geometry]} => node in graph (tuple of coords), geometry in shp
def create_nodes_maps(gdf_nodes):
    gdf_nodes['coords'] = gdf_nodes.apply(lambda row: (row.geometry.x, row.geometry.y), axis = 1)
    map_nodes = gdf_nodes.apply(lambda row: [(row.geometry.x, row.geometry.y), row.geometry], axis = 1).to_dict()
    map_coords= gdf_nodes.set_index('coords').T.to_dict('list') 
    map_geom = gdf_nodes.set_index('geometry').T.to_dict('list') 

    return {'map_nodes':map_nodes, 'map_coords':map_coords, 'map_geom':map_geom}