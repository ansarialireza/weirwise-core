# Weirwise Core Performance Baseline

## Hardware & Environment
- **CPU**: Intel(R) Core(TM) i7-8565U CPU @ 1.80GHz (4 cores / 8 threads)
- **OS**: Windows 10 (Build 26200) / WSL Ubuntu 24.04
- **PostgreSQL**: PostgreSQL 16.15 / pgvector 0.8.7
- **Python**: 3.11.0

## Measured Benchmarks
1. **Vector Retrieval (2,500 vectors, dim=1536, top_k=10)**:
   - Exact Search (Sequential Scan): p50 = 11.41 ms, p95 = 14.93 ms, p99 = 18.39 ms
   - HNSW Index Search: p50 = 3.05 ms, p95 = 5.33 ms, p99 = 6.04 ms (3.74x faster)
   - Recall@10: 0.575 (with `ef_search = 40`)
2. **Concurrent Load (400 requests across concurrency 1-20)**:
   - 1 Client: 15.55 req/s (p50: 50.65 ms, p95: 106.93 ms)
   - 5 Clients: 34.35 req/s (p50: 118.25 ms, p95: 227.22 ms)
   - 10 Clients: 29.99 req/s (p50: 268.12 ms, p95: 525.95 ms)
   - 20 Clients: 26.01 req/s (p50: 818.77 ms, p95: 980.95 ms)
   - Error Rate: 0.0% (0 / 400 failed)
