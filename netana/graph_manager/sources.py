import pandas as pd
import geopandas as gpd
from shapely.ops import nearest_points
from shapely.geometry import MultiPoint, Point, LineString
import networkx as nx

# create a clean sources gdf
def create_sources(gdf_sources, v_crs_proj, v_label=None):
    gdf_sources_2 = gdf_sources.to_crs(v_crs_proj)
    
    if 'id' not in gdf_sources_2.columns:
        gdf_sources_2.loc[:,'id'] = list(gdf_sources_2.index)
        gdf_sources_2.loc[:,'id'] = gdf_sources_2.apply(lambda row: "loc_"+str(row.id), axis=1) 

    gdf_sources_2 = gdf_sources_2[['id', 'geometry']]

    if v_label:
        gdf_sources_2.loc[:,'label'] = v_label
        gdf_sources_2 = gdf_sources_2.loc[:,['id', 'label', 'geometry']]
        
    return gdf_sources_2

# Find the nearest network node to each source
def find_closest_node_to_source(gdf_sources, gdf_nodes):
    gdf_amenities = gpd.sjoin_nearest(gdf_sources, gdf_nodes, how='inner')
    if 'label' in list(gdf_sources.columns):
        gdf_amenities = gdf_amenities.loc[:,['id', 'label', 'node_id', 'geometry']]
    else:
        gdf_amenities = gdf_amenities.loc[:,['id', 'node_id', 'geometry']]
    return gdf_amenities



