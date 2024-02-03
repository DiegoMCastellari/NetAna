import momepy
nodes, edges, sw = momepy.nx_to_gdf(graph, points=True, lines=True, spatial_weights=True)