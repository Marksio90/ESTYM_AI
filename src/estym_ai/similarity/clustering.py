"""Product family clustering using HDBSCAN.

Automatically discovers product families from historical data
without requiring a predefined number of clusters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import structlog

logger = structlog.get_logger()

try:
    from sklearn.cluster import HDBSCAN as SklearnHDBSCAN
    from sklearn.preprocessing import StandardScaler

    HAS_HDBSCAN = True
except ImportError:
    HAS_HDBSCAN = False


@dataclass
class ClusteringResult:
    """Result of product family clustering."""
    n_clusters: int = 0
    n_noise_points: int = 0
    labels: list[int] = field(default_factory=list)  # -1 = noise
    probabilities: list[float] = field(default_factory=list)
    cluster_sizes: dict[int, int] = field(default_factory=dict)
    cluster_centroids: dict[int, list[float]] = field(default_factory=dict)


def cluster_products(
    embeddings: np.ndarray,
    min_cluster_size: int = 5,
    min_samples: int = 3,
    metric: str = "euclidean",
) -> ClusteringResult:
    """
    Cluster products into families using HDBSCAN.

    HDBSCAN advantages:
    - No need to specify number of clusters
    - Detects noise/outliers (unique one-off products)
    - Returns membership probabilities

    Args:
        embeddings: (N, D) array of product embeddings.
        min_cluster_size: Minimum cluster size (smaller = more clusters).
        min_samples: Core point threshold (larger = more conservative).
        metric: Distance metric.

    Returns:
        ClusteringResult with labels and metadata.
    """
    if not HAS_HDBSCAN:
        logger.error("scikit-learn HDBSCAN not available (requires sklearn >= 1.3)")
        return ClusteringResult()

    result = ClusteringResult()

    if len(embeddings) < min_cluster_size:
        logger.warning("too_few_products_to_cluster", count=len(embeddings))
        result.labels = [-1] * len(embeddings)
        result.n_noise_points = len(embeddings)
        return result

    # Normalize features
    scaler = StandardScaler()
    scaled = scaler.fit_transform(embeddings)

    # Run HDBSCAN
    clusterer = SklearnHDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        store_centers="centroid",
    )
    clusterer.fit(scaled)

    labels = clusterer.labels_.tolist()
    probabilities = clusterer.probabilities_.tolist() if hasattr(clusterer, "probabilities_") else [1.0] * len(labels)

    result.labels = labels
    result.probabilities = probabilities
    result.n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    result.n_noise_points = labels.count(-1)

    # Cluster sizes
    for label in set(labels):
        if label >= 0:
            result.cluster_sizes[label] = labels.count(label)

    # Centroids
    if hasattr(clusterer, "centroids_") and clusterer.centroids_ is not None:
        for i, centroid in enumerate(clusterer.centroids_):
            result.cluster_centroids[i] = centroid.tolist()

    logger.info(
        "clustering_complete",
        n_products=len(embeddings),
        n_clusters=result.n_clusters,
        n_noise=result.n_noise_points,
        sizes=result.cluster_sizes,
    )

    return result


def find_nearest_cluster(
    query_embedding: np.ndarray,
    cluster_centroids: dict[int, list[float]],
) -> tuple[int, float]:
    """Find the nearest cluster for a new product."""
    best_cluster = -1
    best_distance = float("inf")

    for cluster_id, centroid in cluster_centroids.items():
        centroid_arr = np.array(centroid)
        distance = np.linalg.norm(query_embedding - centroid_arr)
        if distance < best_distance:
            best_distance = distance
            best_cluster = cluster_id

    return best_cluster, best_distance