# return new edges to add to the graph
def create_sources_edges_and_nodes (gdf_edges, gdf_sources, search_radio):

    gdf_sources.loc[:,'node_id'] = gdf_sources.loc[:,'id'].astype(str) +"_cen"

    edges_lists = []
    if gdf_sources.geom_type[0] == 'Polygon':
        # creates the location's nodes
        gdf_loc_centroid = gdf_sources.copy()
        gdf_loc_centroid.geometry = gdf_sources.centroid
        gdf_loc_centroid.loc[:,'pt_cat'] = 'cen'

        gdf_loc_exterior = gdf_sources.copy()
        gdf_loc_exterior.geometry = gdf_loc_exterior.loc[:,'geometry'].apply(lambda x: MultiPoint(list(x.exterior.coords)))
        gdf_loc_exterior = gdf_loc_exterior.explode(index_parts=False).reset_index(drop=True).reset_index()
        gdf_loc_exterior = gdf_loc_exterior.drop_duplicates(subset='geometry').reset_index(drop=True)
        gdf_loc_exterior.reset_index(drop=True, inplace=True)
        gdf_loc_exterior.loc[:,'pt_cat'] = 'vertex'
        gdf_loc_exterior.loc[:,'node_id'] = gdf_loc_exterior.loc[:,'id'].astype(str) +"_v"+ gdf_loc_exterior['index'].astype(str)

        gdf_loc_points = pd.concat([gdf_loc_centroid, gdf_loc_exterior])

        # create the location's edges
        gdf_loc_edges = gdf_loc_points.loc[gdf_loc_points.pt_cat=='vertex', ['node_id', 'pt_cat']].copy()
        gdf_loc_edges.loc[:,'id'] = "le_"+ (gdf_loc_edges.index+1).astype(str)
        gdf_loc_edges.loc[:,'nd_st'] = gdf_loc_points.loc[gdf_loc_points.pt_cat=='vertex'].apply(lambda row: list(gdf_loc_points.loc[gdf_loc_points.id ==  row.id, 'node_id'])[0], axis=1)
        gdf_loc_edges.loc[:,'nd_en'] = gdf_loc_points.loc[gdf_loc_points.pt_cat=='vertex', 'node_id']
        gdf_loc_edges.loc[:,'weight'] = 0
        gdf_loc_edges.loc[:,'geometry'] = gdf_loc_edges.apply(lambda row: LineString([list(gdf_loc_points.loc[gdf_loc_points.node_id == row.nd_st, 'geometry'])[0], 
                                                    list(gdf_loc_points.loc[gdf_loc_points.node_id == row.nd_en, 'geometry'])[0]]), 
                                                    axis=1)
        gdf_loc_edges = gpd.GeoDataFrame(gdf_loc_edges, geometry='geometry')
        gdf_loc_edges.crs = gdf_sources.crs
        gdf_loc_edges = gdf_loc_edges.loc[:,['id', 'nd_st', 'nd_en', 'weight', 'geometry']]
        edges_lists.append(gdf_loc_edges)

        gdf_loc_points_cen = gdf_loc_points.loc[gdf_loc_points.pt_cat!='vertex']
        gdf_loc_points = gdf_loc_points.loc[gdf_loc_points.pt_cat=='vertex']

    # If only points, start from here
    gdf_loc_points_2 = gpd.sjoin_nearest(gdf_loc_points, gdf_edges.loc[:,['id', 'geometry']].rename(columns={'id':'id_line'}))
    gdf_loc_points_2 = gdf_loc_points_2.merge(gdf_edges.rename(columns={'id':'id_line', 'geometry':'geometry_line'}), on='id_line', how='left')
    gdf_loc_points_2.loc[:,'near_pt'] = gdf_loc_points_2.apply(lambda row: nearest_points(row.geometry, row.geometry_line)[1], axis=1)
    gdf_loc_points_2.loc[:,'near_len'] = gdf_loc_points_2.apply(lambda row: row.near_pt.distance(row.geometry), axis=1)
    gdf_loc_points_3 = gdf_loc_points_2.loc[gdf_loc_points_2.near_len <= search_radio]

    # create the location's edges
    gdf_loc_edges_2 = gdf_loc_points_3.copy()
    gdf_loc_edges_2.loc[:,'id'] = "ce_"+ (gdf_loc_edges_2.index+1).astype(str)
    gdf_loc_edges_2.loc[:,'nd_st'] = gdf_loc_edges_2.loc[:,'node_id']
    gdf_loc_edges_2.loc[:,'nd_en'] = gdf_loc_edges_2.loc[:,'node_id']+"_cp"
    gdf_loc_edges_2.loc[:,'weight'] = 0
    gdf_loc_edges_2.loc[:,'geometry'] = gdf_loc_edges_2.apply(lambda row: LineString([row.geometry, row.near_pt]), axis=1)                                   
    gdf_loc_edges_2 = gpd.GeoDataFrame(gdf_loc_edges_2, geometry='geometry')
    gdf_loc_edges_2.crs = gdf_loc_points_3.crs
    gdf_loc_edges_2 = gdf_loc_edges_2.loc[:,['id', 'nd_st', 'nd_en', 'weight', 'geometry']]
    edges_lists.append(gdf_loc_edges_2)

    gdf_loc_points_3.loc[:,'len_m_A'] = gdf_loc_points_3.apply(lambda row: row.near_pt.distance(Point(row.geometry_line.coords[0])), axis=1)
    gdf_loc_points_3.loc[:,'len_m_B'] = gdf_loc_points_3.apply(lambda row: row.near_pt.distance(Point(row.geometry_line.coords[-1])), axis=1)
    gdf_loc_points_3.loc[:,'len_total'] = gdf_loc_points_3.loc[:,'len_m_A'] + gdf_loc_points_3.loc[:,'len_m_B']
    gdf_loc_points_3.loc[:,'weight_A'] = gdf_loc_points_3.loc[:,'weight'] * gdf_loc_points_3.loc[:,'len_m_A'] / gdf_loc_points_3.loc[:,'len_total']
    gdf_loc_points_3.loc[:,'weight_B'] = gdf_loc_points_3.loc[:,'weight'] * gdf_loc_points_3.loc[:,'len_m_B'] / gdf_loc_points_3.loc[:,'len_total']

    # create the location's edges
    gdf_loc_edges_3_A = gdf_loc_points_3.copy()
    gdf_loc_edges_3_A.loc[:,'id'] = "cwe_"+ (gdf_loc_edges_3_A.index+1).astype(str)
    gdf_loc_edges_3_A.loc[:,'nd_en'] = gdf_loc_edges_3_A.loc[:,'nd_st']
    gdf_loc_edges_3_A.loc[:,'nd_st'] = gdf_loc_edges_3_A.loc[:,'node_id']+"_cp"
    gdf_loc_edges_3_A.loc[:,'weight'] = gdf_loc_edges_3_A.loc[:,'weight_A']
    gdf_loc_edges_3_A.loc[:,'geometry'] = gdf_loc_edges_3_A.apply(lambda row: LineString([row.near_pt, row.geometry_line.coords[0]]), axis=1)                              
    gdf_loc_edges_3_A = gpd.GeoDataFrame(gdf_loc_edges_3_A, geometry='geometry')
    gdf_loc_edges_3_A.crs = gdf_loc_edges_3_A.crs
    gdf_loc_edges_3_A = gdf_loc_edges_3_A.loc[:,['id', 'nd_st', 'nd_en', 'weight', 'geometry']]
    edges_lists.append(gdf_loc_edges_3_A)

    # create the location's edges
    gdf_loc_edges_3_B = gdf_loc_points_3.copy()
    gdf_loc_edges_3_B.loc[:,'id'] = "cwe_"+ (gdf_loc_edges_3_B.index+1).astype(str)
    gdf_loc_edges_3_B.loc[:,'nd_st'] = gdf_loc_edges_3_B.loc[:,'node_id']+"_cp"
    gdf_loc_edges_3_B.loc[:,'nd_en'] = gdf_loc_edges_3_B.loc[:,'nd_en']
    gdf_loc_edges_3_B.loc[:,'weight'] = gdf_loc_edges_3_B.loc[:,'weight_B']
    gdf_loc_edges_3_B.loc[:,'geometry'] = gdf_loc_edges_3_B.apply(lambda row: LineString([row.near_pt, row.geometry_line.coords[1]]), axis=1)                                
    gdf_loc_edges_3_B = gpd.GeoDataFrame(gdf_loc_edges_3_B, geometry='geometry')
    gdf_loc_edges_3_B.crs = gdf_loc_edges_3_B.crs
    gdf_loc_edges_3_B = gdf_loc_edges_3_B.loc[:,['id', 'nd_st', 'nd_en', 'weight', 'geometry']]
    edges_lists.append(gdf_loc_edges_3_B)

    gdf_loc_edges_merged = pd.concat(edges_lists)
    return [gdf_loc_edges_merged, gdf_sources]   

