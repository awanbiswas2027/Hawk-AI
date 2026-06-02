# Hawk-AI: Open-Source Crowdsourced Traffic Violation Detection Ecosystem

Welcome to the official repository and project documentation suite for **Hawk-AI**. 

Hawk-AI is an automated, edge-to-cloud traffic violation detection and reporting system. It is designed to capture real-time video feed via a helmet-mounted or dashcam-mounted camera, process the feed locally on an edge computing device using lightweight computer vision to detect traffic infractions, filter and validate these detections using a secondary cloud-based Vision-Language Model (VLM), and automatically generate and dispatch a verified structured infraction report (including location metadata, timestamp, image evidence, and extracted license plate data) directly to municipal traffic authorities without requiring manual driver intervention.

This documentation package is designed to meet the standards for academic final year project submissions, startup MVP specifications, professional portfolios, and enterprise-grade software development.

---

## 📂 Documentation Directory

To ensure the highest depth and professional quality, the project documentation has been organized into modular sections:

### 1. Project Planning & Business Requirements
*   [01. Executive Summary](file:///e:/CODING/Projects/Hawk-AI/docs/01_executive_summary.md): Project overview, Bengaluru-specific traffic issues, and high-level dual-layer AI solution.
*   [02. Business Requirements Document (BRD)](file:///e:/CODING/Projects/Hawk-AI/docs/02_brd.md): Stakeholder matrix, scope boundaries, compliance frameworks (GDPR/DPDP), and success criteria.
*   [03. Product Requirements Document (PRD)](file:///e:/CODING/Projects/Hawk-AI/docs/03_prd.md): User personas, functional/non-functional requirements, user journeys, and Gherkin acceptance criteria.
*   [04. Software Requirements Specification (SRS)](file:///e:/CODING/Projects/Hawk-AI/docs/04_srs.md): IEEE 830-1998 compliant specification detailing camera, GPS, and dispatch interfaces.
*   [05. Project Plan & Budget](file:///e:/CODING/Projects/Hawk-AI/docs/05_project_plan.md): Work Breakdown Structure (WBS), Agile sprints, milestones, and cost-benefit analysis (Edge vs. Cloud VLM transactional costs).
*   [Interactive Roadmap Dashboard](file:///e:/CODING/Projects/Hawk-AI/roadmap.html): A fully interactive, phase-by-phase and day-by-day checklist, progress monitor, and token cost calculator tool.
*   [Static Roadmap Artifact](file:///C:/Users/Awan%20Biswas/.gemini/antigravity/brain/6fb2270b-bdc9-4253-9720-fbda67505ab0/daywise_roadmap.md): Detailed markdown outline of the 14-day implementation optimized for the Gemini 3.5 Flash VLM.

### 2. Architecture & Design
*   [06. System Architecture Document](file:///e:/CODING/Projects/Hawk-AI/docs/06_system_architecture.md): High-Level, component, deployment, and data flow diagrams.
*   [07. High-Level Design (HLD)](file:///e:/CODING/Projects/Hawk-AI/docs/07_hld.md): System modules, database choices, and the rationale behind hybrid edge-cloud edge-inference.
*   [08. Low-Level Design (LLD)](file:///e:/CODING/Projects/Hawk-AI/docs/08_lld.md): Class details, function schemas, and the offline/cellular dead-zone state machine logic.
*   [09. Database Design](file:///e:/CODING/Projects/Hawk-AI/docs/09_database_design.md): Entity-Relationship Diagram (ERD), table schemas, index strategies, and sample SQL data.
*   [10. UML Diagrams](file:///e:/CODING/Projects/Hawk-AI/docs/10_uml_documentation.md): Combined Use Case, Class, Sequence, Activity, State, and Component UML diagrams.

### 3. Engineering, APIs & Security
*   [11. API Documentation](file:///e:/CODING/Projects/Hawk-AI/docs/11_api_documentation.md): REST endpoints specification, payload examples, token auth, and rate-limiting.
*   [12. UI/UX Specifications](file:///e:/CODING/Projects/Hawk-AI/docs/12_ui_ux_documentation.md): Information Architecture, user flows, wireframe specifications, and WCAG accessibility.
*   [13. Security & Threat Modeling](file:///e:/CODING/Projects/Hawk-AI/docs/13_security_documentation.md): Threat models, JWT/API key auth, and edge-side bystander face and plate blurring algorithms.
*   [14. DevOps & CI/CD Pipelines](file:///e:/CODING/Projects/Hawk-AI/docs/14_devops_deployment.md): GitHub Actions configurations, Docker architectures, and Over-the-Air (OTA) firmware update workflows.

### 4. Quality Assurance, Testing & Bug Tracking
*   [15. Testing & Verification Documentation](file:///e:/CODING/Projects/Hawk-AI/docs/15_testing_documentation.md): Test plan, scripts, thermal throttle limits, vibration testing, and cell drop tests.
*   [16. Defect & Bug Tracking Report](file:///e:/CODING/Projects/Hawk-AI/docs/16_bug_tracking.md): Severity scale, bug workflow state machine, and mock defects.

### 5. Deployment, Operations & Maintenance
*   [17. User & Admin Manual](file:///e:/CODING/Projects/Hawk-AI/docs/17_user_manual.md): Hardware build instructions (BOM, RPi flashing, camera mount guide), configuration, and troubleshooting.
*   [18. Maintenance & SLA Procedures](file:///e:/CODING/Projects/Hawk-AI/docs/18_maintenance_support.md): Change management, incident escalations, and ML weight hot-reloading procedures.
*   [19. Release Documentation](file:///e:/CODING/Projects/Hawk-AI/docs/19_release_documentation.md): SemVer release model, release notes, and future changelogs.

### 6. Academic Thesis & Viva Prep
*   [20. Comprehensive Project Report](file:///e:/CODING/Projects/Hawk-AI/docs/20_project_report.md): Academic thesis chapters including Abstract, Literature Review, Methodology, and Future Scope.
*   [21. Viva Voce Preparation Q&A](file:///e:/CODING/Projects/Hawk-AI/docs/21_viva_preparation.md): 100 anticipated viva questions with complete technical answers across all system domains.

---

## 🛠️ Core Technology Stack

| Domain | Selected Technology | Rationale |
| :--- | :--- | :--- |
| **Edge Hardware** | Raspberry Pi 4 Model B (4GB) / Pi 5 | Low power draw, GPIO interface for GPS modules, affordable, Linux base. |
| **Edge Computer Vision** | Python 3.10, OpenCV, Ultralytics YOLOv8n | Real-time object detection (helmet, wrong-way) with ~15 FPS edge inference. |
| **Cloud Validation VLM** | OpenAI GPT-4o (Vision API) | Multi-modal reasoning to confirm infraction context and extract plate OCR. |
| **Cloud Core Backend** | Node.js, TypeScript, Express | High throughput, asynchronous operations, type-safety. |
| **Database Engine** | PostgreSQL 15 | Relational integrity for citations, geo-spatial query capabilities via PostGIS. |
| **Containerization** | Docker, Docker Compose | Consistent development environments and easy containerized microservice deployments. |
| **CI/CD & Deployment** | GitHub Actions, Mender.io | Automated unit/integration testing and secure Over-The-Air (OTA) updates. |

---

## 🚀 Key Project Principles

1. **Zero-Involvement Capture**: The driver does not interact with any software while riding. Detections are triggered automatically based on spatial parameters and camera feeds.
2. **False-Positive Elimination**: Citations are not sent to municipal authorities unless verified by a secondary multi-modal intelligence layer (GPT-4o VLM) with a confidence score exceeding 95%.
3. **Edge-Side Privacy First**: License plates of non-violating vehicles and faces of innocent bystanders are blurred directly on the Raspberry Pi *before* any frames leave the local edge storage.
4. **Resiliency to Connectivity Outages**: When passing through cellular dead zones, the edge device buffers logs and media in a local SQLite file database, syncing them immediately when cell coverage is restored.
