# Technical Documentation: Cross-border Teleconsultation Flow (Track 12)

This document describes the technical implementation of the teleconsultation flow between Country A (Consumer) and Country B (Responder).

## Prerequisites

Before starting the flow, the following Organization resources must exist on the server to satisfy the references in the `ServiceRequest`.

**1. Create Requester Organization (Uruguay):**
```bash
curl -X PUT http://localhost:8080/fhir/Organization/hospital-uy \
     -H "Content-Type: application/fhir+json" \
     -d @examples/track12/organization-uy.json
```

**2. Create Performer Organization (Panama):**
```bash
curl -X PUT http://localhost:8080/fhir/Organization/pais-panama \
     -H "Content-Type: application/fhir+json" \
     -d @examples/track12/organization-panama.json
```

---

## Technical Details and FHIR Interactions

All examples assume a FHIR server running at `http://localhost:8080/fhir`.

### 1. Initiation: POST /ServiceRequest

The HIS of Country A sends a `ServiceRequest` to National Node A.

**Request:**
```bash
curl -X POST http://localhost:8080/fhir/ServiceRequest \
     -H "Content-Type: application/fhir+json" \
     -d @examples/track12/serviceRequest.json
```

---

### 2. Discovery: Find Pending Requests (Country B)

National Node B (or HIS Country B) queries National Node A to find pending interconsultation requests assigned to their organization.

**Request:**
```bash
curl -G http://localhost:8080/fhir/ServiceRequest \
     --data-urlencode "performer=Organization/pais-panama" \
     --data-urlencode "status=active" \
     -H "Accept: application/fhir+json"
```

---

### 3. Providing the Report: MHD ITI-65 (Provide Document Bundle)

The HIS Country B sends the report using an MHD Transaction Bundle. This bundle includes the **Patient**, the **DocumentReference**, and the **clinical Bundle** (document).

**Request:**
```bash
curl -X POST http://localhost:8080/fhir \
     -H "Content-Type: application/fhir+json" \
     -d @examples/track12/iti65-transaction.json
```

---

### 4. Discovery: MHD ITI-67 (Find Document References)

HIS Country A queries National Node A to find available documents. To filter out unrelated documents (like the original IPS), we search specifically for the **Referral note** type (`57133-1`) defined in our transaction.

**Request:**
```bash
curl -G http://localhost:8080/fhir/DocumentReference \
     --data-urlencode "patient.identifier=urn:oid:2.16.858.1.858.1.1.1|12345678" \
     --data-urlencode "status=current" \
     --data-urlencode "type=http://loinc.org|57133-1" \
     -H "Accept: application/fhir+json"
```

**Response Example:** [iti67-response.json](./examples/iti67-response.json)

---

### 5. Retrieval: MHD ITI-68 (Retrieve Document)

HIS Country A retrieves the document using the ID found in the previous step.

**Request:**
```bash
curl -X GET http://localhost:8080/fhir/Bundle/03e4a890-b152-481a-9ca5-685e03550a08 \
     -H "Accept: application/fhir+json"
```

---

### 6. Closure: PATCH /ServiceRequest (Country A)

Once the response is received and stored, Country A closes the `ServiceRequest` to indicate the process is complete. 

**Request (Assuming ID [ID_SOLICITUD] was obtained in Step 1 or 2):**
```bash
curl -X PATCH http://localhost:8080/fhir/ServiceRequest/[ID_SOLICITUD] \
     -H "Content-Type: application/json-patch+json" \
     -d '[{"op": "replace", "path": "/status", "value": "completed"}]'
```

---

## Example Files Summary

| File | Description |
| --- | --- |
| `organization-uy.json` | Organization for the requester center. |
| `organization-panama.json` | Organization for the destination country node. |
| `serviceRequest.json` | Initial request for teleconsultation. |
| `iti65-transaction.json` | MHD Transaction for submitting the report. |
