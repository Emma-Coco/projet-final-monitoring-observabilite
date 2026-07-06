# Monitoring & Observabilité — Mini E-commerce

Projet de démonstration Cloud-Native pour le module **Monitoring &
Observabilité**. Deux microservices Flask (Order Service, Product Service)
entièrement instrumentés avec les **trois piliers de l'observabilité** :

- **Métriques** → Prometheus → Grafana
- **Logs structurés** → Promtail → Loki → Grafana
- **Traces distribuées** → OpenTelemetry Collector → Jaeger

Tout tourne en local avec Docker Compose, sans Kubernetes et sans AWS.

## Architecture

```
               Client (Postman / curl)
                         │
                   POST /order
                         │
                         ▼
                  Order Service (5000)
                         │
                  GET /products
                         │
                         ▼
                 Product Service (5001)

      Metrics            Logs              Traces
        │                  │                  │
        ▼                  ▼                  ▼
   Prometheus            Promtail      OTel Collector
   (scrape /metrics)   (tail logs/*.log)  (OTLP gRPC/HTTP)
        │                  │                  │
        │                  ▼                  ▼
        │                Loki              Jaeger
        │                  │
        └────────┬─────────┘
                  ▼
               Grafana
      (dashboards: Application Overview, Logs)
```

Quand le client appelle `POST /order`, Order Service journalise chaque
étape, appelle `Product Service` en HTTP, et les deux appels (serveur +
client) sont capturés comme une **trace distribuée unique** visible dans
Jaeger.

## Arborescence du projet

```
monitoring-observability/
├── docker-compose.yml
├── README.md
├── order-service/
│   ├── app.py           # routes Flask (/, /order, /metrics)
│   ├── telemetry.py      # setup OpenTelemetry (tracer + auto-instrumentation)
│   ├── logger.py         # logs JSON structurés -> logs/order.log
│   ├── metrics.py         # métriques Prometheus (Counter, Histogram)
│   ├── Dockerfile
│   └── requirements.txt
├── product-service/
│   ├── app.py           # routes Flask (/, /products, /metrics)
│   ├── telemetry.py
│   ├── logger.py         # -> logs/product.log
│   ├── metrics.py
│   ├── Dockerfile
│   └── requirements.txt
├── prometheus/
│   └── prometheus.yml    # scrape order-service & product-service toutes les 5s
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yml  # Prometheus + Loki auto-provisionnés
│   │   └── dashboards/dashboards.yml    # provider qui charge les dashboards JSON
│   └── dashboards/
│       ├── application-overview.json    # dashboard "Application Overview"
│       └── logs.json                    # dashboard "Logs"
├── loki/
│   └── local-config.yaml
├── promtail/
│   └── config.yml        # tail logs/*.log -> push vers Loki
├── otel/
│   └── collector-config.yaml  # OTLP -> Jaeger
└── logs/                 # logs générés au runtime (order.log, product.log)
```

## Prérequis

- Docker et Docker Compose (v2, la commande `docker compose` sans tiret).
- Ports libres sur la machine hôte : `5050, 5001, 9090, 3000, 3100, 16686,
  4317, 4318`.

> **Note macOS** : Order Service est exposé sur le port hôte **5050** (et
> non 5000) car macOS réserve le port 5000 pour ControlCenter (AirPlay
> Receiver). Le conteneur écoute toujours en interne sur le port 5000
> (`order-service:5000` sur le réseau Docker), seul le port publié côté hôte
> change. Si vous désactivez AirPlay Receiver (Réglages Système > Général >
> AirDrop et Handoff), vous pouvez remapper `"5000:5000"` dans
> `docker-compose.yml`.

## Installation & lancement

Depuis la racine du projet :

```bash
docker compose up --build
```

Cette commande construit les images `order-service` et `product-service`
puis démarre les 8 conteneurs suivants :

| Conteneur         | Rôle                                   |
|-------------------|-----------------------------------------|
| `order-service`   | API métier, point d'entrée du client    |
| `product-service` | Catalogue produit                       |
| `prometheus`      | Collecte des métriques                  |
| `grafana`         | Visualisation (dashboards)               |
| `loki`            | Stockage des logs                        |
| `promtail`        | Collecte des logs et envoi vers Loki     |
| `otel-collector`  | Réception/forward des traces OpenTelemetry |
| `jaeger`          | Visualisation des traces distribuées     |

Attendez de voir dans les logs que les 8 services sont démarrés (~15-20
secondes), puis passez aux tests ci-dessous.

Pour arrêter le projet :

```bash
docker compose down
```

## URLs utiles

| Service            | URL                              | Description                          |
|---------------------|-----------------------------------|---------------------------------------|
| Order Service       | http://localhost:5050            | `GET /`, `POST /order`, `GET /metrics` |
| Product Service     | http://localhost:5001            | `GET /`, `GET /products`, `GET /metrics` |
| Prometheus          | http://localhost:9090            | UI Prometheus (Status > Targets)      |
| Grafana             | http://localhost:3000            | Dashboards (accès anonyme, rôle Admin) |
| Jaeger UI           | http://localhost:16686           | Recherche et visualisation des traces |

Grafana est configuré en accès anonyme (`GF_AUTH_ANONYMOUS_ENABLED=true`),
aucune connexion n'est nécessaire.

## Comment tester

