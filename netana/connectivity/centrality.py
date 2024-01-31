import pandas as pd
import networkx as nx


##**************  CENTRALITIES

def calculate_closeness_centrality(graph, v_weight='cost'):
    close_centrality = nx.closeness_centrality(graph, distance=v_weight)
    return close_centrality

def calculate_eigenvector_centrality(graph, v_k=1000, v_weight='cost'):
    eigen_centrality = nx.eigenvector_centrality(graph, max_iter=v_k, weight=v_weight)
    return eigen_centrality

def calculate_betweenness_centrality(graph, object_type, nodes_coords=False, v_k=1000, v_weight='cost'):

    if object_type == 'nodes':
        if nodes_coords != False:
            between_centrality = nx.betweenness_centrality_subset(graph, sources=nodes_coords, targets=list(graph.nodes), weight=v_weight)
        else:
            between_centrality = nx.betweenness_centrality(graph, k=v_k, weight=v_weight)
        return between_centrality
    
    elif object_type == 'edges':
        if nodes_coords != False:
            between_centrality = nx.edge_betweenness_centrality_subset(graph, sources=nodes_coords, targets=list(graph.nodes), weight=v_weight)
        else:
            between_centrality = nx.edge_betweenness_centrality(graph, k=v_k, weight=v_weight)
        return between_centrality
    
    else:
        print(f"object_type parameter posible values: 'nodes' or 'edges'.-")


##**************  FUNCTIONS

def merge_centrality_values_to_edges(gdf_edges, centrality_values, mapping_nodes):
    df_edges_centrality = pd.DataFrame(list(centrality_values.items()), columns=['Key', 'Values'])
    df_edges_centrality['node_start'] = df_edges_centrality.apply(lambda row: mapping_nodes['map_coords'][row.Key[0]][0], axis=1)
    df_edges_centrality['node_end'] = df_edges_centrality.apply(lambda row: mapping_nodes['map_coords'][row.Key[1]][0], axis=1)
    df_edges_centrality['node_start_end'] = df_edges_centrality.apply(lambda row: str(row.node_start) +'-'+ str(row.node_end), axis=1)

    gdf_edges['node_start_end'] = gdf_edges.apply(lambda row: str(row.node_start) +'-'+ str(row.node_end), axis=1)
    edges_centrality = gdf_edges.merge(df_edges_centrality[['Values', 'node_start_end']], on='node_start_end', how='left')

    return edges_centrality
    

def calcualte_edges_centrality(graph, gdf_edges, mapping_nodes, centrality_type, object_type='edges', nodes_coords=False, v_k=1000, v_weight='cost'):

    print(f"Calculate {centrality_type} centrality")
    if centrality_type == 'closeness':
        centrality_values = calculate_closeness_centrality(graph, v_weight=v_weight)
        edges_centrality = merge_centrality_values_to_edges(gdf_edges, centrality_values, mapping_nodes)
        return edges_centrality
    
    elif centrality_type == 'eigenvector':
        centrality_values = calculate_eigenvector_centrality(graph, v_k=v_k, v_weight=v_weight)
        edges_centrality = merge_centrality_values_to_edges(gdf_edges, centrality_values, mapping_nodes)
        return edges_centrality
    
    elif centrality_type == 'betweenness':
        centrality_values = calculate_betweenness_centrality(graph, object_type, nodes_coords, v_k=v_k, v_weight=v_weight)
        edges_centrality = merge_centrality_values_to_edges(gdf_edges, centrality_values, mapping_nodes)
        return edges_centrality
    
    else:
        print(f"centrality_type parameter posible values: 'closeness', 'eigenvector' or 'betweenness'.-") 


