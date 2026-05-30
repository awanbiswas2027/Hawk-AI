# Document 10: UML Documentation

---

## 1. Use Case Diagram

The use case diagram defines interactions between actors (Commuters, Officers, Administrators, and VLM API) and the system.

```mermaid
leftToRightDirection
actor Commuter as "Commuter (Data Contributor)"
actor Officer as "Traffic Officer"
actor Admin as "System Administrator"
actor VLM as "OpenAI VLM API"

rectangle Hawk-AI_AI_System {
    usecase UC1 as "Register Edge Device"
    usecase UC2 as "Passive Capture & Sync"
    usecase UC3 as "Review Pending Queue"
    usecase UC4 as "Approve/Reject Citations"
    usecase UC5 as "Analyze Violation Hotspots"
    usecase UC6 as "Manage User Accounts"
    usecase UC7 as "Verify Violation & Extract Plate"
}

Commuter --> UC1
Commuter --> UC2
Officer --> UC3
Officer --> UC4
Officer --> UC5
Admin --> UC6
Admin --> UC5
VLM --> UC7
UC2 ..> UC7 : "<<includes>>"
UC7 ..> UC4 : "<<precedes>>"
```

---

## 2. Class Diagram

The core classes in the Cloud API Backend structure the business logic.

```mermaid
classDiagram
    class User {
        +UUID id
        +String email
        +String role
        +registerDevice() Device
    }
    class Device {
        +UUID id
        +String deviceSerial
        +String status
        +syncViolations() List
    }
    class Violation {
        +UUID id
        +DateTime occurrenceTime
        +Object geolocation
        +String violationClass
        +String status
        +submitToVLM() Citation
    }
    class Citation {
        +UUID id
        +String ticketNumber
        +String licensePlate
        +Float vlmConfidence
        +approve(officerId)
        +reject()
        +dispatch()
    }
    
    User "1" --> "*" Device : owns
    Device "1" --> "*" Violation : captures
    Violation "1" -- "0..1" Citation : generates
    User "1" --> "*" Citation : reviews
```

---

## 3. Sequence Diagram: Edge-Cloud Event Sync

Details the sequence of network handshakes when uploading and verifying a suspected violation.

```mermaid
sequenceDiagram
    autonumber
    participant Pi as Edge Raspberry Pi
    participant API as Cloud API Gateway
    participant S3 as Amazon S3 Bucket
    participant Queue as Redis Queue
    participant Worker as VLM Worker
    participant VLM as OpenAI GPT-4o API

    Pi->>API: POST /api/v1/ingest (Metadata JSON + image file)
    Note over API: Verify Device Key & Validate Coordinates
    API->>S3: Upload raw image
    S3-->>API: Return Image URI
    API->>Queue: Push Job {violation_id, image_uri}
    API-->>Pi: HTTP 202 Accepted (Sync Successful)
    Worker->>Queue: Poll next job
    Queue-->>Worker: Return Job Data
    Worker->>VLM: POST /chat/completions (Image URI + Prompt)
    VLM-->>Worker: Return JSON {license_plate: "KA03HA1234", confidence: 0.98}
    Note over Worker: Generate Citation PDF & Write to DB
    Worker->>API: Send Dispatch Trigger
```

---

## 4. Activity Diagram: Edge Detection Cycle

Shows the active control flow inside the Raspberry Pi edge client.

```mermaid
flowchart TD
    Start([Start System]) --> GetFrame[Grab Next Camera Frame]
    GetFrame --> GetGPS[Read GPS Serial Buffer]
    GetGPS --> RunYOLO[Execute YOLOv8-nano]
    RunYOLO --> CheckDet{Violation Detected?}
    CheckDet -->|No| ClearMem[Clear frame from RAM] --> GetFrame
    CheckDet -->|Yes| CropROI[Crop Violation Region of Interest]
    CropROI --> BlurNon[Blur non-violating plates and faces]
    BlurNon --> CheckNet{Network Connected?}
    CheckNet -->|Yes| Upload[POST to Cloud API] --> GetFrame
    CheckNet -->|No| Buffer[Write to Local SQLite DB] --> GetFrame
```

---

## 5. State Diagram: Violation Event Lifecycle

Tracks the database states of a single violation report.

```mermaid
stateDiagram-v2
    [*] --> PENDING : Event uploaded to Cloud
    PENDING --> VLM_PROCESSING : Worker pulls job from Redis
    
    state VLM_PROCESSING {
        [*] --> Analyzing
        Analyzing --> Extracting_Plate : OCR Pass
    }
    
    VLM_PROCESSING --> APPROVED : VLM Confidence > 95%
    VLM_PROCESSING --> HITL_REVIEW : VLM Confidence 75% - 95%
    VLM_PROCESSING --> REJECTED : VLM Confidence < 75%
    
    HITL_REVIEW --> APPROVED : Officer Approves
    HITL_REVIEW --> REJECTED : Officer Rejects
    
    APPROVED --> DISPATCHED : PDF generated and SMTP/API sent
    DISPATCHED --> [*]
    REJECTED --> [*]
```

---

## 6. Component Diagram

Shows the container boundaries of the deployed modules.

```mermaid
component {
    [React Admin Client] as UI
    [Express Gateway] as Gateway
    [VLM Processor] as Worker
    [Postgres DB] as DB
    [Redis Store] as Cache
    [Mender Client] as Mender

    UI --> Gateway : "HTTPS API Calls"
    Gateway --> Cache : "BullMQ Jobs"
    Worker --> Cache : "Poll Jobs"
    Worker --> DB : "Write SQL"
    Gateway --> DB : "Read SQL"
    Mender --> Gateway : "Check Updates"
}
```
