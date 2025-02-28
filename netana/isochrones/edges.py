import pandas as pd
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point
from shapely.ops import split, snap, nearest_points

def split_line_by_point(line_geometry, inter_perc, from_end_or_start):

    if from_end_or_start == 'end':
        inter_perc_calc = 1 - inter_perc
    else:
        inter_perc_calc = inter_perc
    
    v_point_middle_x = line_geometry.interpolate(inter_perc_calc, normalized=True).x
    v_point_middle_y = line_geometry.interpolate(inter_perc_calc, normalized=True).y
    minimum_distance = nearest_points(Point(v_point_middle_x, v_point_middle_y), line_geometry)[1]

    split_line = split(snap(line_geometry, minimum_distance,  0.00001), minimum_distance )
    segments = [feature for feature in split_line.geoms]

    try:
        length_1 = segments[0].length
        length_2 = segments[1].length

        if inter_perc > 0.5:
            if length_1 > length_2:
                new_geom = segments[0]
            else:
                new_geom = segments[1]
        else:
            if length_1 > length_2:
                new_geom = segments[1]
            else:
                new_geom = segments[0]
    except:
        new_geom = line_geometry

    return new_geom


# ******************************************************************************************* #  
## ISOCHRONES EDGES FUNTIONS BY WEIGHT LIMIT

def calculate_travel_time_to_all_nodes(graph, f_weight, loc_node_list):
    result = nx.multi_source_dijkstra_path_length(graph, 
                                        sources = loc_node_list, 
                                        cutoff=None, 
                                        weight=f_weight)
    df = pd.DataFrame(result.items(), columns=['node_id', 'weight_to'])
    return df

def asign_weight_values_to_nodes_and_edges(gdf_nodes, gdf_edges, df_weight):
    df_nodes= gdf_nodes.merge(df_weight[['node_id', 'weight_to']], on='node_id', how='left')
    df_nodes= df_nodes[['node_id', 'geometry', 'weight_to']]

    df_edges = gdf_edges.merge(df_weight[['node_id', 'weight_to']], left_on='nd_st', right_on='node_id', how='left')
    df_edges = df_edges.merge(df_weight[['node_id', 'weight_to']], left_on='nd_en', right_on='node_id', how='left')
    df_edges.rename(columns={'weight_to_x':'weight_start', 'weight_to_y':'weight_end'}, inplace=True)
    df_edges.drop(columns=['node_id_x', 'node_id_y'], inplace=True)

    return df_nodes, df_edges

def create_service_area_by_weight_limit(gdf_edges, weight_limit):

    gdf_edges['cat_limit'] = 'out'
    gdf_edges.loc[(gdf_edges.weight_start < weight_limit) & (gdf_edges.weight_end < weight_limit), 'cat_limit'] = 'ok'
    df_edges_ok = gdf_edges.loc[gdf_edges.cat_limit == 'ok'].reset_index(drop=True)
   
    df_edges__from_start = gdf_edges[(gdf_edges.weight_start < weight_limit) & (gdf_edges.weight_end > weight_limit)].reset_index(drop=True)
    if len(df_edges__from_start) > 0:
        df_edges__from_start['cat_limit'] = 'start'
        df_edges__from_start['weight_delta'] = (weight_limit - df_edges__from_start['weight_start']) / (df_edges__from_start['weight_end'] - df_edges__from_start['weight_start'])
        df_edges__from_start['geometry'] = df_edges__from_start.apply(lambda row: split_line_by_point(row.geometry, row.weight_delta, 'start'), axis=1)

    df_edges_from_end = gdf_edges[(gdf_edges.weight_start > weight_limit) & (gdf_edges.weight_end < weight_limit)].reset_index(drop=True)
    if len(df_edges_from_end) > 0:
        df_edges_from_end['cat_limit'] = 'end'
        df_edges_from_end['weight_delta'] = (weight_limit - df_edges_from_end['weight_end']) / (df_edges_from_end['weight_start'] - df_edges_from_end['weight_end'])
        df_edges_from_end['geometry'] = df_edges_from_end.apply(lambda row: split_line_by_point(row.geometry, row.weight_delta, 'end'), axis=1)

    df_edges_weight_limit = pd.concat([df_edges_ok, df_edges__from_start, df_edges_from_end])

    df_edges_weight_limit.drop(columns=['cat_limit'], inplace=True)
    if 'weight_delta' in list(df_edges_weight_limit.columns):
        df_edges_weight_limit.drop(columns=['weight_delta'], inplace=True)
    df_edges_weight_limit['weight_limit'] = weight_limit
    return df_edges_weight_limit

