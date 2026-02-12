"""Product similarity search and family clustering."""

from .clustering import ClusteringResult, cluster_products, find_nearest_cluster
from .embeddings import compute_weighted_similarity, generate_feature_embedding, generate_text_embedding
