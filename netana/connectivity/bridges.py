import pandas as pd
import networkx as nx

def filter_border_edges(graph, edges_bridges):
    df_point_degree = pd.DataFrame(list(graph.degree()), columns=['node_id', 'degree'])
    edges_m = edges_bridges.merge(df_point_degree[['node_id', 'degree']], left_on='node_id_st', right_on='node_id')
    edges_m.rename(columns={'degree':'degree_start'}, inplace=True)
    edges_m.drop(columns='node_id', inplace=True)
    edges_m = edges_m.merge(df_point_degree[['node_id', 'degree']], left_on='node_id_en', right_on='node_id')
    edges_m.rename(columns={'degree':'degree_end'}, inplace=True)
    edges_m.drop(columns='node_id', inplace=True)
    edges_m.loc[(edges_m.degree_start == 1) | (edges_m.degree_end == 1), 'bridge'] = 0
    edges_m.drop(columns='degree_start', inplace=True)
    edges_m.drop(columns='degree_end', inplace=True)

    return edges_bridges

def find_bridge_edges(graph, gdf_edges):

    graph_bridges = list(nx.bridges(graph))
    df_bridges = pd.DataFrame(graph_bridges, columns=['pt_start', 'pt_end'])
    df_bridges['node_st_en'] = df_bridges.apply(lambda row: str(row.pt_start) +"-"+ str(row.pt_end), axis=1)

    edges_bridges = gdf_edges.copy()
    edges_bridges['node_st_en'] = edges_bridges.apply(lambda row: str(row.node_id_st) +"-"+ str(row.node_id_en), axis=1)
    edges_bridges = edges_bridges.merge(df_bridges[['node_st_en', 'pt_end']], on='node_st_en', how='left')
    edges_bridges.rename(columns={'pt_end':'bridge'}, inplace=True)
    edges_bridges.loc[edges_bridges.bridge.notnull(), 'bridge'] = 1
    edges_bridges.bridge.fillna(0, inplace=True)

    return edges_bridges

def find_bridges(graph, gdf_edges):
    edges_bridges = find_bridge_edges(graph, gdf_edges)
    edges_bridges = filter_border_edges(graph, edges_bridges)
    return edges_bridges