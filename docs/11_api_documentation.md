# Document 11: API Documentation

---

## 1. Authentication & Security Headers

All cloud API endpoints (`https://api.hawk-ai.ai/v1/`) require specific authentication headers.

### 1.1 Edge Device Authentication
Edge devices authenticate using a unique API Key generated during device registration.
* **Header**: `X-Device-API-Key: <unique_api_key>`
* **Header**: `X-Device-Serial: <device_serial_number>`

### 1.2 User Portal Authentication
Web client users must authenticate via a JWT Bearer Token obtained from the login endpoint.
* **Header**: `Authorization: Bearer <jwt_token>`

---

## 2. API Endpoints

### 2.1 Device Ingestion: Send Suspected Violation
Receives real-time or synced violation payloads from the edge devices.

* **URL**: `/api/v1/ingest`
* **Method**: `POST`
* **Content-Type**: `multipart/form-data`
* **Rate Limiting**: Maximum 60 requests/minute per API key.
* **Headers**: Requires Edge Device Authentication headers.

#### Request Parameters (Multipart Form Fields)
* `metadata`: JSON string matching the metadata schema.
* `evidence_file`: Binary file crop (JPEG/PNG, max 2MB).

```json
// Example 'metadata' JSON field value
{
  "occurrence_time": "2026-05-31T08:30:15Z",
  "geolocation": {
    "lat": 12.9716,
    "lon": 77.5946
  },
  "speed_kmh": 24.5,
  "violation_class": "NO_HELMET",
  "edge_confidence": 0.892
}
```

#### Response (Success `202 Accepted`)
```json
{
  "status": "success",
  "message": "Violation payload accepted for VLM verification queue.",
  "violation_id": "d8a50b3e-5948-4987-d9f6-1155ae853945"
}
```

#### Error Responses
* **401 Unauthorized**: If `X-Device-API-Key` is missing or invalid.
* **400 Bad Request**: If GPS coordinates or required parameters are malformed.
* **429 Too Many Requests**: If rate limits are exceeded.

---

### 2.2 User Auth: Log In User
Authenticates users (Commuters, Officers, Admins) and returns a session JWT.

* **URL**: `/api/v1/auth/login`
* **Method**: `POST`
* **Content-Type**: `application/json`
* **Rate Limiting**: Maximum 5 requests/minute per IP address.

#### Request Body
```json
{
  "email": "s.patil@police.gov.in",
  "password": "SecurePassword123"
}
```

#### Response (Success `200 OK`)
```json
{
  "status": "success",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImI1ZTI4YTFjLTM3MjY...",
  "user": {
    "id": "b5e28a1c-3726-4765-b7d4-9933ec631723",
    "full_name": "Officer Patil",
    "role": "OFFICER"
  }
}
```

#### Error Responses
* **401 Unauthorized**: Invalid email or password credentials.

---

### 2.3 Portal: Get Review Queue
Used by the web admin client to retrieve citations flagged for Human-in-the-Loop review.

* **URL**: `/api/v1/portal/review-queue`
* **Method**: `GET`
* **Headers**: Requires User Portal Authentication.
* **Query Parameters**:
  * `page` (optional): Default 1.
  * `limit` (optional): Default 20.
  * `violation_class` (optional): Filter by infraction class.

#### Response (Success `200 OK`)
```json
{
  "status": "success",
  "data": {
    "total_records": 1,
    "current_page": 1,
    "records": [
      {
        "violation_id": "f2a1b3c4-9843-2287-c812-774e1e32d665",
        "occurrence_time": "2026-05-31T09:12:45Z",
        "violation_class": "NO_HELMET",
        "edge_confidence": 0.812,
        "vlm_confidence": 0.845,
        "image_url": "https://s3.hawk-ai.ai/evidence/20260531_f2a1b3c4.jpg",
        "vlm_reasoning": "Rider is wearing a blue baseball cap. Borderline helmet infraction.",
        "location": {
          "lat": 12.9622,
          "lon": 77.6433
        }
      }
    ]
  }
}
```

---

### 2.4 Portal: Approve/Reject Citation
Submit officer action on borderline citations.

* **URL**: `/api/v1/portal/citation/resolve`
* **Method**: `POST`
* **Headers**: Requires User Portal Authentication.

#### Request Body
```json
{
  "violation_id": "f2a1b3c4-9843-2287-c812-774e1e32d665",
  "action": "APPROVE", // "APPROVE" or "REJECT"
  "license_plate": "KA04JD8912" // Verified or corrected plate number
}
```

#### Response (Success `200 OK`)
```json
{
  "status": "success",
  "message": "Citation resolved and dispatched.",
  "citation_id": "774e1e32-d665-4f2a-b3c4-98432287c812",
  "ticket_number": "CIT-2026-009842"
}
```
