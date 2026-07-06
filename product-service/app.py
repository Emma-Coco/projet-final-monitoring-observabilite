"""Product Service.

Backend catalog service called by Order Service. It exposes the product
list with a simulated 200ms processing delay, so the distributed trace
visible in Jaeger shows a realistic latency for the downstream call.

This module wires together the three observability pillars:
  - metrics.py   -> Prometheus counters/histogram, exposed on /metrics
  - logger.py    -> structured JSON logs, written to logs/product.log
  - telemetry.py -> OpenTelemetry tracing, exported to the OTel Collector
"""
import time

from flask import Flask, Response, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from logger import setup_logger
from metrics import create_metrics
from telemetry import setup_telemetry

SERVICE_NAME = "product-service"
PRODUCTS = ["Laptop", "Mouse", "Keyboard"]

app = Flask(__name__)

# Observability wiring, done once at startup.
tracer = setup_telemetry(app, SERVICE_NAME)
logger = setup_logger(SERVICE_NAME, "logs/product.log")
REQUEST_COUNT, REQUEST_DURATION, ERROR_COUNT = create_metrics("product")


@app.route("/")
def home():
    """Simple identification route."""
    return jsonify({"service": "Product Service"})


@app.route("/metrics")
def metrics():
    """Exposes metrics in the Prometheus text format for scraping."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/products")
def products():
    """Returns the product catalog after a simulated 200ms lookup."""
    method = "GET"
    endpoint = "/products"
    start_time = time.time()

    try:
        logger.info("Products requested")

        # Simulate a database/catalog lookup.
        time.sleep(0.2)

        logger.info("Products returned")

        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, http_status=200
        ).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(
            time.time() - start_time
        )

        return jsonify(PRODUCTS)

    except Exception as exc:  # pragma: no cover - defensive safety net
        logger.error(f"Failed to fetch products: {exc}")

        ERROR_COUNT.labels(method=method, endpoint=endpoint).inc()
        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, http_status=500
        ).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(
            time.time() - start_time
        )

        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
