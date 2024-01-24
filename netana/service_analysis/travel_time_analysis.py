import pandas as pd
import networkx as nx
from ..tools.calc_tools import split_line_by_point

def calculate_travel_time_to_all_nodes(graph, loc_node_list, mapping_nodes):
    result = nx.multi_source_dijkstra_path_length(graph, 
                                        sources = list(pd.Series(loc_node_list).map(lambda row: mapping_nodes['map_nodes'][row][0])), 
                                        cutoff=None, 
                                        weight='ttime_walk')
    df = pd.DataFrame(result.items(), columns=['node_to', 'cost_to'])
    df['node_id'] = df['node_to'].map(lambda row: mapping_nodes['map_coords'][row][0])
    df = df[['node_id', 'node_to', 'cost_to']]

    return df

def asign_cost_values_to_nodes_and_edges(gdf_nodes, gdf_edges, df_cost):
    df_nodes= gdf_nodes.merge(df_cost[['node_id', 'cost_to']], on='node_id', how='left')
    df_nodes= df_nodes[['nodeID', 'geometry', 'cost_to']]

    df_edges = gdf_edges.merge(df_cost[['node_id', 'cost_to']], left_on='node_start_id', right_on='node_id', how='left')
    df_edges = df_edges.merge(df_cost[['node_id', 'cost_to']], left_on='node_end_id', right_on='node_id', how='left')
    df_edges.rename(columns={'cost_to_x':'cost_to_start', 'cost_to_y':'cost_to_end'}, inplace=True)
    df_edges['cost_to_mean'] = (df_edges['cost_to_start'] + df_edges['cost_to_end'])/2
    df_edges.drop(columns=['node_id_x', 'node_id_y'], inplace=True)

    return df_nodes, df_edges

def create_service_area_by_cost_limit(gdf_edges, cost_limit):

    gdf_edges['cat_5_min'] = 'out'
    gdf_edges.loc[(gdf_edges.cost_to_start < cost_limit) & (gdf_edges.cost_to_end < cost_limit), 'cat_5_min'] = 'ok'
    df_edges_ok = gdf_edges.loc[gdf_edges.cat_5_min == 'ok'].reset_index()

    df_edges__from_start = gdf_edges[(gdf_edges.cost_to_start < cost_limit) & (gdf_edges.cost_to_end > cost_limit)].reset_index()
    df_edges__from_start['cat_5_min'] = 'start'
    df_edges__from_start['cost_delta'] = (cost_limit - df_edges__from_start['cost_to_start']) / (df_edges__from_start['cost_to_end'] - df_edges__from_start['cost_to_start'])

    df_edges_from_end = gdf_edges[(gdf_edges.cost_to_start > cost_limit) & (gdf_edges.cost_to_end < cost_limit)].reset_index()
    df_edges_from_end['cat_5_min'] = 'end'
    df_edges_from_end['cost_delta'] = (cost_limit - df_edges_from_end['cost_to_end']) / (df_edges_from_end['cost_to_start'] - df_edges_from_end['cost_to_end'])

    df_edges__from_start['geometry'] = df_edges__from_start.apply(lambda row: split_line_by_point(row.geometry, row.cost_delta, 'start'), axis=1)
    df_edges_from_end['geometry'] = df_edges_from_end.apply(lambda row: split_line_by_point(row.geometry, row.cost_delta, 'end'), axis=1)

    df_edges_cost_limit = pd.concat([df_edges_ok, df_edges__from_start, df_edges_from_end])

    return df_edges_cost_limit