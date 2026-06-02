# Backend Systems Engineer — Meridian Payments

## About the role

Meridian's payments platform processes 4M+ transactions per day across 60 currencies. We're looking for a backend engineer to join the infrastructure team and work on the systems that make transactions fast, reliable, and observable — rate limiting, distributed tracing, latency analysis, and the tooling that helps us find problems before customers do.

This is not a feature team. You will own infrastructure that every other team depends on.

## What you'll do

- Design and implement rate limiting, traffic shaping, and abuse detection systems for high-throughput payment flows
- Build and maintain the distributed tracing and observability pipeline — spans, sampling strategies, alerting
- Instrument services for latency profiling and identify bottlenecks in the critical path
- Write and review Go services that need to be correct under concurrent load, not just fast on average
- Participate in on-call rotation; when something breaks you are one of the engineers who fixes it

## What we're looking for

- Strong systems fundamentals — you understand what happens at the OS and network level when a request arrives
- Experience with distributed tracing (OpenTelemetry, Jaeger, Zipkin, or similar) and what makes traces useful versus noisy
- Comfort with high-throughput systems: connection pooling, backpressure, queue depth, the difference between p50 and p99 latency
- Go proficiency, or strong enough systems background that Go is a fast ramp
- Redis or similar in-memory stores — you've used them for more than caching
- Experience with Kubernetes or container orchestration at the service level

## Bonus

- You've designed a sampling strategy for a tracing system and know the tradeoffs between head-based and tail-based sampling
- You've worked on payments, fintech, or any domain where correctness is non-negotiable
- You've done capacity planning or load testing at production scale

## Stack

Go, Redis, Kafka, PostgreSQL, Kubernetes, Prometheus, Jaeger, Grafana

## Location

Remote (Canada or US) or Toronto office
