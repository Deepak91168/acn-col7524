
import networkx as nx

# Create an undirected graph of our switches
G = nx.Graph()

# Add switch-to-switch links with delays (ms)
G.add_edge(1, 2, weight=20)
G.add_edge(2, 3, weight=10)
G.add_edge(3, 4, weight=20)
G.add_edge(4, 1, weight=15)

# Find the shortest path from s1 to s3
path = nx.shortest_path(G, source=1, target=3, weight="weight")

cost = nx.shortest_path_length(G, source=1, target=3, weight="weight")

print("Selected path:", path)
print("Total delay:", cost, "ms")
