"""Prometheus metrics definitions for Product Service.

Exposes the three metric types required by the observability project:
  - a Counter for the total number of requests handled
  - a Histogram for request duration (also gives us count/sum for averages,
    and buckets for the histogram/heatmap panel in Grafana)
  - a Counter for errors encountered while handling requests
"""
from prometheus_client import Counter, Histogram


def create_metrics(service_prefix: str):
    """Creates and registers the Prometheus metrics for a service.

    Args:
        service_prefix: short name prepended to each metric, e.g. "product".

    Returns:
        A tuple (request_count, request_duration, error_count).
    """
    request_count = Counter(
        f"{service_prefix}_requests_total",
        "Total number of HTTP requests received",
        ["method", "endpoint", "http_status"],
    )

    request_duration = Histogram(
        f"{service_prefix}_request_duration_seconds",
        "Duration of HTTP requests in seconds",
        ["method", "endpoint"],
    )

    error_count = Counter(
        f"{service_prefix}_errors_total",
        "Total number of errors encountered while handling requests",
        ["method", "endpoint"],
    )

    return request_count, request_duration, error_count
