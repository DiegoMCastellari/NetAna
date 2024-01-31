import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

def create_walking_network(gdf_network, crs_calc):
    gdf_network = gdf_network.explode().reset_index(drop=True)
    gdf_network = gdf_network.to_crs(crs_calc)

    gdf_network['len_m'] = gdf_network.length
    gdf_network.len_m = round(gdf_network.len_m, 2)

    gdf_network['cost'] = gdf_network['len_m'] / 80
    gdf_network['id'] = list(gdf_network.index)

    gdf_network = gdf_network[['id', 'len_m', 'cost', 'geometry']]
    return gdf_network

def split_intersecting_lines(gdf_lines):

    unary_union_result = gdf_lines.unary_union.intersection(gdf_lines.unary_union)

    gpd_lines = gpd.GeoDataFrame([unary_union_result], columns=['geometry'], geometry='geometry').explode(index_parts=False).reset_index(drop=True)
    gpd_lines['start_point'] = gpd_lines.apply(lambda row: Point(row.geometry.coords[0]), axis=1)
    gpd_lines['end_point'] = gpd_lines.apply(lambda row: Point(row.geometry.coords[1]), axis=1)
    gpd_lines['id'] = gpd_lines.index +1

    df_points_from_lines = pd.concat([gpd_lines[['start_point', 'id']].rename(columns={'start_point':'geometry'}), gpd_lines[['end_point', 'id']].rename(columns={'end_point':'geometry'})])
    df_point_count = pd.DataFrame(df_points_from_lines.geometry.value_counts()).reset_index()
    df_points_from_lines = df_points_from_lines.merge(df_point_count, on='geometry', how='left')
    df_points_from_lines.rename(columns={'id':'lines_ids'}, inplace=True)
    df_points_from_lines.lines_ids = df_points_from_lines.lines_ids.astype(str)
    df_point_ids = df_points_from_lines.groupby('geometry')['lines_ids'].apply(list).reset_index()
    df_points_from_lines.drop(columns='lines_ids', inplace=True)
    df_points_from_lines = df_points_from_lines.merge(df_point_ids, on='geometry', how='left')
    df_points_from_lines.drop_duplicates(subset='geometry', inplace=True)
    df_points_from_lines.reset_index(drop=True, inplace=True)

    df_sj_points_lines = df_points_from_lines.sjoin(gpd_lines)
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
    
    return gpd_lines, df_sj_points_lines