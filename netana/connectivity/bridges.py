import pandas as pd
import networkx as nx

def filter_border_edges(graph, edges_bridges, mapping_nodes):
    df_point_degree = pd.DataFrame(list(graph.degree()), columns=['point', 'degree'])
    df_point_degree['point_id'] = df_point_degree.apply(lambda row: mapping_nodes['map_coords'][row.point][0], axis=1)

    edges_m = edges_bridges.merge(df_point_degree[['point_id', 'degree']], left_on='node_start', right_on='point_id')
    edges_m.rename(columns={'degree':'degree_start'}, inplace=True)
    edges_m.drop(columns='point_id', inplace=True)
    edges_m = edges_m.merge(df_point_degree[['point_id', 'degree']], left_on='node_end', right_on='point_id')
    edges_m.rename(columns={'degree':'degree_end'}, inplace=True)
    edges_m.drop(columns='point_id', inplace=True)
    edges_m.loc[(edges_m.degree_start == 1) | (edges_m.degree_end == 1), 'bridge'] = 0
    edges_m.drop(columns='degree_start', inplace=True)
    edges_m.drop(columns='degree_end', inplace=True)

    return edges_bridges

def find_bridge_edges(graph, gdf_edges, mapping_nodes):

    graph_bridges = list(nx.bridges(graph))

    df_bridges = pd.DataFrame(graph_bridges, columns=['start', 'end'])
    df_bridges['pt_start'] = df_bridges.apply(lambda row: mapping_nodes['map_coords'][row.start][0], axis=1)
    df_bridges['pt_end'] = df_bridges.apply(lambda row: mapping_nodes['map_coords'][row.end][0], axis=1)
    df_bridges['pt_start_end'] = df_bridges.apply(lambda row: str(row.pt_start) +"-"+ str(row.pt_end), axis=1)

    edges_bridges = gdf_edges.copy()
    edges_bridges['pt_start_end'] = edges_bridges.apply(lambda row: str(row.node_start) +"-"+ str(row.node_end), axis=1)
    edges_bridges = edges_bridges.merge(df_bridges[['pt_start_end', 'pt_end']], on='pt_start_end', how='left')
    edges_bridges.rename(columns={'pt_end':'bridge'}, inplace=True)
    edges_bridges.loc[edges_bridges.bridge.notnull(), 'bridge'] = 1
    edges_bridges.bridge.fillna(0, inplace=True)

    return edges_bridges

def find_bridges(graph, gdf_edges, mapping_nodes):
    edges_bridges = find_bridge_edges(graph, gdf_edges, mapping_nodes)
    edges_bridges = filter_border_edges(graph, edges_bridges, mapping_nodes)
    return edges_bridges