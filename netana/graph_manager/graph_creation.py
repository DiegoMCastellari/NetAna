import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString

import momepy
import networkx as nx
from .network import  create_connections_network
from .graph_add import add_edges_list_to_graph


#************* CREATE ***************

# create a graph from a gdf of linestrings (no multilines)
def create_graph_from_gdf(gdf_network, v_make_directed=False, v_directed=False, remove_isolated=False, remove_selfloop=False):

    if 'label' in list(gdf_network.columns):
        graph = momepy.gdf_to_nx(gdf_network[['id', 'weight', 'label', 'geometry']], approach="primal", directed=v_directed)
    else:
        graph = momepy.gdf_to_nx(gdf_network[['id', 'weight', 'geometry']], approach="primal", directed=v_directed)

    if remove_isolated == True:
        graph.remove_nodes_from(list(nx.isolates(graph)))
    if remove_selfloop == True:
        graph.remove_edges_from(nx.selfloop_edges(graph))

    if v_make_directed == True:
        graph = graph.to_directed(as_view=False)

    graph_2 = nx.convert_node_labels_to_integers(graph, first_label=0, ordering='default', label_attribute='coords')
    if 'label' in list(gdf_network.columns):
        v_label = list(gdf_network.label.unique())[0]
        dictionary = dict(zip( list(graph_2.nodes) , [str(x) +"_"+ v_label for x in list(graph_2.nodes)]))
        graph_2 = nx.relabel_nodes(graph_2, dictionary, copy=True)

    attrs_g = {'crs': gdf_network.crs}
    graph_2.graph.update(attrs_g)

    return graph_2

def merge_graphs(list_graphs):
    if len(list_graphs) == 2:
        composed_graph = nx.compose(list_graphs[0], list_graphs[1])
    else:
        composed_graph = nx.compose_all(list_graphs)
    return composed_graph


def map_geom_nodes_rel(graph):
    dict_nodes = dict(zip(list(graph.nodes), [Point(graph.nodes[n]['coords']) for n in list(graph.nodes)]))
    dict_geom = dict(zip([Point(graph.nodes[n]['coords']) for n in list(graph.nodes)], list(graph.nodes)))
    dict_mapping_nodes = {'map_nodes':dict_nodes, 'map_geom':dict_geom}
    return dict_mapping_nodes

def nodes_to_points(graph):
    dict_mapping_nodes = map_geom_nodes_rel(graph)
    gdf_nodes = gpd.GeoDataFrame(dict_mapping_nodes['map_nodes'].items(), columns=['node_id', 'geometry'], geometry='geometry')
    gdf_nodes.crs = graph.graph['crs']
    return gdf_nodes

# extract points and linestrings from graph, and the mapping relationship between nodes ids and geometry 
def create_geodata_from_graph(graph):
    dict_mapping_nodes = map_geom_nodes_rel(graph)

    gdf_nodes = gpd.GeoDataFrame(dict_mapping_nodes['map_nodes'].items(), columns=['node_id', 'geometry'], geometry='geometry')
    gdf_edges = gpd.GeoDataFrame([graph.edges[e] for e in list(graph.edges)], geometry='geometry')

    gdf_edges['node_id_st'] = gdf_edges.apply(lambda row: dict_mapping_nodes['map_geom'][Point(row.geometry.coords[0])], axis=1)
    gdf_edges['node_id_en'] = gdf_edges.apply(lambda row: dict_mapping_nodes['map_geom'][Point(row.geometry.coords[-1])], axis=1)

    gdf_nodes.crs = graph.graph['crs']
    gdf_edges.crs = graph.graph['crs']

    return [gdf_nodes, gdf_edges, dict_mapping_nodes]

# create graph, point, edges and mapping dict. from gdf
def graph_from_gdf(gdf_network, f_weight='weight', v_label=None, v_make_directed=False, v_directed=False, remove_isolated=False, remove_selfloop=False):

    graph = create_graph_from_gdf(gdf_network, f_weight=f_weight, v_make_directed=v_make_directed, v_directed=v_directed, remove_isolated=remove_isolated, remove_selfloop=remove_selfloop)
        
    gdf_nodes, gdf_edges, dict_mapping_nodes = create_geodata_from_graph(graph)
    gdf_nodes.crs = gdf_network.crs
    gdf_edges.crs = gdf_network.crs

    return [graph, gdf_nodes, gdf_edges, dict_mapping_nodes]


##**************  GRAPHS CONNECTIONS (JOINS) 

def find_graphs_connections(graph_1, graph_2, v_weight_set, v_buffer_search, v_label):
    
    gdf_nodes_1 = nodes_to_points(graph_1)
    gdf_nodes_2 = nodes_to_points(graph_2)

    gdf_nodes_1.geometry = gdf_nodes_1.buffer(v_buffer_search)

    gdf_connections = gdf_nodes_1.sjoin(gdf_nodes_2)
    gdf_connections.rename(columns={'node_id_left':'node_start', 'node_id_right':'node_end'}, inplace=True)

    list_edges_connections = list(gdf_connections.apply(lambda row: (row.node_start, row.node_end, {'weight': v_weight_set, 'label':v_label, 'geometry': LineString([graph_1.nodes[row.node_start]['coords'], graph_2.nodes[row.node_end]['coords']])}), axis=1))

    return list_edges_connections

