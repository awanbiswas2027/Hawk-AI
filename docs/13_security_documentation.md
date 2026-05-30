# Document 13: Security Documentation

---

## 1. STRIDE Threat Model

The Hawk-AI system security is evaluated using the STRIDE threat modeling framework:

| Threat Category | Specific Threat | Target Component | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Rogue edge devices uploading fake/simulated violations. | Cloud Ingestion Gateway | Require hardware-tied device serials and unique cryptographically signed device keys (`X-Device-API-Key`) verified on every API request. |
| **Tampering** | Man-in-the-middle modification of captured evidence images. | In-Transit Data | Enforce strict HTTPS (TLS 1.3) protocol with certificate pinning on the edge Python client to prevent proxy interception. |
| **Repudiation** | User denies committing a violation or police denies issuing a ticket. | DB System Records | Store SHA-256 hashes of all raw captured evidence files and metadata payloads in the database. Logs record timestamped signatures of reviewing officers. |
| **Information Disclosure** | Leak of innocent citizen faces and non-violating license plates. | Local Edge Camera / Cloud Storage | **Edge-Side Blurring**: Apply Gaussian blurs to uninvolved faces and plates on the edge RAM buffer *before* saving to disk or uploading. |
| **Denial of Service** | Flooding the API ingestion system to drive up VLM API costs. | Ingestion API / OpenAI API | Set strict rate limits (Rate limiting headers) at the AWS Load Balancer level. Use Redis BullMQ queue buffers to limit concurrent GPT-4o API transactions. |
| **Elevation of Privilege** | Attacker injects prompt commands into the VLM. | Cloud VLM Orchestrator | Input formatting uses strict JSON boundaries. GPT-4o system prompt is hardened to ignore user inputs or visual text containing command overrides. |

---

## 2. Authentication & Authorization Strategy

### 2.1 Edge Device Authentication
Edge devices authenticate using a unique pre-shared key (PSK) generated at device registration. On boot, the device completes a handshake:
1. Device sends serial and encrypted signature of its local timestamp.
2. Ingestion server validates signature against DB public key and returns an active session token valid for 24 hours.

### 2.2 Role-Based Access Control (RBAC) Matrix
User portal security is managed via explicit role boundaries:

| API Interface Endpoint | Commuter | Traffic Officer | System Administrator |
| :--- | :---: | :---: | :---: |
| `POST /api/v1/ingest` | ✔ (Device Only) | ✘ | ✘ |
| `GET /api/v1/portal/review-queue` | ✘ | ✔ | ✔ |
| `POST /api/v1/portal/citation/resolve` | ✘ | ✔ | ✘ |
| `GET /api/v1/portal/analytics` | ✘ | ✔ | ✔ |
| `POST /api/v1/admin/devices` | ✘ | ✘ | ✔ |

---

## 3. Data Protection: Edge Anonymization

To comply with global privacy rules (GDPR/DPDP), the system enforces privacy-by-design at the edge:
* **Principle of Minimality**: Raw video feeds are never saved to permanent disk storage. Frames reside inside a rolling volatile ring buffer in RAM and are overwritten within 5 seconds if no violation is triggered.
* **Pixel Blurring**: If YOLO flags a violation (e.g., wrong-way car), the anonymizer finds all bystander faces and non-violating plates. It maps OpenCV Gaussian blur filters with a kernel size of $23 \times 23$ to make face recovery impossible, leaving only the infraction subject clear.

```text
[Raw Frame Capture] 
       │
       ▼
[Identify Bounding Boxes] ──► Violating Bounding Box (Do not blur plate)
       │
       ▼
[Face & Plate Haar Classifiers]
       │
       ▼
[Overlay Gaussian Mask (Kernel: 23x23)] ──► Bystander Faces & Non-Violating Plates
       │
       ▼
[Write Blurred Payload to Disk/Upload]
```

---

## 4. Encryption Specifications

* **Data In-Transit**: Enforce TLS 1.3 protocol. Cipher suite configuration: `TLS_AES_256_GCM_SHA384` for all API endpoints.
* **Data At-Rest**:
  * PostgreSQL DB: Encrypted via AES-256 transparent data encryption (TDE) on AWS RDS.
  * Amazon S3: Server-Side Encryption (SSE-S3) enabled by default on all bucket uploads.
  * Edge Local SQLite: Stored in an encrypted database container using **SQLCipher** to prevent raw disk reads in case the hardware is physically stolen.

---

## 5. OWASP API Top 10 Mitigations

1. **API1:2023 - Broken Object Level Authorization (BOLA)**: Every query to fetch violation or device details checks if the logged-in user belongs to the authority tenancy or owns the target device before returning records.
2. **API3:2023 - Broken Object Level Authorization**: We do not return raw database models directly. Data payloads are filtered through serialized transfer objects (DTOs) to prevent exposing internal device system parameters.
3. **API8:2023 - Security Misconfiguration**: Default ports (such as database port 5432) are bound to the internal Docker network and are inaccessible to the external internet. All CORS configurations are locked down to explicit domain subnets.
