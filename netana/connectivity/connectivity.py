import networkx as nx

def min_edge_connectivity(graph, nodes_coords_list):
    min_edge_con = -1
    for n_1 in nodes_coords_list:
        for n_2 in nodes_coords_list:
            if min_edge_con != 1:
                if n_1 != n_2:
                    edge_con = nx.edge_connectivity(graph, s=n_1, t=n_2)
                    if min_edge_con == -1:
                        min_edge_con = edge_con
                    elif (min_edge_con > edge_con) & (edge_con != 0):
                        min_edge_con = edge_con
            else:
                return min_edge_con
    return min_edge_con