def create_connection_graph (graph_1, graph_2, v_weight_set, v_buffer_search, v_label):
    list_edges_connections = find_graphs_connections(graph_1, graph_2, v_weight_set, v_buffer_search, v_label)
    connection_graph = nx.Graph(list_edges_connections) 
    return connection_graph

def connect_graph_to_multiple_graphs(graph_1, list_graphs):
    final_graph = graph_1.copy()
    for graph_item in list_graphs:
        final_graph = nx.compose(final_graph, graph_item['graph'])
        list_edges_connections = find_graphs_connections(graph_1, graph_item['graph'], graph_item['weight'], graph_item['buffer_search'], graph_item['label'])
        final_graph = add_edges_list_to_graph(final_graph, list_edges_connections)
    return final_graph

# create a new graph (nodes and edges) from geodata file (shp, geojson, etc)
""" def create_graph_from_file(v_file_path, v_crs_proj, v_directed=False):
    gdf_network = gpd.read_file(v_file_path)
    gdf_network = gdf_network.to_crs(v_crs_proj)
    gdf_network, graph, nodes, edges, mapping_nodes = create_graph_from_gdf(gdf_network, v_crs_proj, v_directed)
    return [gdf_network, graph, nodes, edges, mapping_nodes] """

# create a graph with all the nodes within a limit weight, from a starting node
# create a new graph (subgraph) from an existing graph,starting in a node and using the weight limit  
# returns the subgraph, and it's nodes and edges
""" def create_subgraph_from_node_and_weight(graph, v_node_id, d_mapping_edges, v_weight_value, f_weight_field):    
    center_node =  list(graph.nodes())[v_node_id]
    subgraph = nx.ego_graph(graph, center_node, radius=v_weight_value, distance=f_weight_field)
    sub_nodes, sub_edges, sw = momepy.nx_to_gdf(subgraph, points=True, lines=True, spatial_weights=True)
    sub_nodes, sub_edges = map_node_ids_in_graph_gdfs(sub_nodes, sub_edges, d_mapping_edges)
    sub_nodes = sub_nodes.loc[sub_nodes.node_id != v_node_id]
    sub_edges.category.fillna('edge', inplace=True)
    return [subgraph, sub_nodes, sub_edges] """
    

# create graph, point, edges and mapping dict. from multiple gdfs
def create_graph_from_multigdfs(graph_dict, connection_list, v_crs_proj):

    list_graphs = []
    list_networks = []

    for graph_key in graph_dict.keys():

        dict_keys = list(graph_dict[graph_key].keys())

        if 'v_make_directed' in dict_keys:
            value_make_directed = graph_dict[graph_key]['v_make_directed']
        else:
            value_make_directed = False
        if 'v_directed' in dict_keys:
            value_v_directed = graph_dict[graph_key]['v_directed']
        else:
            value_v_directed = False
        if 'remove_isolated' in dict_keys:
            value_remove_isolated = graph_dict[graph_key]['remove_isolated']
        else:
            value_remove_isolated = False
        if 'remove_selfloop' in dict_keys:
            value_remove_selfloop = graph_dict[graph_key]['remove_selfloop']
        else:
            value_remove_selfloop = False


        graph = create_graph_from_gdf(
            gdf_network= graph_dict[graph_key]['gdf_network'], 
            v_make_directed= value_make_directed, 
            v_directed= value_v_directed, 
            remove_isolated= value_remove_isolated, 
            remove_selfloop= value_remove_selfloop
        )
        list_graphs.append(graph) 
        list_networks.append(graph_dict[graph_key]['gdf_network'])
    
    for con_key in connection_list.keys():
        gdf_nodes_key = graph_dict[ connection_list[con_key]['source'] ]['gdf_network']
        gdf_nodes_value = graph_dict[ connection_list[con_key]['target'] ]['gdf_network']
        v_weight_set = connection_list[con_key]['weight']
        v_buffer_search = connection_list[con_key]['buffer_search']

        connection_gdf = create_connections_network(gdf_nodes_key, gdf_nodes_value, v_weight_set, v_crs_proj, v_buffer_search)
        graph = create_graph_from_gdf(
            gdf_network= connection_gdf, 
            v_make_directed= True
        )
        list_graphs.append(graph) 
        list_networks.append(connection_gdf)

        gdf_network_complete = pd.concat(list_networks)
        composed_graph = nx.compose_all(list_graphs)
        gdf_nodes, gdf_edges, dict_mapping_nodes = create_geodata_from_graph(composed_graph)

        return [composed_graph, gdf_network_complete, gdf_nodes, gdf_edges, dict_mapping_nodes]