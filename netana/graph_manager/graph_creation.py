import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

import networkx as nx

#************* CREATE ***************

# create nodes and edges datasets
def create_nodes_and_edges_gdf(gpd_lines):
    # create lines
    # get starting and ending points
    gpd_lines['nd_st_coords'] = gpd_lines.apply(lambda row: Point(row.geometry.coords[0]), axis=1)
    gpd_lines['nd_en_coords'] = gpd_lines.apply(lambda row: Point(row.geometry.coords[-1]), axis=1)

    # create points from lines
    # list all unique points from lines
    points_list = list(gpd_lines.nd_st_coords.unique()) + list(gpd_lines.nd_en_coords.unique())
    points_list = set(points_list)

    # create a point dataset
    gdf_points = pd.DataFrame(points_list, columns=['geometry'])
    gdf_points['node_id'] = "n_"+ (gdf_points.index+1).astype(str)
    gdf_points = gdf_points[['node_id', 'geometry']]

    # add points ids to lines dataset
    gpd_lines['nd_st'] = gpd_lines.apply(lambda row: list(gdf_points.loc[gdf_points.geometry == row.nd_st_coords, 'node_id'])[0], axis=1)
    gpd_lines['nd_en'] = gpd_lines.apply(lambda row: list(gdf_points.loc[gdf_points.geometry == row.nd_en_coords, 'node_id'])[0], axis=1)
    gpd_lines = gpd_lines[['id', 'nd_st', 'nd_en', 'weight', 'geometry']]

    return [gdf_points, gpd_lines]

# create graph, point, edges and mapping dict. from gdf
def graph_from_gdf(gdf_network, f_weight='weight', v_label=None, v_make_directed=False, v_directed=False, remove_isolated=False, remove_selfloop=False):

    gdf_nodes, gdf_edges = create_nodes_and_edges_gdf(gdf_network)
    gdf_nodes = gpd.GeoDataFrame(gdf_nodes)
    gdf_edges = gpd.GeoDataFrame(gdf_edges)
    gdf_nodes.crs = gdf_network.crs
    gdf_edges.crs = gdf_network.crs

    edgelist = list(gdf_edges.apply(lambda row: ( row.nd_st, row.nd_en, {'id':row.id, 'weight': row.weight}), axis=1))
    graph = nx.from_edgelist(edgelist)

    if remove_isolated == True:
        graph.remove_nodes_from(list(nx.isolates(graph)))
    if remove_selfloop == True:
        graph.remove_edges_from(nx.selfloop_edges(graph))

    if v_make_directed == True:
        graph = graph.to_directed(as_view=False)
    
    return [graph, gdf_nodes, gdf_edges]