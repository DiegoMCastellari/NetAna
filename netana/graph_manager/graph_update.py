import networkx as nx

#************* MODIFY ***************

# change nodes in graph to coords (tuple of coords, as initialy)
def relabel_nodes_to_coords(v_graph, v_mapping):
    mapping_dict = {}
    for n in v_mapping['map_coords'].keys():
        mapping_dict[v_mapping['map_coords'][n]] = n
    new_graph = nx.relabel_nodes(v_graph, mapping_dict, copy=True)
    return new_graph

# change nodes in graph to numbers (id)
def relabel_nodes_to_numbers(v_graph, v_mapping):
    mapping_dict = {}
    for n in v_mapping['map_nodes'].keys():
        mapping_dict[v_mapping['map_nodes'][n]] = n
    new_graph = nx.relabel_nodes(v_graph, mapping_dict, copy=True)
    return new_graph