import pandas as pd
import geopandas as gpd

# create isochrone polygon a for a single weight limit
def create_isochrones_polygons(gdf_edges, v_buffer_meters, v_buffer_distance, f_dissolve='weight_limit'):
    weight_limit_value = list(gdf_edges[f_dissolve].unique())[0]
    v_buffer_distance_retract = (-0.99) * v_buffer_distance
    v_buffer_meters = v_buffer_meters - v_buffer_distance *0.01

    gdf_edges_buffer = gdf_edges.copy()
    gdf_edges_buffer.geometry = gdf_edges_buffer.buffer(v_buffer_distance) # , cap_style=2
    gdf_edges_buffer = gdf_edges_buffer.dissolve(by=f_dissolve).reset_index()

    gdf_edges_buffer.geometry = gdf_edges_buffer.buffer(v_buffer_distance_retract, cap_style=2)
    gdf_edges_buffer.geometry = gdf_edges_buffer.buffer(v_buffer_meters)

    gdf_edges_buffer[f_dissolve] = weight_limit_value
    gdf_edges_buffer = gdf_edges_buffer[[f_dissolve, 'geometry']]

    return gdf_edges_buffer  

def sort_isochrones_by_weight(list_gpd_service_areas, f_dissolve):
    gpd_all_areas = pd.concat(list_gpd_service_areas) 
    gpd_all_areas = gpd_all_areas.sort_values(f_dissolve, ascending=True).reset_index(drop=True)
    return gpd_all_areas

# merge isochrones of different weight limits, into polygons or rings by limit weight
def create_ring_isochrones( list_gpd_service_areas, f_dissolve):
    gpd_all_areas = sort_isochrones_by_weight(list_gpd_service_areas, f_dissolve)
    l_weight_list = list(gpd_all_areas[f_dissolve].sort_values(ascending=False))

    gpd_service_areas_result = gpd.GeoDataFrame([], columns=[f_dissolve, 'geometry'], geometry='geometry')

    for i in range(len(l_weight_list)-1):
        p_area_bigger = gpd_all_areas.loc[gpd_all_areas[f_dissolve] <= l_weight_list[i]]
        p_area_smaller = gpd_all_areas.loc[gpd_all_areas[f_dissolve] <= l_weight_list[i+1]]

        p_area_diff = p_area_bigger.overlay(p_area_smaller[['geometry']], how='difference') 
        p_area_diff = p_area_diff[[f_dissolve, 'geometry']] 
        gpd_service_areas_result = pd.concat([gpd_service_areas_result, p_area_diff])

    gpd_service_areas_result = pd.concat([gpd_service_areas_result, p_area_smaller])
    gpd_service_areas_result.reset_index(inplace=True, drop=True)

    return gpd_service_areas_result
