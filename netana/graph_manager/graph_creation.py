import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString

import momepy
import networkx as nx
from .network import calculate_speed_cost, create_walking_network, reverse_line_direction
from .mapping_elements import create_nodes_maps, map_node_ids_in_graph_gdfs



#************* CREATE ***************

# create a graph from a gdf of linestrings (no multilines)
def create_graph_from_gdf(gdf_network, v_crs_proj, f_cost='cost', v_directed=False, remove_isolated=False, remove_selfloop=False):
    gdf_network = gdf_network.to_crs(v_crs_proj)
    gdf_network['id'] = list(gdf_network.index +1)
    if f_cost != 'cost':
        gdf_network.rename(columns={f_cost:'cost'}, inplace=True)

    graph = momepy.gdf_to_nx(gdf_network[['id', 'cost', 'geometry']], approach="primal", directed=v_directed)
    if remove_isolated == True:
        graph.remove_nodes_from(list(nx.isolates(graph)))
    if remove_selfloop == True:
        graph.remove_edges_from(nx.selfloop_edges(graph))

    return [graph, gdf_network]

def create_geodata_from_graph(graph):
    nodes, edges, sw = momepy.nx_to_gdf(graph, points=True, lines=True, spatial_weights=True)

    mapping_nodes = create_nodes_maps(nodes)
    nodes, edges = map_node_ids_in_graph_gdfs(nodes, edges, mapping_nodes)

    edges['category'] = 'edge'
    return [nodes, edges, mapping_nodes]


def find_nodes_connections(gdf_nodes, gdf_nodes_target, v_cost_set, v_crs_proj, v_buffer_search):
    gdf_streets_buffer = gdf_nodes.copy()
    gdf_streets_buffer = gdf_streets_buffer.to_crs(v_crs_proj)
    gdf_streets_buffer['geometry_center'] = gdf_streets_buffer.geometry
    gdf_streets_buffer.geometry = gdf_streets_buffer.buffer(v_buffer_search)
    gdf_streets_buffer['id_b'] = gdf_streets_buffer.index +1

    gdf_connections = gdf_nodes_target.copy()
    gdf_connections = gdf_connections.to_crs(v_crs_proj)
    gdf_connections = gdf_connections[['geometry']].sjoin(gdf_streets_buffer[['id_b', 'geometry']])
    gdf_connections = gdf_connections.merge(gdf_streets_buffer[['id_b', 'geometry_center']], on='id_b', how='left')
    gdf_connections['geom_lines'] = gdf_connections.apply(lambda row: LineString([row.geometry, row.geometry_center]), axis=1)
    gdf_connections['cost'] = v_cost_set
    gdf_connections = gdf_connections[['cost', 'geom_lines']] 
    gdf_connections.rename(columns={'geom_lines':'geometry'}, inplace=True)
    gdf_connections.crs = gdf_streets_buffer.crs
    
    return gdf_connections


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


#************* CREATE TRANSPORT GRAPH***************

def create_city_transport_graph(gdf_streets, dict_trasp, network_crs, v_buffer_search):
    
    gdf_streets = calculate_speed_cost(gdf_streets, network_crs, 80)
    G_streets, streets = create_graph_from_gdf(gdf_streets, network_crs, v_directed=False)
    nodes_streets, edges_streets, mapping_nodes_streets = create_geodata_from_graph(G_streets)
    streets['line_type'] = 'street'
    G_streets = G_streets.to_directed(as_view=False)
    

    graph_list = [G_streets]
    gdf_network = streets

    for k in dict_trasp.keys():
        
        gdf_trans = calculate_speed_cost(dict_trasp[k][0], network_crs, dict_trasp[k][2])
        G_trans, gdf_trans = create_graph_from_gdf(gdf_trans, network_crs, v_directed=True)
        gdf_trans['line_type'] = k

        graph_list.append(G_trans)
        gdf_network = pd.concat([gdf_network, gdf_trans])

        gdf_connections = find_nodes_connections(nodes_streets, dict_trasp[k][1], dict_trasp[k][3], network_crs, v_buffer_search)
        G_conn, gdf_conn = create_graph_from_gdf(gdf_connections, network_crs, v_directed=False)
        G_conn = G_conn.to_directed(as_view=False)
        gdf_conn['line_type'] = 'conn_'+ k

        graph_list.append(G_conn)
        gdf_network = pd.concat([gdf_network, gdf_conn])

    composed_graph = nx.compose_all(graph_list)

    return [composed_graph, gdf_network]
    