import pandas as pd
import geopandas as gpd
import networkx as nx
from ..tools.calc_tools import split_line_by_point

def calculate_travel_time_to_all_nodes(graph, f_cost, loc_node_list, mapping_nodes):
    result = nx.multi_source_dijkstra_path_length(graph, 
                                        sources = list(pd.Series(loc_node_list).map(lambda row: mapping_nodes['map_nodes'][row][0])), 
                                        cutoff=None, 
                                        weight=f_cost)
    df = pd.DataFrame(result.items(), columns=['node_to', 'cost_to'])
    df['node_id'] = df['node_to'].map(lambda row: mapping_nodes['map_coords'][row][0])
    df = df[['node_id', 'node_to', 'cost_to']]

    return df

def asign_cost_values_to_nodes_and_edges(gdf_nodes, gdf_edges, df_cost):
    df_nodes= gdf_nodes.merge(df_cost[['node_id', 'cost_to']], on='node_id', how='left')
    df_nodes= df_nodes[['nodeID', 'geometry', 'cost_to']]

    df_edges = gdf_edges.merge(df_cost[['node_id', 'cost_to']], left_on='pt_start_id', right_on='node_id', how='left')
    df_edges = df_edges.merge(df_cost[['node_id', 'cost_to']], left_on='pt_end_id', right_on='node_id', how='left')
    df_edges.rename(columns={'cost_to_x':'cost_start', 'cost_to_y':'cost_end'}, inplace=True)
    df_edges['cost_mean'] = (df_edges['cost_start'] + df_edges['cost_end'])/2
    df_edges.drop(columns=['node_id_x', 'node_id_y'], inplace=True)

    return df_nodes, df_edges

def create_service_area_by_cost_limit(gdf_edges, cost_limit):

    gdf_edges['cat_limit'] = 'out'
    gdf_edges.loc[(gdf_edges.cost_start < cost_limit) & (gdf_edges.cost_end < cost_limit), 'cat_limit'] = 'ok'
    df_edges_ok = gdf_edges.loc[gdf_edges.cat_limit == 'ok'].reset_index(drop=True)

    df_edges__from_start = gdf_edges[(gdf_edges.cost_start < cost_limit) & (gdf_edges.cost_end > cost_limit)].reset_index(drop=True)
    df_edges__from_start['cat_limit'] = 'start'
    df_edges__from_start['cost_delta'] = (cost_limit - df_edges__from_start['cost_start']) / (df_edges__from_start['cost_end'] - df_edges__from_start['cost_start'])

    df_edges_from_end = gdf_edges[(gdf_edges.cost_start > cost_limit) & (gdf_edges.cost_end < cost_limit)].reset_index(drop=True)
    df_edges_from_end['cat_limit'] = 'end'
    df_edges_from_end['cost_delta'] = (cost_limit - df_edges_from_end['cost_end']) / (df_edges_from_end['cost_start'] - df_edges_from_end['cost_end'])

    df_edges__from_start['geometry'] = df_edges__from_start.apply(lambda row: split_line_by_point(row.geometry, row.cost_delta, 'start'), axis=1)
    df_edges_from_end['geometry'] = df_edges_from_end.apply(lambda row: split_line_by_point(row.geometry, row.cost_delta, 'end'), axis=1)

    df_edges_cost_limit = pd.concat([df_edges_ok, df_edges__from_start, df_edges_from_end])

    df_edges_cost_limit.drop(columns=['cat_limit', 'cost_delta'], inplace=True)
    df_edges_cost_limit['cost_limit'] = cost_limit
    return df_edges_cost_limit

def calculate_service_edges(graph, gdf_nodes, gdf_edges, f_cost, v_cost_limit, list_source_nodes, mapping_nodes):
    df_cost_times = calculate_travel_time_to_all_nodes(graph, f_cost, list_source_nodes, mapping_nodes)
    gdf_nodes, gdf_edges = asign_cost_values_to_nodes_and_edges(gdf_nodes, gdf_edges, df_cost_times)
    df_edges_cost_limit = create_service_area_by_cost_limit(gdf_edges, v_cost_limit)
    return df_edges_cost_limit


## SERVICES AREAS

# create service area for a single cost limit
def create_service_area(gdf_edges, v_buffer_meters, v_dissolve_distance):
    cost_limit_value = list(gdf_edges.cost_limit.unique())[0]
    v_dissolve_distance_retract = (-0.99) * v_dissolve_distance
    v_buffer_meters = v_buffer_meters - v_dissolve_distance *0.01

    gdf_edges_buffer = gdf_edges.copy()
    gdf_edges_buffer.geometry = gdf_edges.buffer(v_dissolve_distance) # , cap_style=2
    gdf_edges_buffer = gdf_edges_buffer.dissolve(by='cost_limit').reset_index(drop=True)

    gdf_edges_buffer.geometry = gdf_edges_buffer.buffer(v_dissolve_distance_retract, cap_style=2)
    gdf_edges_buffer.geometry = gdf_edges_buffer.buffer(v_buffer_meters)

    gdf_edges_buffer['cost_limit'] = cost_limit_value

    return gdf_edges_buffer

# merge service areas of different cost limits, into polygons or rings by limit cost
def merge_service_areas_polygons( list_gpd_service_areas, v_type='rings'):

    gpd_all_areas = pd.concat(list_gpd_service_areas) 
    gpd_all_areas = gpd_all_areas.sort_values('cost_limit', ascending=True).reset_index(drop=True)
    l_cost_list = list(gpd_all_areas['cost_limit'].sort_values(ascending=False))

    if v_type == 'rings':
        gpd_service_areas_result = gpd.GeoDataFrame([], columns=['cost_limit', 'geometry'], geometry='geometry')

        for i in range(len(l_cost_list)-1):
            p_area_bigger = gpd_all_areas.loc[gpd_all_areas.cost_limit <= l_cost_list[i]]
            p_area_smaller = gpd_all_areas.loc[gpd_all_areas.cost_limit <= l_cost_list[i+1]]

            p_area_diff = p_area_bigger.overlay(p_area_smaller[['geometry']], how='difference') 
            p_area_diff = p_area_diff[['cost_limit', 'geometry']] 
            gpd_service_areas_result = pd.concat([gpd_service_areas_result, p_area_diff])

        gpd_service_areas_result = pd.concat([gpd_service_areas_result, p_area_smaller])
        gpd_service_areas_result.reset_index(inplace=True, drop=True)

        return gpd_service_areas_result
    
    else:
        return gpd_all_areas
    
## SERVICES AREAS FOR MULTIPLE COST LIMITS
def create_service_area_for_multiple_costs(graph, gdf_nodes, gdf_edges, f_cost , list_cost, list_source_nodes, mapping_nodes, v_buffer_meters, v_dissolve_distance, area_type='rings'): 

    list_costs_buffers = []
    for v_cost_limit in list_cost:
        df_edges_cost_limit = calculate_service_edges(graph, gdf_nodes, gdf_edges, f_cost, v_cost_limit, list_source_nodes, mapping_nodes)
        df_edges_cost_limit_buffer = create_service_area(df_edges_cost_limit, v_buffer_meters, v_dissolve_distance)
        list_costs_buffers.append(df_edges_cost_limit_buffer)

    gdf_service_areas = merge_service_areas_polygons( list_costs_buffers, area_type)

    return gdf_service_areas