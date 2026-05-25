# Observability quick start

This backend now exposes:

- **Prometheus metrics** at `http://localhost:8000/metrics/`
- **Grafana dashboards** at `http://localhost:3000`
- **Prometheus** at `http://localhost:9090`
- **Loki** for logs at `http://localhost:3100`
- **Tempo** for traces at `http://localhost:3200`

## What you need to do

1. Start the stack:

```powershell
docker compose -f docker-compose.yml up -d --build
```

2. Open the app and generate some traffic:

- Visit `http://localhost:8000/health/`
- Open a few API pages in the browser
- Log in / perform actions in the app

3. Check Prometheus:

- Go to **Status → Targets**
- Make sure the `backend` target is **UP**
- Try this query in the Prometheus graph:

```promql
up{job="backend"}
```

4. Check Grafana:

- Open the **Backend Overview** dashboard
- The top panel should show whether Prometheus can scrape the app
- The request/latency graphs will only move after you send some traffic

## If graphs are empty

That usually means one of these:

- The app has not received any requests yet
- Prometheus cannot reach the backend container
- The dashboard datasource was not provisioned yet
- You are looking at a time range with no recent traffic

## Useful queries

```promql
sum(rate(backend_http_requests_total[5m]))
histogram_quantile(0.95, sum(rate(backend_http_request_duration_seconds_bucket[5m])) by (le))
up{job="backend"}
```

