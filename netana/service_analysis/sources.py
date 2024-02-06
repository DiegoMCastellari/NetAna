import pandas as pd
import geopandas as gpd
from shapely.ops import nearest_points
from shapely.geometry import MultiPoint, Point, LineString

# create a clean sources gdf
def create_sources_from_gdf(gdf_sources, v_crs_proj):
    
    gdf_sources = gdf_sources.to_crs(v_crs_proj)
    gdf_sources = gdf_sources.explode(index_parts=True).reset_index(drop=True)
    gdf_sources['id'] = list(gdf_sources.index)
    gdf_sources['id'] = gdf_sources.apply(lambda row: "loc_"+str(row.id), axis=1) 

    return gdf_sources

# return id of graph's nodes near sources, by buffer distance
def search_node_near_to_sources (gdf_sources, gdf_nodes, search_radio):
    nodes_in = gdf_nodes.sjoin(gpd.GeoDataFrame(geometry=gdf_sources.buffer(search_radio)))
    nodes_in = nodes_in.drop_duplicates(subset='node_id').reset_index(drop=True)
    node_list = list(nodes_in.node_id)

    return node_list

# return new edges to add to the graph, and the sources id 
def create_sources_edges_and_nodes (gdf_network, gdf_sources, dict_mapping_nodes, search_radio):

    lista_nodes_all = []
    lista_edges_all = []

    # nodes and edges from the source
    gdf_loc_points = gdf_sources.copy()
    gdf_loc_points.geometry = gdf_sources.geometry.apply(lambda x: MultiPoint(list(x.exterior.coords)))
    gdf_loc_points = gdf_loc_points.explode(index_parts=False).reset_index(drop=True).reset_index()
    gdf_loc_points.drop_duplicates(subset='geometry', inplace=True)
    gdf_loc_points['node_id'] = gdf_loc_points['id'] +"_"+ gdf_loc_points['index'].astype(str)
    gdf_loc_points['coords'] = gdf_loc_points.apply(lambda row: row.geometry.coords[0], axis=1)

    list_loc_nodes = list(gdf_loc_points.apply(lambda row: (row.node_id, {'coords':row.coords}) , axis=1))

    gdf_loc_lines = pd.DataFrame(gdf_loc_points.groupby('id')['node_id'].apply(list).reset_index()).merge(pd.DataFrame(gdf_loc_points.groupby('id')['geometry'].apply(list).reset_index()), on='id')
    lista_linestrings = []
    gdf_loc_lines.apply(lambda row: lista_linestrings.extend([[row.id, row.node_id[0], row.node_id[x], LineString([row.geometry[0], row.geometry[x]]), 0] for x in range(1, len(row.geometry))]) , axis=1)
    lista_linestrings = gpd.GeoDataFrame(lista_linestrings, columns=['loc', 'node_st', 'node_en', 'geometry', 'w'], geometry='geometry')
    list_loc_edges = list(lista_linestrings.apply(lambda row: (row.node_st, row.node_en, {'weight':row.w, 'label':'loc', 'geometry': row.geometry}) , axis=1))

    lista_nodes_all.extend(list_loc_nodes)
    lista_edges_all.extend(list_loc_edges)

    # nodes and edges from nearest point of network to the source
    df = gpd.sjoin_nearest(gdf_loc_points, gdf_network[['id', 'geometry']].rename(columns={'id':'id_line'}))
    df = df.merge(gdf_network.rename(columns={'id':'id_line', 'geometry':'geometry_line'}), on='id_line', how='left')
    df = df[['id', 'geometry', 'node_id', 'coords', 'index_right', 'id_line', 'len_m', 'weight', 'geometry_line']]

    df['near_pt'] = df.apply(lambda row: nearest_points(row.geometry, row.geometry_line)[1], axis=1)
    df['coords_near'] = df.apply(lambda row: row.near_pt.coords[0], axis=1)
    df['len_near'] = df.apply(lambda row: row.near_pt.distance(row.geometry), axis=1)
    df = df.loc[df.len_near <= search_radio]

    sources_list = list(df.drop_duplicates(subset='id')['node_id'])

    df['len_m_A'] = df.apply(lambda row: row.near_pt.distance(Point(row.geometry_line.coords[0])), axis=1)
    df['len_m_B'] = df.apply(lambda row: row.near_pt.distance(Point(row.geometry_line.coords[-1])), axis=1)
    df['len_total'] = df['len_m_A'] + df['len_m_B']
    df['weight_A'] = df['weight'] * df['len_m_A'] / df['len_total']
    df['weight_B'] = df['weight'] * df['len_m_B'] / df['len_total']

    lista_nodes_near = list(df.apply(lambda row: (row.node_id+"_near", {'coords':row.coords_near}) , axis=1))
    lista_edges_near = list(df.apply(lambda row: (row.node_id, row.node_id+"_near", {'weight':0, 'label':'loc', 'geometry': LineString([row.geometry, Point(row.coords_near)])}) , axis=1))

    lista_nodes_all.extend(lista_nodes_near)
    lista_edges_all.extend(lista_edges_near)

    # edges from nearest point of network to the nodes of network
    lista_edges_con_A = list(df.apply(lambda row: (row.node_id+"_near", dict_mapping_nodes['map_geom'][Point(row.geometry_line.coords[0])], 
                    {'weight':row.weight_A, 'label':'loc', 'geometry': LineString([row.near_pt, Point(row.geometry_line.coords[0])])}) , axis=1))
    lista_edges_con_B = list(df.apply(lambda row: (row.node_id+"_near", dict_mapping_nodes['map_geom'][Point(row.geometry_line.coords[-1])], 
                    {'weight':row.weight_B, 'label':'loc', 'geometry': LineString([row.near_pt, Point(row.geometry_line.coords[-1])])}) , axis=1))

    lista_edges_all.extend(lista_edges_con_A)
    lista_edges_all.extend(lista_edges_con_B)

    return [lista_nodes_all, lista_edges_all, sources_list]

def add_sources_to_graph(graph, list_nodes, list_edges):
    graph.add_nodes_from(list_nodes)
    graph.add_edges_from(list_edges)

    return graph

def sources_to_graph(graph, gdf_network, gdf_sources, dict_mapping_nodes, search_radio):
    lista_nodes_all, lista_edges_all, sources_list = create_sources_edges_and_nodes (gdf_network, gdf_sources, dict_mapping_nodes, search_radio)
    graph = add_sources_to_graph(graph, lista_nodes_all, lista_edges_all)
    return [graph, sources_list]