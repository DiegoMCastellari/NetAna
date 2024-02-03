import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import networkx as nx

def calculate_speed_cost(gdf_network, v_speed): # speed = m/min
    
    gdf_network['dist'] = gdf_network.length
    gdf_network.dist = round(gdf_network.dist, 2)

    gdf_network['cost'] = gdf_network['dist'] / v_speed

    return gdf_network

def create_gdf_network(gdf_network, v_crs_proj, v_speed, v_label=None):
    gdf_network['id'] = list(gdf_network.index +1)
    gdf_network = gdf_network.explode(index_parts=True).reset_index(drop=True)
    gdf_network = gdf_network.to_crs(v_crs_proj)
    
    calculate_speed_cost(gdf_network, v_speed)
    gdf_network = gdf_network[['id', 'dist', 'cost', 'geometry']]

    if v_label:
        gdf_network['label'] = v_label
        gdf_network = gdf_network[['id', 'dist', 'cost', 'label', 'geometry']]

    return gdf_network

##**************  NETWORKS CONNECTIONS (JOINS) 

def extract_points_from_network(gdf_network):

    list_points_start = gdf_network.apply(lambda row: Point(row.geometry.coords[0]), axis=1)
    list_points_end = gdf_network.apply(lambda row: Point(row.geometry.coords[-1]), axis=1)
    gdf_points = gpd.GeoDataFrame(pd.concat([list_points_start, list_points_end]), columns=['geometry'], geometry='geometry')
    gdf_points.drop_duplicates(subset='geometry', inplace=True)
    gdf_points.reset_index(inplace=True, drop=True)
    gdf_points.crs = gdf_network.crs

    return gdf_points

def create_connections_network(gdf_network_source, gdf_network_target, v_cost_set, v_crs_proj, v_buffer_search):

    gdf_nodes_source = extract_points_from_network(gdf_network_source)
    gdf_nodes_target = extract_points_from_network(gdf_network_target)

    gdf_streets_buffer = gdf_nodes_source.copy()
    gdf_streets_buffer = gdf_streets_buffer.to_crs(v_crs_proj)
    gdf_streets_buffer['geometry_center'] = gdf_streets_buffer.geometry
    gdf_streets_buffer.geometry = gdf_streets_buffer.buffer(v_buffer_search)
    gdf_streets_buffer['id_b'] = gdf_streets_buffer.index +1

    gdf_connections = gdf_nodes_target.copy()
    gdf_connections = gdf_connections.to_crs(v_crs_proj)
    gdf_connections = gdf_connections[['geometry']].sjoin(gdf_streets_buffer[['id_b', 'geometry']])
    gdf_connections = gdf_connections.merge(gdf_streets_buffer[['id_b', 'geometry_center']], on='id_b', how='left')
    gdf_connections['geom_lines'] = gdf_connections.apply(lambda row: LineString([row.geometry, row.geometry_center]), axis=1)
    gdf_connections['id'] = list(gdf_connections.index +1)
    gdf_connections['cost'] = v_cost_set
    gdf_connections = gdf_connections[['id', 'cost', 'geom_lines']] 
    gdf_connections.rename(columns={'geom_lines':'geometry'}, inplace=True)
    gdf_connections.crs = gdf_streets_buffer.crs
    
    if ('label' in list(gdf_network_source.columns)) & ('label' in list(gdf_network_target.columns)):
        v_label = list(gdf_network_source.label.unique())[0] +"_"+ list(gdf_network_target.label.unique())[0]
        gdf_connections['label'] = v_label
    return gdf_connections


##************** COMBINE MULTIPLE GDF NETWORKS

"""
    gdf_dict = {
        'street': {
            'gdf':              xxx,
            'cost_field':       xxx,

        }
    }

    connection_dict= {
        'street'= {
            'target':              xxx,
            'cost': 
            'buffer_search':
        }
            
    }
"""

def network_from_multi_gdfs(gdf_dict, v_crs_proj, connection_dict=False):

    list_networks = []
    for net_keys in gdf_dict.keys():
        gdf_net = gdf_dict[net_keys]['gdf']
        v_speed = gdf_dict[net_keys]['speed']
        v_label = net_keys
        gdf_net_clean = create_gdf_network(gdf_net, v_crs_proj, v_speed, v_label=v_label)
        list_networks.append(gdf_net_clean)

    if connection_dict != False:
        for con_key in connection_dict.keys():
            gdf_network_source = gdf_dict[con_key]['gdf']
            gdf_network_target = gdf_dict[connection_dict[con_key]['target']]['gdf']
            v_cost_set = connection_dict[con_key]['cost']
            v_buffer_search = connection_dict[con_key]['buffer_search']
            gdf_con = create_connections_network(gdf_network_source, gdf_network_target, v_cost_set, v_crs_proj, v_buffer_search)
            gdf_network['label']= con_key +"_"+ connection_dict[con_key]['target']
            list_networks.append(gdf_con)
    
    gdf_network = pd.concat(list_networks)
    gdf_network.crs = gdf_net_clean.crs

    return gdf_network

##************** TOPOLOGY

