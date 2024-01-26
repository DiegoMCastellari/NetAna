import geopandas as gpd
import momepy
import networkx as nx
from .mapping_elements import create_nodes_maps, map_node_ids_in_graph_gdfs



#************* CREATE ***************

# create a graph from a gdf of linestrings (no multilines)
def create_graph_from_gdf(gdf_network, f_cost, v_crs_proj, v_directed=False):
    gdf_network = gdf_network.to_crs(v_crs_proj)
    gdf_network['id'] = list(gdf_network.index +1)
    if f_cost != 'cost':
        gdf_network.rename(columns={f_cost:'cost'}, inplace=True)

    graph = momepy.gdf_to_nx(gdf_network[['id', 'cost', 'geometry']], approach="primal", directed=v_directed)
    nodes, edges, sw = momepy.nx_to_gdf(graph, points=True, lines=True, spatial_weights=True)

    mapping_nodes = create_nodes_maps(nodes)
    nodes, edges = map_node_ids_in_graph_gdfs(nodes, edges, mapping_nodes)

    edges['category'] = 'edge'
    return [gdf_network, graph, nodes, edges, mapping_nodes]

# create a new graph (nodes and edges) from geodata file (shp, geojson, etc)
""" def create_graph_from_file(v_file_path, v_crs_proj, v_directed=False):
    gdf_network = gpd.read_file(v_file_path)
    gdf_network = gdf_network.to_crs(v_crs_proj)
    gdf_network, graph, nodes, edges, mapping_nodes = create_graph_from_gdf(gdf_network, v_crs_proj, v_directed)
    return [gdf_network, graph, nodes, edges, mapping_nodes] """

# create a graph with all the nodes within a limit cost, from a starting node
# create a new graph (subgraph) from an existing graph,starting in a node and using the cost limit  
# returns the subgraph, and it's nodes and edges
def create_subgraph_from_node_and_cost(graph, v_node_id, d_mapping_edges, v_cost_value, f_cost_field):    
    center_node =  list(graph.nodes())[v_node_id]
    subgraph = nx.ego_graph(graph, center_node, radius=v_cost_value, distance=f_cost_field)
    sub_nodes, sub_edges, sw = momepy.nx_to_gdf(subgraph, points=True, lines=True, spatial_weights=True)
    sub_nodes, sub_edges = map_node_ids_in_graph_gdfs(sub_nodes, sub_edges, d_mapping_edges)
    sub_nodes = sub_nodes.loc[sub_nodes.node_id != v_node_id]
    sub_edges.category.fillna('edge', inplace=True)
    return [subgraph, sub_nodes, sub_edges]