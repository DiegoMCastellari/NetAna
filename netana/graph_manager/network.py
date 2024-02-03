import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import networkx as nx

def calculate_speed_cost(gdf_network, crs_calc, v_speed): # speed = m/min
    gdf_network = gdf_network.explode(index_parts=True).reset_index(drop=True)
    gdf_network = gdf_network.to_crs(crs_calc)

    gdf_network['len_m'] = gdf_network.length
    gdf_network.len_m = round(gdf_network.len_m, 2)

    gdf_network['cost'] = gdf_network['len_m'] / v_speed
    gdf_network['id'] = list(gdf_network.index)

    gdf_network = gdf_network[['id', 'len_m', 'cost', 'geometry']]
    return gdf_network

def create_walking_network(gdf_network, crs_calc):
    gdf_network= calculate_speed_cost(gdf_network, crs_calc, 80)
    return gdf_network

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

def reverse_line_direction(gdf_lines):

    reversed_lines = gdf_lines.apply(lambda row: LineString([row.geometry.coords[1], row.geometry.coords[0]]), axis=1)
    df = gpd.GeoDataFrame(reversed_lines, columns=['geometry'], geometry='geometry')

    columns_list = gdf_lines.columns
    columns_list.remove('geometry')
    for col in columns_list:
        df[col] = gdf_lines[col]
    
    return df