### 1. Vérifier que les services répondent

```bash
curl http://localhost:5050/
# {"service":"Order Service"}

curl http://localhost:5001/
# {"service":"Product Service"}

curl http://localhost:5001/products
# ["Laptop","Mouse","Keyboard"]
```

### 2. Déclencher une commande (le scénario principal)

Avec curl :

```bash
curl -X POST http://localhost:5050/order
# {"status":"success","products":["Laptop","Mouse","Keyboard"]}
```

Avec Postman : créez une requête `POST http://localhost:5050/order` (pas de
body nécessaire) et envoyez-la. Répétez l'appel une dizaine de fois pour
peupler les dashboards Grafana.

### 3. Observer les métriques (Prometheus)

- Ouvrez http://localhost:9090/targets : `order-service` et
  `product-service` doivent apparaître `UP`.
- Testez une requête PromQL, par exemple `order_requests_total` ou
  `rate(product_requests_total[1m])`.
- Chaque service expose directement ses métriques brutes sur
  `/metrics` (`curl http://localhost:5050/metrics`).

### 4. Observer les dashboards (Grafana)

Ouvrez http://localhost:3000 :

- **Application Overview** : nombre total de requêtes par service, taux de
  requêtes par seconde, temps de réponse moyen, histogramme de durée, et
  durée maximale observée.
- **Logs** : logs structurés d'Order Service et de Product Service en temps
  réel (source Loki), avec un panneau combiné pour les deux services.

### 5. Observer la trace distribuée (Jaeger)

1. Ouvrez http://localhost:16686.
2. Dans le menu **Service**, sélectionnez `order-service`.
3. Cliquez sur **Find Traces**.
4. Ouvrez la trace la plus récente : elle affiche la hiérarchie complète

   ```
   POST /order            (order-service, span serveur)
     └── GET /products    (order-service, span client "requests")
           └── GET /products (product-service, span serveur)
   ```

   avec la durée de chaque étape, confirmant la trace distribuée bout en
   bout entre les deux microservices.

### 6. Corréler Grafana → Jaeger

1. Dans le dashboard **Logs** de Grafana, repérez la ligne `Order completed`
   correspondant à votre appel de test (basé sur l'horodatage).
2. Notez l'heure exacte de la requête.
3. Dans Jaeger, filtrez les traces `order-service` sur cette même plage
   horaire pour retrouver la trace correspondante et visualiser sa
   décomposition en spans.

Cette démarche illustre concrètement comment logs, métriques et traces se
complètent pour diagnostiquer le comportement d'une requête de bout en
bout — le cœur du sujet "Monitoring & Observabilité".

## Détails d'implémentation

### Métriques (Prometheus)

Chaque service définit, dans `metrics.py` :

- `*_requests_total` (Counter, labellisé par `method`, `endpoint`,
  `http_status`) : nombre total de requêtes traitées.
- `*_request_duration_seconds` (Histogram, labellisé par `method`,
  `endpoint`) : durée des requêtes ; ses buckets alimentent l'histogramme
  Grafana et son `_sum`/`_count` permettent de calculer la moyenne.
- `*_errors_total` (Counter) : nombre d'erreurs rencontrées.

Prometheus scrape `order-service:5000/metrics` et
`product-service:5001/metrics` toutes les 5 secondes (voir
`prometheus/prometheus.yml`).

### Logs (Loki / Promtail)

`logger.py` configure un logger qui écrit des lignes JSON structurées
(`timestamp`, `level`, `service`, `message`) à la fois sur la sortie
standard et dans `logs/order.log` / `logs/product.log`. Ce dossier est monté
en volume Docker partagé avec le conteneur `promtail`, qui tail les
fichiers `*.log` et les pousse vers Loki (`promtail/config.yml`). Grafana
interroge ensuite Loki via la datasource provisionnée automatiquement.

### Traces (OpenTelemetry / Jaeger)

`telemetry.py` configure un `TracerProvider` OpenTelemetry qui exporte les
spans en OTLP/HTTP vers l'OpenTelemetry Collector
(`otel/collector-config.yaml`), lequel les retransmet à Jaeger. Flask est
instrumenté automatiquement via `FlaskInstrumentor` (span serveur pour
chaque requête entrante) et, côté Order Service, la librairie `requests`
est instrumentée via `RequestsInstrumentor` (span client pour l'appel
sortant vers Product Service). La propagation du contexte de trace
(en-têtes W3C `traceparent`) est automatique, ce qui relie les deux spans
en une seule trace distribuée.

## Dépannage

- **Un dashboard Grafana affiche "No data"** : envoyez quelques requêtes
  `POST /order` pour générer des métriques/logs, puis attendez le prochain
  scrape Prometheus (5s) ou refresh Grafana (5s).
- **Prometheus target `DOWN`** : vérifiez `docker compose ps` puis
  `docker compose logs order-service` / `product-service`.
- **Pas de traces dans Jaeger** : vérifiez `docker compose logs
  otel-collector` pour confirmer la réception des spans OTLP, et que
  `OTEL_EXPORTER_OTLP_ENDPOINT` pointe bien vers `otel-collector:4318`.
- **Pas de logs dans Loki** : vérifiez que `./logs` contient bien
  `order.log`/`product.log` sur la machine hôte, et consultez
  `docker compose logs promtail`.
