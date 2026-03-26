# Project Proposal: Distributed Audio Processing Pipeline with Observability

## Vision

The goal of this project is to design and implement a distributed system for processing audio files through an asynchronous pipeline.

The system will allow users to upload audio files, which will then be processed by a set of distributed worker services. Each file will go through a sequence of processing steps (e.g., metadata extraction, basic audio feature analysis such as duration or waveform characteristics), and the results will be stored and made available to the user.

The system is designed around an event-driven architecture where components communicate asynchronously through a message broker. This enables scalability, decoupling, and fault tolerance.

Core functionalities:
- Upload audio files to the system
- Asynchronous processing of audio files through worker services
- Storage of processed results and metadata
- Monitoring of system behavior through metrics and dashboards

## Learning Goals

This project is highly relevant to the Distributed Systems course as it focuses on designing and implementing a system where distribution is necessary to achieve scalability and robustness.

The main learning objectives are:

- Understanding and applying **event-driven architectures** and **asynchronous communication**
- Designing a system with **clear service boundaries** and **loose coupling**
- Exploring **fault tolerance mechanisms**, such as retries and failure recovery
- Reasoning about **data consistency**, particularly eventual consistency in pipelines
- Implementing **scalability strategies**, especially horizontal scaling of worker components
- Gaining practical experience with **observability**, including metrics collection and visualization
- Deploying and orchestrating distributed components using containerization technologies

## Intended Technologies and Motivations

- **Python (FastAPI)**  
  For implementing the API service due to its simplicity and rapid development capabilities.

- **Message Broker (RabbitMQ or Kafka)**  
  To enable asynchronous communication between services and decouple producers from consumers.

- **Worker Services (Python)**  
  For processing audio files independently and in parallel.

- **PostgreSQL**  
  For storing metadata and processing results in a structured way.

- **Object Storage (e.g., MinIO or local file system)**  
  For storing uploaded audio files.

- **Docker**  
  For containerizing all components and ensuring reproducibility.

- **Kubernetes (e.g., Kind)**  
  For orchestrating services and enabling horizontal scaling of workers.

- **Prometheus + Grafana**  
  For collecting, monitoring, and visualizing system metrics (e.g., processing time, queue size, throughput).

These technologies are chosen to reflect real-world distributed system architectures while remaining feasible within the project constraints.

## Intended Deliverables

- A working distributed application composed of:
  - API service
  - Message broker
  - Worker service(s)
  - Storage components
- Containerized deployment (Docker-based)
- Kubernetes configuration for orchestration
- Monitoring dashboards showing system behavior under load
- Unit and integration tests for API and worker services
- Source code hosted on a GitHub repository
- Final report (LaTeX) describing design, implementation, and evaluation
- Presentation and demonstration of the system

## Usage Scenarios

### Scenario 1: Audio Upload and Processing
A user uploads an audio file through the API. The system stores the file and sends a processing request to the message queue. Worker services consume the request, process the file, and store the results. The user can later retrieve the processed information.

### Scenario 2: Concurrent Processing
Multiple users upload audio files simultaneously. The system distributes the workload across multiple worker instances, demonstrating parallel processing and scalability.

### Scenario 3: Fault Tolerance
During processing, a worker service fails. The system ensures that the task is retried or reassigned, demonstrating resilience and fault recovery.

### Scenario 4: Observability
System metrics (e.g., processing latency, queue size, worker utilization) are collected and visualized. The user can observe how the system behaves under different loads.

## Group Members

- Matteo Cardellini  
  matteo.cardellini@studio.unibo.it