# add the new source´s edges to the graph
def add_sources_edges_to_graph(graph, gdf_edges, gdf_nodes, gdf_loc_edges_merged):
    gdf_edges_sources = pd.concat([gdf_edges, gdf_loc_edges_merged])

    gdf_loc_edges_merged['geom_nd_st'] = gdf_loc_edges_merged.apply(lambda row: Point(row.geometry.coords[0]), axis=1)
    gdf_loc_edges_merged['geom_nd_en'] = gdf_loc_edges_merged.apply(lambda row: Point(row.geometry.coords[1]), axis=1)
    gdf_nodes_sources = pd.concat([gdf_loc_edges_merged[['nd_st', 'geom_nd_st']].rename(columns={'nd_st':'node_id', 'geom_nd_st':'geometry'}), 
            gdf_loc_edges_merged[['nd_en', 'geom_nd_en']].rename(columns={'nd_en':'node_id', 'geom_nd_en':'geometry'})])
    gdf_nodes_sources = gdf_nodes_sources.drop_duplicates(subset='node_id').reset_index(drop=True)
    gdf_nodes_sources.reset_index(inplace=True, drop=True)
    gdf_nodes_sources = pd.concat([gdf_nodes, gdf_nodes_sources])

    edgelist_loc = list(gdf_loc_edges_merged.apply(lambda row: ( row.nd_st, row.nd_en, {'id':row.id, 'weight': row.weight}), axis=1))
    graph_loc = nx.DiGraph(edgelist_loc)
    if nx.is_directed(graph):
        graph_sources = nx.compose(graph, graph_loc)
    else:
        di_graph = graph.to_directed()
        graph_sources = nx.compose(di_graph, graph_loc)

    return [graph_sources, gdf_edges_sources, gdf_nodes_sources]

# creates a new graph, with source´s edges
def sources_to_graph(graph, gdf_edges, gdf_nodes, gdf_sources, search_radio):
    gdf_loc_edges_merged, gdf_sources = create_sources_edges_and_nodes (gdf_edges, gdf_sources, search_radio)
    graph_sources, gdf_edges_sources, gdf_nodes_sources = add_sources_edges_to_graph(graph, gdf_edges, gdf_nodes, gdf_loc_edges_merged)
    return [graph_sources, gdf_edges_sources, gdf_nodes_sources, gdf_sources]