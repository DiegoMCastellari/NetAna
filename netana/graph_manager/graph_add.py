import numpy as np
from shapely.geometry import MultiPoint, LineString
from ..tools.calc_tools import nearest_edge_to_point_parameters, calculate_weight_to_node_of_nearest_edge

#************* INSERT ***************

def add_edges_list_to_graph(graph, list_edges_connections):
    graph.add_edges_from(list_edges_connections)
    return graph

# insert a source (as node) to a graph, from a point in a gdf (params gdf and id)
# get the nearest edge and conect the source to its nodes
# calculate the weight of the new edges (interpolation)
def insert_source_to_graph(gdf_points, point_id, graph, gdf_nodes, gdf_edges, mapping_nodes, f_weight, v_dist):

    gdf_point = gdf_points.loc[gdf_points.id == point_id]
    
    # update map
    gdf_point_node = (list(gdf_point.geometry)[0].x, list(gdf_point.geometry)[0].y)
    n_map_position = len(mapping_nodes['map_nodes'])
    mapping_nodes['map_nodes'][n_map_position] = [gdf_point_node, list(gdf_point.geometry)[0]]
    mapping_nodes['map_coords'][gdf_point_node] = [n_map_position, list(gdf_point.geometry)[0]]
    mapping_nodes['map_geom'][list(gdf_point.geometry)[0]] = [n_map_position, gdf_point_node]
    
    target_pt_1, target_pt_2, target_w, length_line = nearest_edge_to_point_parameters(gdf_point, gdf_edges, f_weight, v_dist)
    if sum([target_pt_1, target_pt_2, target_w, length_line]) != 0:
        w_1 = calculate_weight_to_node_of_nearest_edge(gdf_point, gdf_nodes, target_pt_1, length_line, target_w)
        w_2 = calculate_weight_to_node_of_nearest_edge(gdf_point, gdf_nodes, target_pt_2, length_line, target_w)

        edges_list = [
            (gdf_point_node, mapping_nodes['map_nodes'][target_pt_1][0], {f_weight: w_1, 'category':'loc', 'geometry':LineString([gdf_point_node, mapping_nodes['map_nodes'][target_pt_1][0]])}),
            (gdf_point_node, mapping_nodes['map_nodes'][target_pt_2][0], {f_weight: w_2, 'category':'loc', 'geometry':LineString([gdf_point_node, mapping_nodes['map_nodes'][target_pt_2][0]])}),
        ]
        
        graph.add_edges_from(edges_list)
        return [graph, mapping_nodes, 1]
    else:
        return [graph, mapping_nodes, 0]

def insert_poly_source_to_graph(gdf_sources, v_loc_id, graph, gdf_nodes, gdf_edges, d_mapping, f_cost, v_dist):
    
    sources_pt = gdf_sources.loc[[v_loc_id]]
    sources_pt.geometry = sources_pt.geometry.apply(lambda x: MultiPoint(list(x.exterior.coords)))
    sources_pt = sources_pt.explode(index_parts=True).reset_index(drop=True)
    sources_pt.id = sources_pt.index + 1
    sources_pt = sources_pt.iloc[:-1]

    v_conected_total = 0
    for i in list(sources_pt.id):
        G_updated, mapping_nodes_updated, v_conected = insert_source_to_graph(sources_pt, i, graph, gdf_nodes, gdf_edges, d_mapping, f_cost, v_dist)
        v_conected_total += v_conected

    # edges between polygon vertex
    list_coords = [(b[0], b[1]) for b in np.dstack(gdf_sources.loc[0, 'geometry'].boundary.coords.xy)[0][:-1]]
    start_node = list_coords[0]
    edges_list = []
    for end_node in list_coords[1:]:
        edges_list.append((start_node, end_node, {f_cost: 0, 'category':'loc', 'geometry':LineString([start_node, end_node])}))
    G_updated.add_edges_from(edges_list)

    return [G_updated, mapping_nodes_updated, v_conected_total]