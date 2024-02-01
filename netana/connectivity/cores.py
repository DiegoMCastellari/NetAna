import pandas as pd
import networkx as nx

def find_k_cores(graph, gdf_nodes, gdf_edges, mapping_nodes, k_value):
    k_core_values = nx.k_core(nx.Graph(graph), k=k_value)

    core_k_field = "core_"+str(k_value)
    k_core_ids = [mapping_nodes['map_coords'][x][0] for x in list(k_core_values)]

    gdf_nodes[core_k_field] = gdf_nodes.apply(lambda row: 1 if row.node_id in k_core_ids else 0, axis=1)

    gdf_edges['k_core_start'] = gdf_edges.apply(lambda row: 1 if row.node_start in k_core_ids else 0, axis=1)
    gdf_edges['k_core_end'] = gdf_edges.apply(lambda row: 1 if row.node_end in k_core_ids else 0, axis=1)
    gdf_edges[core_k_field] = 0
    gdf_edges.loc[(gdf_edges.k_core_start == 1) & (gdf_edges.k_core_end == 1), core_k_field] = 1

    return gdf_edges, gdf_nodes

def find_cores(graph, gdf_nodes, mapping_nodes):
    cores_values = nx.core_number(nx.Graph(graph))
    df = pd.DataFrame(list(cores_values.items()), columns=['Key', 'k_cores'])
    df['node_id'] = df.apply(lambda row: mapping_nodes['map_coords'][row.Key][0], axis=1)
    df = gdf_nodes.merge(df[['node_id', 'k_cores']], on='node_id', how='left')
    return df