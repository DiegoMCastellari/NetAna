import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

def crearte_grid(gdf_nodes, v_length, v_wide):
    xmin, ymin, xmax, ymax = gdf_nodes.total_bounds

    length = v_length
    wide = v_wide

    cols = list(np.arange(xmin, xmax + wide, wide))
    rows = list(np.arange(ymin, ymax + length, length))
    print(f"Grid size: {len(cols) * len(rows)} cells")

    polygons = []
    for x in cols[:-1]:
        for y in rows[:-1]:
            polygons.append(Polygon([(x,y), (x+wide, y), (x+wide, y+length), (x, y+length)]))

    grid_poly = gpd.GeoDataFrame({'geometry':polygons})
    grid_poly.crs = gdf_nodes.crs
    grid_poly['pol_id'] = grid_poly.index +1

    return grid_poly

def find_closest_node_to_centroid_of_grid(gdf_nodes, gdf_grid_poly, mapping_nodes):
    grid = gdf_grid_poly.copy()
    grid.geometry = grid.centroid
    mesh_nodes_ids = gpd.sjoin_nearest(grid, gdf_nodes)

    mesh_nodes_coords = []
    mesh_nodes_gdf = gpd.GeoDataFrame([])
    for x in list(mesh_nodes_ids.nodeID.unique()):

        append_node = True
        try:
            mesh_nodes_coords.append(mapping_nodes['map_nodes'][x][0])
        except:
            append_node = False

        if append_node:
            nodes_filtered = gdf_nodes.loc[gdf_nodes.nodeID == x]
            if len(mesh_nodes_gdf) == 0:
                mesh_nodes_gdf = nodes_filtered
            else:
                mesh_nodes_gdf = pd.concat([mesh_nodes_gdf, nodes_filtered])

    mesh_nodes_gdf['coords'] = mesh_nodes_gdf['coords'].astype(str)
    print(f"Nodes: {len(mesh_nodes_coords)}")

    return mesh_nodes_coords, mesh_nodes_gdf

def find_grid_central_nodes(gdf_nodes, v_length, v_wide, mapping_nodes):
    gdf_grid_poly = crearte_grid(gdf_nodes, v_length, v_wide)
    grid_nodes_coords, grid_nodes_gdf = find_closest_node_to_centroid_of_grid(gdf_nodes, gdf_grid_poly, mapping_nodes)
    return grid_nodes_coords, grid_nodes_gdf, gdf_grid_poly