def calculate_isochrones_edges(graph, gdf_nodes, gdf_edges, f_weight, v_weight_limit, gdf_locations):
    list_source_nodes = list(gdf_locations['node_id'])
    df_weight_times = calculate_travel_time_to_all_nodes(graph, f_weight, list_source_nodes)
    gdf_nodes, gdf_edges = asign_weight_values_to_nodes_and_edges(gdf_nodes, gdf_edges, df_weight_times)
    df_edges_weight_limit = create_service_area_by_weight_limit(gdf_edges, v_weight_limit)
    return df_edges_weight_limit



# ******************************************************************************************* #  
## ISOCHRONES EDGES FUNTIONS, BY INDIVIDUAL SOURCE

# creates a dict with all node-node pairs, with the path weight, filter by a threshold
def create_dict_time_pairs(graph, f_weight, v_time, v_time_factor=2):
    v_time_tolerance = v_time * v_time_factor

    all_pairs = nx.all_pairs_dijkstra_path_length(graph, cutoff=v_time_tolerance, weight=f_weight)
    all_pairs_dict = dict(all_pairs)
    
    return all_pairs_dict

# creates a dict with all the weight for each source-node pairs (*filter sources)
def time_from_source_to_all_nodes(all_pairs_dict, list_node_sources):
    dict_you_want = {key: all_pairs_dict[key] for key in list_node_sources}

    df_all_pairs = pd.DataFrame.from_dict(dict_you_want, orient='index', dtype=None, columns=None)
    df_all_pairs = pd.DataFrame(df_all_pairs.stack().explode())
    df_all_pairs.reset_index(inplace=True)
    df_all_pairs.rename(columns={df_all_pairs.columns[0]:'node_source', df_all_pairs.columns[1]:'node_weight', df_all_pairs.columns[2]:'weight'}, inplace=True)

    return df_all_pairs

# filter edges containing the source-node pairs
def edges_with_sources_to_each_source(gdf_nodes, gdf_edges):
    df_2_start = gdf_nodes.copy()
    df_2_start.rename(columns={gdf_nodes.columns[0]:'node_source_st', gdf_nodes.columns[1]:'nd_st', gdf_nodes.columns[2]:'weight_start'}, inplace=True)

    df_2_end = gdf_nodes.copy()
    df_2_end.rename(columns={gdf_nodes.columns[0]:'node_source_en', gdf_nodes.columns[1]:'nd_en', gdf_nodes.columns[2]:'weight_end'}, inplace=True)

    gdf_edges_2 = gdf_edges[['id', 'nd_st', 'nd_en', 'geometry']]
    gdf_edges__3 = gdf_edges_2.merge(df_2_start, how='left', on='nd_st')
    gdf_edges__3 = gdf_edges__3.merge(df_2_end, how='left', on='nd_en')
    gdf_edges__3 = gdf_edges__3.loc[gdf_edges__3.node_source_st == gdf_edges__3.node_source_en].reset_index(drop=True)

    return gdf_edges__3

def calculate_all_nodes_and_edges_from_individual_sources(all_pairs_dict, gdf_edges, list_node_sources):
    gdf_sources_to_nodes = time_from_source_to_all_nodes(all_pairs_dict, list_node_sources)
    gdf_sources_to_nodes = edges_with_sources_to_each_source(gdf_sources_to_nodes, gdf_edges)
    return gdf_sources_to_nodes

def calculate_individual_isochrone_edges(graph, gdf_edges, gdf_locations, f_weight, v_weight_limit, v_frac=0, v_time_factor=1.2):

    list_source_nodes = list(gdf_locations['node_id'])
    all_pairs_dict = create_dict_time_pairs(graph, f_weight, v_weight_limit, v_time_factor)
    
    if v_frac != 0:
        list_edges = []
        for i in range(int(len(list_source_nodes)/v_frac)+1):
            i_init = v_frac * i
            i_end  = v_frac * (i+1)
            print(i, i_init, i_end, len(list_source_nodes[i_init:i_end]))
            gdf_sources_to_nodes = calculate_all_nodes_and_edges_from_individual_sources(all_pairs_dict, gdf_edges, list_source_nodes[i_init:i_end])
            gdf_edges_for_iso = create_service_area_by_weight_limit(gdf_sources_to_nodes, v_weight_limit)

            list_edges.append(gdf_edges_for_iso)

        df_all_isos = pd.concat(list_edges)
        return df_all_isos

    else:
        gdf_sources_to_nodes = calculate_all_nodes_and_edges_from_individual_sources(all_pairs_dict, gdf_edges, list_source_nodes)
        gdf_edges_for_iso = create_service_area_by_weight_limit(gdf_sources_to_nodes, v_weight_limit)
        return gdf_edges_for_iso