def reverse_line_direction(gdf_lines):

    reversed_lines = gdf_lines.apply(lambda row: LineString([row.geometry.coords[1], row.geometry.coords[0]]), axis=1)
    df = gpd.GeoDataFrame(reversed_lines, columns=['geometry'], geometry='geometry')

    columns_list = gdf_lines.columns
    columns_list.remove('geometry')
    for col in columns_list:
        df[col] = gdf_lines[col]
    
    return df


def classify_points_position(gpd_points, gpd_lines):
    
    df_point_count = pd.DataFrame(gpd_points.geometry.value_counts()).reset_index()
    gpd_points = gpd_points.merge(df_point_count, on='geometry', how='left')
    gpd_points.rename(columns={'id':'lines_ids'}, inplace=True)
    gpd_points.lines_ids = gpd_points.lines_ids.astype(str)
    df_point_ids = gpd_points.groupby('geometry')['lines_ids'].apply(list).reset_index()
    gpd_points.drop(columns='lines_ids', inplace=True)
    gpd_points = gpd_points.merge(df_point_ids, on='geometry', how='left')
    gpd_points.drop_duplicates(subset='geometry', inplace=True)
    gpd_points.reset_index(drop=True, inplace=True)

    df_sj_points_lines = gpd_points.sjoin(gpd_lines)
    df_lines_ids = df_sj_points_lines.groupby('geometry')['id'].apply(list).reset_index()
    df_lines_ids.rename(columns={'id':'lines_ids_sj'}, inplace=True)
    df_sj_points_lines = df_sj_points_lines[['geometry', 'count', 'lines_ids']]
    df_sj_points_lines = df_sj_points_lines.merge(df_lines_ids, on='geometry', how='left')
    df_sj_points_lines['lines_count'] = df_sj_points_lines.apply(lambda row: len(row.lines_ids_sj), axis=1)
    df_sj_points_lines.drop_duplicates(subset='geometry', inplace=True)
    df_sj_points_lines.reset_index(drop=True, inplace=True)
    df_sj_points_lines.rename(columns={'count':'point_count'}, inplace=True)
    df_sj_points_lines.lines_ids_sj = df_sj_points_lines.lines_ids_sj.astype(str)

    df_sj_points_lines['point_type'] = 'node'
    df_sj_points_lines.loc[(df_sj_points_lines.point_count == 1) & (df_sj_points_lines.lines_count == 1), 'point_type'] = 'border'
    df_sj_points_lines.loc[(df_sj_points_lines.point_count == 1) & (df_sj_points_lines.lines_count != 1), 'point_type'] = 'error'
    df_sj_points_lines = df_sj_points_lines[['geometry', 'point_count', 'lines_count', 'point_type']]

    return df_sj_points_lines

def classify_edge_position(gpd_points, gpd_lines):
    gdf_lines_network_2 = gpd_lines.merge(gpd_points[['geometry', 'point_type']], left_on='start_point', right_on='geometry', how='left')
    gdf_lines_network_2.rename(columns={'point_type':'point_type_start'}, inplace=True)
    gdf_lines_network_2 = gdf_lines_network_2.merge(gpd_points[['geometry', 'point_type']], left_on='end_point', right_on='geometry', how='left')
    gdf_lines_network_2.rename(columns={'point_type':'point_type_end'}, inplace=True)
    gdf_lines_network_2[ 'edge_type'] = 'edge'
    gdf_lines_network_2.loc[(gdf_lines_network_2.point_type_start == 'border') | ((gdf_lines_network_2.point_type_end == 'border')), 'edge_type'] = 'border'

    gpd_lines[ 'edge_type'] = gdf_lines_network_2[ 'edge_type']
    return gpd_lines


def extract_points_from_lines(gpd_lines):
    gpd_lines['start_point'] = gpd_lines.apply(lambda row: Point(row.geometry.coords[0]), axis=1)
    gpd_lines['end_point'] = gpd_lines.apply(lambda row: Point(row.geometry.coords[1]), axis=1)
    gpd_lines['id'] = gpd_lines.index +1

    df_points_from_lines = pd.concat([gpd_lines[['start_point', 'id']].rename(columns={'start_point':'geometry'}), gpd_lines[['end_point', 'id']].rename(columns={'end_point':'geometry'})])
    df_points_classified = classify_points_position(df_points_from_lines, gpd_lines)
    df_lines_classified = classify_edge_position(df_points_classified, gpd_lines)

    df_points_classified.crs = gpd_lines.crs
    df_lines_classified.crs = gpd_lines.crs

    return df_lines_classified, df_points_classified

def split_intersecting_lines(gdf_lines):

    unary_union_result = gdf_lines.unary_union.intersection(gdf_lines.unary_union)

    gpd_lines = gpd.GeoDataFrame([unary_union_result], columns=['geometry'], geometry='geometry').explode(index_parts=False).reset_index(drop=True)
    df_lines_classified, df_points_classified = extract_points_from_lines(gpd_lines)
    
    df_points_classified.crs = gdf_lines.crs
    df_lines_classified.crs = gdf_lines.crs

    return df_lines_classified, df_points_classified

def set_island_to_nodes(graph, gdf_nodes):
    islands = {}
    for i, c in enumerate(nx.connected_components(graph)):
        if i != 0: 
            islands[f"I{i}"] = c

    gdf_nodes['island'] = 0
    for k in islands.keys():
        for p in list(islands[k]):
            gdf_nodes.loc[gdf_nodes.coords == p, 'island'] = k

    return gdf_nodes


