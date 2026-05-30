# Document 19: Release Documentation

---

## 1. Versioning Strategy

Hawk-AI follows **Semantic Versioning 2.0.0 (SemVer)**:
$$\text{Version Format: } \text{MAJOR}.\text{MINOR}.\text{PATCH}$$
* **MAJOR**: Structural system API changes, breaking changes in edge-to-cloud interfaces.
* **MINOR**: New features (e.g., adding detection for a new infraction class like "triple-riding").
* **PATCH**: Bug fixes, performance optimizations, and security patches.

---

## 2. Release Notes: v1.0.0-alpha (MVP Release)

### 2.1 Overview
This release provides the first complete, end-to-end MVP build of the Hawk-AI traffic infraction crowdsourced reporting system. It supports helmet-less rider and wrong-way driving detection on the Raspberry Pi edge device, local sync modes, and cloud VLM validation queues.

### 2.2 What's New
* **Edge Inference Integration**: Loaded custom YOLOv8-nano model optimized for embedded CPUs.
* **Privacy Engine**: Embedded edge-side blurring of bystander faces and non-violating plates.
* **Offline Storage**: Integrated local SQLite database buffering during network dropouts.
* **Cloud Ingestion API**: Created secure Express API gateway with API key verification.
* **VLM Verification Engine**: Integrated OpenAI GPT-4o Vision API for secondary validation and plate text extraction.
* **Admin Interface**: Created review panel dashboard with interactive Leaflet map overlays.

---

## 3. Project Changelog

### [1.0.0-alpha] - 2026-05-31
#### Added
* Custom YOLOv8-nano model weights file and OpenCV capture loop on Edge Client.
* GPS NMEA sentence parser supporting UART interface readouts.
* Edge-side Gaussian blurring modules for faces and license plates.
* SQLite local DB schemas for offline data caching.
* Node.js/TypeScript Ingestion API with Token Authentication.
* OpenAI GPT-4o API prompt templates and JSON extraction parsers.
* PostgreSQL table configurations with PostGIS geography extensions.
* Web dashboard featuring review lists, details panes, and Leaflet Maps.
* CI/CD build scripts for Docker cloud deployments.

#### Fixed
* Fixed thread lock bugs occurring during rapid concurrent writes to the local SQLite database.
* Resolved mobile viewport height bugs on Safari browser (iOS 16) in the portal layout.

#### Security
* Configured TLS 1.3 protocol requirement on API routing paths.
* Hardened VLM prompt templates to mitigate user text injection vectors.
* Encrypted local SQLite storage instances using SQLCipher.
