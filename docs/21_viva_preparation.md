# Document 21: Viva Voce Preparation Section (100 Questions & Answers)

This guide helps students prepare for final-year project viva examinations. The questions are categorized into six key technical areas.

---

## 📂 Table of Contents
1. [Core Project Concept & Problem Space (Q1 - Q15)](#1-core-project-concept--problem-space-q1---q15)
2. [Edge hardware & Embedded Systems (Q16 - Q30)](#2-edge-hardware--embedded-systems-q16---q30)
3. [Computer Vision & Edge YOLO Model (Q31 - Q45)](#3-computer-vision--edge-yolo-model-q31---q45)
4. [Cloud Backend, APIs & Redis Queue (Q46 - Q65)](#4-cloud-backend-apis--redis-queue-q46---q65)
5. [Database Architecture & GIS Systems (Q66 - Q80)](#5-database-architecture--gis-systems-q66---q80)
6. [Security, Privacy, Threat Model & Testing (Q81 - Q100)](#6-security-privacy-threat-model--testing-q81---q100)

---

## 1. Core Project Concept & Problem Space (Q1 - Q15)

#### Q1: What is the core objective of Hawk-AI?
**Answer**: To build an automated, edge-to-cloud traffic violation detection and reporting system. It uses a helmet-mounted or dashcam camera to capture video, runs lightweight computer vision on the edge to detect violations, validates reports using a cloud-based VLM, and dispatches verified citations to municipal traffic authorities without manual driver intervention.

#### Q2: What inspired this project?
**Answer**: The high rate of traffic violations in dense cities (like Bengaluru), the lack of police personnel to enforce traffic laws everywhere, and the safety hazards commuters face when trying to manually record violations while driving.

#### Q3: Who are the target users?
**Answer**: Motorcyclists and vehicle commuters (data contributors), local traffic police departments (report reviewers and ticket issuers), and open-source developers (contributors).

#### Q4: Why is it called a "crowdsourced" ecosystem?
**Answer**: Instead of relying on static city cameras, the system crowdsources data collection by allowing everyday commuters to mount cameras and edge devices on their vehicles.

#### Q5: What are the three core traffic infractions detected in v1.0?
**Answer**: Riding a motorcycle without a helmet, wrong-way driving, and jumping road dividers.

#### Q6: How does the system protect citizen privacy?
**Answer**: It uses edge-side anonymization. Faces of pedestrians and license plates of vehicles NOT involved in the violation are blurred on the Raspberry Pi before data is uploaded to the cloud.

#### Q7: Why is a dual-layer AI setup used instead of running everything on the edge?
**Answer**: Embedded processors like the Raspberry Pi do not have the compute power to run large, multi-modal Vision-Language Models (VLMs) locally. Using a lightweight model (YOLOv8-nano) on the edge to filter frames and a larger model (GPT-4o) in the cloud to verify violations balances local performance with validation accuracy.

#### Q8: Why is a dual-layer AI setup chosen over streaming all video to the cloud?
**Answer**: Streaming raw 1080p video consumes too much network bandwidth (~3-5 GB/hour per user), is expensive to process in the cloud, and fails in cellular dead zones. Local edge filtering only uploads image crops of suspected violations, reducing bandwidth usage by 99.9%.

#### Q9: How does the system handle cellular dead zones?
**Answer**: When network connectivity is lost, the edge device buffers reports locally in an encrypted SQLite database. Once connection is restored, the device synchronizes the buffered reports back to the cloud.

#### Q10: How does the platform achieve a target of 0% false positives sent to police?
**Answer**: Citations are only sent to the police portal if the cloud VLM returns a verification confidence rating of >95%. Borderline cases (75%-95% confidence) are routed to a human-in-the-loop (HITL) review dashboard for manual approval.

#### Q11: What is the role of municipal traffic authorities in this ecosystem?
**Answer**: They act as the final review authority. They log into the admin portal, review the pre-verified citations, and approve them to issue official government fines.

#### Q12: How does the system prevent citizen harassment or abuse?
**Answer**: Data is encrypted, edge devices are authenticated with unique keys, and all final citations must be reviewed by traffic officers before official tickets are issued.

#### Q13: What is the business model or value proposition for municipalities?
**Answer**: It acts as a force multiplier for traffic enforcement. It creates a dynamic, mobile monitoring network at zero infrastructure capital expenditure for the city, increasing citation revenue while improving road safety.

#### Q14: What is the legal viability of citizen-submitted video evidence?
**Answer**: Many jurisdictions do not legally recognize automated citizen video as sole grounds for issuing traffic fines. Hawk-AI addresses this by formatting the reports as official civic complaints submitted on the citizen's behalf. The traffic police portal acts as the final arbiter where an officer reviews the evidence before signing the ticket.

#### Q15: What are the primary hardware components of the edge rig?
**Answer**: A Raspberry Pi 4 (or Pi 5), a Neo-6M GPS serial module, a wide-angle USB webcam, a 10,000mAh power bank, and a custom 3D-printed enclosure.

---

## 2. Edge Hardware & Embedded Systems (Q16 - Q30)

#### Q16: Why was the Raspberry Pi 4 chosen as the edge platform?
**Answer**: It runs a full Linux environment, provides GPIO interfaces for sensors, is affordable, and has sufficient CPU/GPU capability to run quantized YOLOv8-nano models at ~12-15 FPS.

#### Q17: How is the GPS module connected to the Raspberry Pi?
**Answer**: It connects to the GPIO header serial pins: GPS TXD connects to RPi RXD (Pin 15/GPIO 15), GPS RXD connects to RPi TXD (Pin 14/GPIO 14), GPS VCC connects to Pin 1 (3.3V), and GPS GND connects to Pin 6 (Ground).

#### Q18: What serial port configuration is required on the Pi to read GPS data?
**Answer**: The hardware serial port `/dev/ttyS0` (or `/dev/aminUART0` on newer models) must be enabled in the config options (`sudo raspi-config`), and the console login interface over serial must be disabled to prevent signal clashes.

#### Q19: Explain the GPS data parsing logic.
**Answer**: The module outputs raw NMEA-0183 sentences. The Python edge script reads this buffer and parses the `$GPRMC` sentence to extract Latitude, Longitude, and Speed, and the `$GPGGA` sentence to verify GPS lock status.

#### Q20: What happens if the GPS module loses satellite lock?
**Answer**: If GPS lock is lost, the edge script pauses violation logging. Captured frames are dropped because valid location coordinates and timestamps are required for legal citations.

#### Q21: What is the power consumption profile of the edge rig?
**Answer**: Under active inference, the Raspberry Pi 4 draws ~800mA to 1.2A at 5V (~5-6 Watts). A 10,000mAh (37Wh) power bank can power the device for 5 to 6 hours of continuous riding.

#### Q22: How does the system handle high edge-operating temperatures inside a rider's pocket or bag?
**Answer**: The custom casing includes passive heatsinks and dual cooling fans. The edge software monitors system temperature via `/sys/class/thermal/thermal_zone0/temp`. If the temp exceeds 75°C, the script slows down inference to prevent thermal throttling or system shutdown.

#### Q23: How do you address high-frequency vibrations on a motorcycle?
**Answer**: The camera uses hardware-based Electronic Image Stabilization (EIS). The edge software calculates frame sharpness using OpenCV's Laplacian variance method, discarding blurry frames to conserve processing cycles.

#### Q24: What is the purpose of the MicroSD card in the edge rig?
**Answer**: It stores the operating system (Raspberry Pi OS), the YOLOv8-nano weights, the edge scripts, and acts as a local storage buffer for offline events.

#### Q25: Why is a class 10 SD card required?
**Answer**: To support the write speeds required when saving raw images to the local SQLite database during offline sync operations.

#### Q26: How does the RPi check for network connectivity?
**Answer**: It runs a background thread that attempts a TCP handshake with the backend API or a public DNS server (e.g., `8.8.8.8`) every 60 seconds.

#### Q27: How does the Pi sync offline databases back to the cloud?
**Answer**: When connection is restored, the `UploadCoordinator` reads the local SQLite database and uploads buffered events sequentially using a rate-limiter to prevent network congestion.

#### Q28: What OS runs on the Raspberry Pi?
**Answer**: A customized, headless installation of Raspberry Pi OS (Debian Bullseye, 64-bit).

#### Q29: How do you perform remote software updates on the edge devices?
**Answer**: We use **Mender.io** for remote OTA (Over-the-Air) system updates. It runs dual A/B system partitions to support automated rollbacks if an update fails.

#### Q30: How is the physical rig mounted?
**Answer**: The camera is mounted on the side or chin of the helmet using adhesive mount brackets. The Raspberry Pi enclosure is mounted on the motorcycle handlebars or carried in a rider's pouch.

---

## 3. Computer Vision & Edge YOLO Model (Q31 - Q45)

#### Q31: Why was YOLOv8-nano chosen over SSD or Faster R-CNN?
**Answer**: YOLOv8-nano is designed for real-time inference on low-power devices. It has a small footprint (~3 million parameters) and maintains an inference latency of under 80ms on the Pi CPU.

#### Q32: How was the YOLO model trained for this project?
**Answer**: We used transfer learning on a custom dataset containing Indian vehicle types, traffic riders, and highway markings, labeled using CVAT. The model was trained in PyTorch and exported to ONNX format.

#### Q33: How is the YOLO model optimized for the Raspberry Pi?
**Answer**: The model is quantized from FP32 to INT8 precision using ONNX Runtime. This reduces model size by 75% and speeds up inference on the RPi CPU.

#### Q34: What is the input image resolution for the YOLOv8 model?
**Answer**: Frames are resized to 640x640 pixels to balance detection accuracy with inference speed.

#### Q35: Explain the logic for wrong-way driving detection.
**Answer**: The system tracks the vehicle's heading vector (calculated from sequential bounding boxes) and compares it against the GPS sensor heading and OpenStreetMap direction vectors for the current road segment.

#### Q36: Explain the helmet violation detection logic.
**Answer**: The YOLO model detects motorcycles and extracts bounding boxes for the rider. Sub-classifiers analyze the head region to verify the presence of a safety helmet.

#### Q37: How is road divider jumping detected?
**Answer**: The system identifies road medians/dividers and flags instances where a vehicle's bounding box intersects or crosses non-designated divider regions.

#### Q38: How does the edge anonymizer work?
**Answer**: It uses OpenCV to run Haar cascades for faces and license plates. It applies a Gaussian blur to all non-violating objects, leaving only the infraction subject clear.

#### Q39: Why not blur violating license plates?
**Answer**: The license plate of the violating vehicle must remain clear as it is the primary evidence required by traffic police to issue citations.

#### Q40: What OpenCV functions are used to blur frames?
**Answer**: `cv2.GaussianBlur` is used to apply a blurring mask to identified bounding boxes.

#### Q41: How do you handle low-light or night driving conditions?
**Answer**: The camera adjusts exposure dynamically. The edge script runs a brightness checker using the frame's average pixel intensity. If it falls below a threshold, the script uses CLAHE (Contrast Limited Adaptive Histogram Equalization) to improve image contrast.

#### Q42: What is "frame skipping" and why is it used?
**Answer**: The camera captures video at 30 FPS, but the Pi CPU can only process YOLO inference at 15 FPS. The script drops every other frame to keep the processing queue running in real-time.

#### Q43: How does the system track vehicles across consecutive frames?
**Answer**: It uses a lightweight Kalman filter-based tracker (ByteTrack) to assign consistent IDs to vehicles, preventing duplicate reports for the same violation.

#### Q44: What is the confidence threshold for the edge YOLO model?
**Answer**: It is set to 0.70. Bounding boxes below this confidence are discarded to reduce unnecessary cloud uploads.

#### Q45: How do you avoid false triggers from static roadside advertisements?
**Answer**: By checking the vehicle tracker speed from GPS inputs. Bounding boxes must have active motion vectors to trigger the validation logic.

---

## 4. Cloud Backend, APIs & Redis Queue (Q46 - Q65)

#### Q46: What technology stack is used for the cloud backend?
**Answer**: Node.js and TypeScript with Express.js for the REST API gateway, Redis for BullMQ task management, and PostgreSQL for storage.

#### Q47: Why is Node.js chosen for the API gateway?
**Answer**: Its asynchronous, non-blocking I/O model handles high volumes of concurrent API requests from edge devices efficiently.

#### Q48: How are edge device payloads uploaded?
**Answer**: Payloads are posted to `/api/v1/ingest` as `multipart/form-data` containing the metadata JSON and the cropped image file.

#### Q49: What is the role of the Redis queue (BullMQ)?
**Answer**: It acts as a task buffer. Because VLM API calls are slow (~2-3 seconds per request), the API gateway writes payloads directly to Redis and returns a `202 Accepted` response. Background workers pull tasks from the queue as VLM capacity allows.

#### Q50: How do you secure communications between the edge and the cloud?
**Answer**: All network traffic is encrypted via HTTPS (TLS 1.3). Edge devices authenticate using unique keys in the request headers (`X-Device-API-Key`).

#### Q51: How is the OpenAI API integrated?
**Answer**: The backend uses the official OpenAI NodeSDK to query the `gpt-4o` model, passing the S3 image link and a structured prompt to receive validation decisions.

#### Q52: What prompt engineering strategies are used?
**Answer**: We use chain-of-thought prompting. The model is instructed to analyze the image step-by-step (e.g., check for a motorcycle, look for a helmet, locate the plate) and return a structured JSON object.

#### Q53: Show an example of the VLM output schema.
**Answer**:
```json
{
  "violation_confirmed": true,
  "license_plate": "KA03HA5512",
  "confidence_score": 0.98,
  "reasoning": "Rider wearing yellow shirt lacks a helmet. License plate KA03HA5512 is clearly visible."
}
```

#### Q54: How does the cloud backend handle VLM API failures?
**Answer**: Workers use an exponential backoff retry strategy managed by BullMQ. If the OpenAI API returns a 503 or rate limit error, the task is returned to the queue and retried after a delay.

#### Q55: How are citation PDFs generated?
**Answer**: We use the Node.js `pdfkit` module to compile coordinates, timestamps, evidence images, and VLM validation text into a structured PDF document.

#### Q56: How are citations dispatched?
**Answer**: PDF reports are emailed to the traffic police portal via SMTP using `nodemailer`, or posted directly to their citation API.

#### Q57: What is the purpose of the `/api/v1/portal/review-queue` endpoint?
**Answer**: It allows the admin dashboard to retrieve citations flagged with borderline VLM confidence (75%-95%) for manual review.

#### Q58: How are user sessions managed on the portal?
**Answer**: Via JSON Web Tokens (JWT). When a user logs in, the server generates a token containing their ID and role, signed with an HS256 secret.

#### Q59: What is the token expiration policy?
**Answer**: JWT tokens expire after 12 hours. Refresh tokens are stored in the database to allow silent session renewal.

#### Q60: Explain how rate limiting is implemented.
**Answer**: We use Express rate-limit middleware backed by Redis. The endpoint `/api/v1/ingest` limits devices to 60 requests/minute to prevent spamming.

#### Q61: Where are the evidence images stored in the cloud?
**Answer**: In an Amazon S3 bucket. Access is secured using signed URLs with a 15-minute expiration window.

#### Q62: How do you optimize S3 storage costs?
**Answer**: We set lifecycle rules that transition files to Glacier Deep Archive after 90 days and delete them after 365 days.

#### Q63: How are the Node.js API services packaged?
**Answer**: They are packaged into Docker containers using multi-stage builds to optimize image size.

#### Q64: What is the role of the load balancer?
**Answer**: The AWS Application Load Balancer distributes incoming edge traffic across ECS task instances and manages SSL certificates.

#### Q65: How do you verify that cloud API requests come from a real edge device?
**Answer**: The request header contains the device serial. The gateway calculates the SHA-256 HMAC signature of the request body using the device's registered private key, comparing it to the signature header.

---

## 5. Database Architecture & GIS Systems (Q66 - Q80)

#### Q66: Why was PostgreSQL chosen over MySQL?
**Answer**: PostgreSQL has strong relational integrity, supports JSON columns, and features the **PostGIS** extension for geo-spatial spatial queries.

#### Q67: What is PostGIS and why is it used?
**Answer**: PostGIS is a spatial database extension for PostgreSQL. It allows storing geographical coordinates as spatial objects and running geometry queries (e.g., finding incidents within a bounding box).

#### Q68: What database data type is used for latitude and longitude?
**Answer**: The `GEOGRAPHY(POINT, 4326)` data type, which coordinates GPS spatial points using the WGS 84 coordinate system.

#### Q69: Explain the difference between GEOMETRY and GEOGRAPHY in PostGIS.
**Answer**: `GEOMETRY` represents points on a flat plane (Cartesian system), while `GEOGRAPHY` uses a spherical model representing the Earth's curvature, providing accurate distance calculations over large areas.

#### Q70: How do you query violations within 500 meters of a junction?
**Answer**: Using the `ST_DWithin` PostGIS function:
```sql
SELECT * FROM violations 
WHERE ST_DWithin(geolocation, ST_MakePoint(77.5946, 12.9716)::geography, 500);
```

#### Q71: What is the indexing strategy for geography columns?
**Answer**: We use a Generalized Search Tree (**GIST**) spatial index on the coordinate column:
```sql
CREATE INDEX idx_violations_geom ON violations USING GIST(geolocation);
```

#### Q72: How are violation records linked to generated citations?
**Answer**: Via a one-to-one relationship using a foreign key constraint: the `citations` table contains a unique `violation_id` referencing `violations(id)`.

#### Q73: What indexes speed up queries on the Admin Dashboard?
**Answer**: GIST indexes for map location searches, B-tree indexes on `occurrence_time DESC` for list sorting, and B-tree indexes on `license_plate` to look up vehicle histories.

#### Q74: Why partition the `violations` table?
**Answer**: As millions of violations are logged, table sizes grow. Partitioning the table monthly based on target dates keeps indexes small and queries fast.

#### Q75: How does database connection pooling work in this stack?
**Answer**: The Node backend uses the `pg-pool` module to manage a pool of active database connections, reusing them to reduce connection overhead.

#### Q76: Explain the database schemas for devices.
**Answer**: The `devices` table records the owner ID, status (active/inactive), serial number, and registration date.

#### Q77: What happens to violations if a device is deleted?
**Answer**: The foreign key constraint is configured with `ON DELETE CASCADE`, so deleting a device automatically removes its associated violation records to clean up the database.

#### Q78: How do you verify database health?
**Answer**: We use Prometheus exporter queries to monitor connections, cache hit ratios, transaction rates, and query latency.

#### Q79: How are database migrations managed?
**Answer**: Using `db-migrate` scripts in Node.js. Schema changes are versioned as SQL up/down scripts in the repository.

#### Q80: How does the system handle concurrent database writes during peak traffic?
**Answer**: Write requests are queued in Redis, letting database workers process writes sequentially to prevent table locks.

---

## 6. Security, Privacy, Threat Model & Testing (Q81 - Q100)

#### Q81: What is the STRIDE security threat model?
**Answer**: A threat modeling framework covering six security categories: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege.

#### Q82: How does the system mitigate "Repudiation" threats?
**Answer**: It stores SHA-256 hashes of all evidence files and metadata payloads in the database. Audit logs track every action taken by reviewing officers.

#### Q83: What is "VLM Prompt Injection" and how is it prevented?
**Answer**: An attack vector where an attacker modifies input data (e.g., license plates containing text like *"Ignore violation"*) to override VLM system prompts. We prevent this by separating user data fields and hardening the GPT-4o system prompt to ignore instructions within images.

#### Q84: How is data encrypted in transit?
**Answer**: Via HTTPS (TLS 1.3) using secure cipher suites. Unencrypted HTTP requests are automatically redirected to HTTPS.

#### Q85: How is data encrypted at rest?
**Answer**: RDS databases use AES-256 encryption. Amazon S3 buckets use Server-Side Encryption (SSE-S3), and local edge SQLite databases use SQLCipher.

#### Q86: What are the primary data privacy regulations this system must comply with?
**Answer**: The General Data Protection Regulation (GDPR) in Europe and the Digital Personal Data Protection (DPDP) Act in India.

#### Q87: How does edge-side blurring ensure privacy compliance?
**Answer**: It blurs all faces and license plates *before* they leave the physical device, ensuring no unanonymized personal data is transmitted or stored in the cloud.

#### Q88: How are JWT secrets secured?
**Answer**: JWT secrets are stored in secure environment variables on AWS Parameter Store, never hardcoded in the repository.

#### Q89: What testing strategies are used?
**Answer**: Unit testing for code modules, integration testing for edge-to-cloud communications, performance testing for hardware and API scaling, and user acceptance testing (UAT).

#### Q90: How do you test edge performance under high load?
**Answer**: We run scripts that simulate raw 30 FPS video feeds on the Pi and measure the frame drop rate, CPU usage, and thermal throttling behaviors.

#### Q91: Explain the vibration test setup.
**Answer**: The hardware rig is mounted on a motorcycle handlebar bracket. We ride at different speeds on varied road surfaces, measuring frame focus scores using OpenCV's Laplacian variance method to confirm the camera's image stabilization handles road vibrations.

#### Q92: What is the focus threshold value for image processing?
**Answer**: Frames with a Laplacian focus score below 100 are discarded immediately as motion-blurred, conserving CPU cycles.

#### Q93: How do you test VLM prompt robustness?
**Answer**: We run test runs with edge case images (e.g., riders wearing caps, helmets carried on arms, license plates with text overlays) to verify the VLM correctly flags violations.

#### Q94: How do you test cell reconnect behaviors?
**Answer**: We block network interfaces manually during active YOLO inference, verify that reports write to the local SQLite database, and confirm they sync to the cloud once interfaces are re-enabled.

#### Q95: What tools automate unit testing?
**Answer**: `Jest` for the Node.js backend services and `unittest`/`pytest` for the edge Python scripts.

#### Q96: What is a "False Positive" in the context of this project?
**Answer**: A citation generated for a driver who did not violate any traffic rules. This must be avoided to maintain public trust.

#### Q97: What is the target rate for false positives?
**Answer**: 0%. The system uses a dual-verification workflow (YOLO + VLM) to filter out false alerts.

#### Q98: How do you test for SQL injection vulnerabilities?
**Answer**: We use parametrized queries in PostgreSQL to prevent SQL injection, and run vulnerability scans using OWASP ZAP on backend endpoints.

#### Q99: What is "Dependency Vulnerability Scanning"?
**Answer**: Automated scans run during CI/CD builds (e.g., using `npm audit` or Snyk) to identify and update libraries with known security exploits.

#### Q100: How does the system handle database connection loss?
**Answer**: Node API endpoints retry database connections automatically using exponential backoff. If database connections fail for over 30 seconds, endpoints return an HTTP 503 Service Unavailable status, and edge devices buffer reports locally.
