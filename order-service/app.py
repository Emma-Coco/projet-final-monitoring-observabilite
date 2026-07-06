"""Order Service.

Entry point of the mini e-commerce demo: a client (Postman) sends a
POST /order request here, this service logs the steps of the order,
calls Product Service over HTTP to fetch the catalog, simulates some
business processing, and returns a success response.

This module wires together the three observability pillars:
  - metrics.py   -> Prometheus counters/histogram, exposed on /metrics
  - logger.py    -> structured JSON logs, written to logs/order.log
  - telemetry.py -> OpenTelemetry tracing, exported to the OTel Collector
"""
import time

from flask import Flask, Response, jsonify
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
import requests

from logger import setup_logger
from metrics import create_metrics
from telemetry import setup_telemetry

SERVICE_NAME = "order-service"
PRODUCT_SERVICE_URL = "http://product-service:5001/products"

app = Flask(__name__)

# Observability wiring, done once at startup.
tracer = setup_telemetry(app, SERVICE_NAME)
logger = setup_logger(SERVICE_NAME, "logs/order.log")
REQUEST_COUNT, REQUEST_DURATION, ERROR_COUNT = create_metrics("order")


@app.route("/")
def home():
    """Simple identification route."""
    return jsonify({"service": "Order Service"})


@app.route("/metrics")
def metrics():
    """Exposes metrics in the Prometheus text format for scraping."""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


@app.route("/order", methods=["POST"])
def create_order():
    """Handles a new order: fetches the product catalog and confirms it.

    This is the route that produces the distributed trace shown in Jaeger:
    the incoming POST /order server span, followed by a client span for the
    outgoing "GET /products" call to Product Service.
    """
    method = "POST"
    endpoint = "/order"
    start_time = time.time()

    logger.info("New order received")

    try:
        logger.info("Calling Product Service")
        response = requests.get(PRODUCT_SERVICE_URL, timeout=5)
        response.raise_for_status()
        products = response.json()
        logger.info("Product found")

        # Simulate additional order processing (payment, stock update, ...).
        time.sleep(0.1)

        logger.info("Order completed")

        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, http_status=200
        ).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(
            time.time() - start_time
        )

        return jsonify({"status": "success", "products": products})

    except requests.exceptions.RequestException as exc:
        logger.error(f"Order failed: {exc}")

        ERROR_COUNT.labels(method=method, endpoint=endpoint).inc()
        REQUEST_COUNT.labels(
            method=method, endpoint=endpoint, http_status=500
        ).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(
            time.time() - start_time
        )

        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
