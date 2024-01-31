import pandas as pd
import networkx as nx


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