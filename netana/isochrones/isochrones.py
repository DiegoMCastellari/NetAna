import pandas as pd
import geopandas as gpd
from .edges import calculate_isochrones_edges, calculate_individual_isochrone_edges
from .isochrones_polygons import create_isochrones_polygons, create_ring_isochrones, sort_isochrones_by_weight

## ISOCHRONE FOR ONE WEIGHT LIMIT
def create_isochrones(graph, gdf_nodes, gdf_edges, gdf_locations, v_weight_limit, v_buffer_meters, v_buffer_distance, f_dissolve='weight_limit', f_weight="weight"):
    df_edges_weight_limit = calculate_isochrones_edges(graph, gdf_nodes, gdf_edges, f_weight, v_weight_limit, gdf_locations)
    df_edges_weight_limit = df_edges_weight_limit[['nd_st', 'nd_en', f_weight, 'weight_start', 'weight_end', 'weight_limit', 'geometry']]
    gdf_buffer = create_isochrones_polygons(df_edges_weight_limit, v_buffer_meters, v_buffer_distance, f_dissolve=f_dissolve)
    return gdf_buffer

## ISOCHRONE FOR MULTIPLE WEIGHT LIMITS
def create_isochrones_multiple_weights(graph, gdf_nodes, gdf_edges, gdf_locations, f_weight , list_weight,  v_buffer_meters, v_buffer_distance, f_dissolve='weight_limit', area_type='rings', v_crs_proj="3857"): 

    list_weights_buffers = []
    for v_weight_limit in list_weight:
        df_edges_weight_limit_buffer = create_isochrones(graph, gdf_nodes, gdf_edges, gdf_locations, v_weight_limit, v_buffer_meters, v_buffer_distance, f_dissolve, f_weight)
        list_weights_buffers.append(df_edges_weight_limit_buffer)

    if area_type=='rings':
        gdf_service_areas = create_ring_isochrones(list_weights_buffers, f_dissolve)
    else:
        gdf_service_areas = sort_isochrones_by_weight(list_weights_buffers, f_dissolve)

    return gdf_service_areas


## INDIVIDUAL ISOCHRONE FOR ONE WEIGHT LIMIT
# create individual isochrones for each source, with the alternative to divide the dataset in batches
def create_individual_isochrones(graph, gdf_edges, gdf_locations, f_weight, v_weight_limit, v_buffer_meters, v_buffer_distance, v_frac=0, v_time_factor= 10):    
    gdf_indiv_edges_for_iso = calculate_individual_isochrone_edges(graph, gdf_edges, gdf_locations, f_weight, v_weight_limit, v_frac, v_time_factor)
    indiv_isochrones = create_isochrones_polygons(gdf_indiv_edges_for_iso, v_buffer_meters, v_buffer_distance, f_dissolve='node_source_st')

    if 'weight_limit' not in list(indiv_isochrones.columns):
        indiv_isochrones['weight_limit'] = v_weight_limit

    return indiv_isochrones

## INDIVIDUAL ISOCHRONE FOR MULTIPLE WEIGHT LIMIT
def create_individual_isochrones_multiple_weights(graph, gdf_edges, gdf_locations, f_weight, list_weight, v_buffer_meters, v_buffer_distance, f_dissolve='weight_limit', area_type='rings', v_frac=0, v_time_factor= 10):    
    
    list_weights_buffers = []
    for v_weight_limit in list_weight:
        indiv_isochrones = create_individual_isochrones(graph, gdf_edges, gdf_locations, f_weight, v_weight_limit, v_buffer_meters, v_buffer_distance, v_frac, v_time_factor)

        if 'weight_limit' not in list(indiv_isochrones.columns):
            indiv_isochrones['weight_limit'] = v_weight_limit
            
        list_weights_buffers.append(indiv_isochrones)
    
    if area_type=='rings':
        gdf_indiv_isochrones_multi_weight = create_ring_isochrones(list_weights_buffers, f_dissolve)
    else:
        gdf_indiv_isochrones_multi_weight = sort_isochrones_by_weight(list_weights_buffers, f_dissolve)

    return gdf_indiv_isochrones_multi_weight

# ******************************************************************************************* #  
##  GENERAL ISOCHRONE EDGES FUNTION

""" def calculate_isochrone_edges(graph, gdf_nodes, gdf_edges, f_weight, list_source_nodes, v_weight_limit=0, iso_type='merged', v_frac=0, v_time_factor=1.2):

    if (type(list_source_nodes) == list):
        if v_weight_limit > 0:
            if iso_type == 'merged':
                df_edges_weight_limit = calculate_weight_isochrone_edges(graph, gdf_nodes, gdf_edges, f_weight, list_source_nodes, v_weight_limit)
                return df_edges_weight_limit
            elif iso_type =='individual': 
                df_edges_weight_limit = calculate_individual_isochrone_edges(graph, gdf_edges, list_source_nodes, f_weight, v_weight_limit, v_frac, v_time_factor)
                return df_edges_weight_limit
            else:
                print("Parameter iso_type must be: 'merged' or 'individual'")
        else:
            print("Parameter v_weight_limit must be > 0")

    elif (type(list_source_nodes) == gpd.geodataframe.GeoDataFrame) | (type(list_source_nodes) == pd.core.frame.DataFrame):
        list_df_edges_weight_limit = []
        for v_time in list(list_source_nodes[f_weight].unique()):
            v_time_list_node_sources = list(list_source_nodes.loc[list_source_nodes[f_weight] == v_time, 'node_loc_id'])

            if iso_type == 'merged':
                df_edges_weight_limit = calculate_weight_isochrone_edges(graph, gdf_nodes, gdf_edges, f_weight, v_time_list_node_sources, v_time)
                df_edges_weight_limit = df_edges_weight_limit[['node_id_st', 'node_id_en', f_weight, 'w_start', 'w_end', 'w_mean', 'w_limit', 'geometry']]
                list_df_edges_weight_limit.append(df_edges_weight_limit)
            elif iso_type =='individual': 
                df_edges_weight_limit = calculate_individual_isochrone_edges(graph, gdf_edges, v_time_list_node_sources, f_weight, v_time, v_frac, v_time_factor)
                list_df_edges_weight_limit.append(df_edges_weight_limit)
            else:
                print("Parameter iso_type must be: 'merged' or 'individual'")
            
        df_edges_weight_limit_dis = pd.concat(list_df_edges_weight_limit)
        return df_edges_weight_limit_dis
    
    else:
        print("Parameter list_source_nodes must be: list or dataframe") """