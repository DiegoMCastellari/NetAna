import pandas as pd
import geopandas as gpd
from .edges import calculate_isochrone_edges, create_dict_time_pairs, time_from_source_to_all_nodes, edges_with_sources_to_each_source


# create isochrone polygon a for a single weight limit
def create_isochrones(gdf_edges, v_crs_proj, v_buffer_meters, v_dissolve_distance, f_dissolve='w_limit'):
    if f_dissolve=='w_limit':
        weight_limit_value = list(gdf_edges[f_dissolve].unique())[0]
    v_dissolve_distance_retract = (-0.99) * v_dissolve_distance
    v_buffer_meters = v_buffer_meters - v_dissolve_distance *0.01

    gdf_edges_buffer = gdf_edges.to_crs(v_crs_proj)
    gdf_edges_buffer.geometry = gdf_edges_buffer.buffer(v_dissolve_distance) # , cap_style=2
    gdf_edges_buffer = gdf_edges_buffer.dissolve(by=f_dissolve).reset_index()

    gdf_edges_buffer.geometry = gdf_edges_buffer.buffer(v_dissolve_distance_retract, cap_style=2)
    gdf_edges_buffer.geometry = gdf_edges_buffer.buffer(v_buffer_meters)

    if f_dissolve=='w_limit':
        gdf_edges_buffer[f_dissolve] = weight_limit_value
    gdf_edges_buffer = gdf_edges_buffer.to_crs(gdf_edges.crs)

    return gdf_edges_buffer  

def create_isochrones(graph, gdf_nodes, gdf_edges, list_node_sources, v_weight_limit, v_crs_proj, v_buffer_meters, v_dissolve_distance, f_dissolve='w_limit', f_weight="weight"):
    df_edges_cost_limit = calculate_isochrone_edges(graph, gdf_nodes, gdf_edges, f_weight, list_node_sources, v_weight_limit=v_weight_limit)
    df_edges_cost_limit = df_edges_cost_limit[['node_id_st', 'node_id_en', f_weight, 'w_start', 'w_end', 'w_mean', 'w_limit', 'geometry']]
    gdf_buffer = create_isochrones(df_edges_cost_limit, v_crs_proj, v_buffer_meters, v_dissolve_distance, f_dissolve=f_dissolve)
    return gdf_buffer

# create individual isochrones for each source, with the alternative to divide the dataset in batches
def create_individual_sources_isochrones(graph, gdf_nodes, gdf_edges, gdf_locations, list_source_nodes, f_weight, v_weight_limit, v_frac=0, v_time_factor= 1.2):
    
    df_edges_weight_limit = calculate_isochrone_edges(graph, gdf_nodes, gdf_edges, f_weight, list_source_nodes, v_weight_limit, iso_type='individual', v_frac=v_frac, v_time_factor=v_time_factor)
    df_all_isos = create_isochrones(df_edges_weight_limit[['node_source_st', 'node_source_en', 'geometry']], "3857", 5, 100, f_dissolve='node_source_st')

    df_all_isos = df_all_isos[['node_source_en', 'geometry']]
    df_all_isos.rename(columns={'node_source_en':'node_id'}, inplace=True)
    
    if 'geometry' in list(gdf_locations.columns):
        gdf_amenities_iso = df_all_isos.merge(gdf_locations.drop(columns='geometry'), how='left', on='node_id')
    else:
        gdf_amenities_iso = df_all_isos.merge(gdf_locations, how='left', on='node_id')
    # gdf_amenities_iso = gdf_amenities_iso[['src_id', 'category', 'label', 'name', 'node_id', 'geometry']]

    return gdf_amenities_iso

# merge isochrones of different weight limits, into polygons or rings by limit weight
def merge_isochrones_polygons( list_gpd_service_areas, v_type='rings'):

    gpd_all_areas = pd.concat(list_gpd_service_areas) 
    gpd_all_areas = gpd_all_areas.sort_values('w_limit', ascending=True).reset_index(drop=True)
    l_weight_list = list(gpd_all_areas['w_limit'].sort_values(ascending=False))

    if v_type == 'rings':
        gpd_service_areas_result = gpd.GeoDataFrame([], columns=['w_limit', 'geometry'], geometry='geometry')

        for i in range(len(l_weight_list)-1):
            p_area_bigger = gpd_all_areas.loc[gpd_all_areas.w_limit <= l_weight_list[i]]
            p_area_smaller = gpd_all_areas.loc[gpd_all_areas.w_limit <= l_weight_list[i+1]]

            p_area_diff = p_area_bigger.overlay(p_area_smaller[['geometry']], how='difference') 
            p_area_diff = p_area_diff[['w_limit', 'geometry']] 
            gpd_service_areas_result = pd.concat([gpd_service_areas_result, p_area_diff])

        gpd_service_areas_result = pd.concat([gpd_service_areas_result, p_area_smaller])
        gpd_service_areas_result.reset_index(inplace=True, drop=True)

        return gpd_service_areas_result
    
    else:
        return gpd_all_areas
    
## SERVICES AREAS FOR MULTIPLE weight LIMITS
def create_isochrones_for_multiple_weights(graph, gdf_nodes, gdf_edges, f_weight , list_weight, list_source_nodes, v_buffer_meters, v_dissolve_distance, area_type='rings', v_crs_proj="3857"): 

    list_weights_buffers = []
    for v_weight_limit in list_weight:
        df_edges_weight_limit = calculate_isochrone_edges(graph, gdf_nodes, gdf_edges, f_weight, list_source_nodes, v_weight_limit)
        df_edges_weight_limit_buffer = create_isochrones(df_edges_weight_limit, v_crs_proj, v_buffer_meters, v_dissolve_distance)
        list_weights_buffers.append(df_edges_weight_limit_buffer)

    gdf_service_areas = merge_isochrones_polygons( list_weights_buffers, area_type)

    return gdf_service_areas