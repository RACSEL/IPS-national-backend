# Technical Documentation: IPS Exchange via Verifiable Health Links (Track 1.1)

This document describes the technical implementation of the International Patient Summary (IPS) exchange flow using Verifiable Health Links (VHL) between Country A (Origin) and Country B (Destination).

## Overview

The flow allows a patient from Country A to travel to Country B, share their medical history (IPS) securely via a VHL (QR Code), and return with an updated history.

---

## Technical Details and FHIR Interactions

### Paso 0: Generar IPS (País A)

The Healthcare Information System (HIS) in Country A identifies the patient, looks up terminologies, and stores the IPS in the National Node.

**1. Patient Discovery (ITI-78):**
```bash
curl -G http://localhost:8080/fhir/Patient \
     --data-urlencode "identifier=18922652-7" \
     -H "Accept: application/fhir+json"
```

**2. Terminology Lookup (ITI-98 / ITI-101):**
Query the terminology server (Snowstorm) for SNOMED CT or ICD-11 codes.
```bash
curl -G http://localhost:8082/fhir/ValueSet/$expand \
     --data-urlencode "url=http://snomed.info/sct?fhir_vs" \
     --data-urlencode "filter=hypertension" \
     -H "Accept: application/fhir+json"
```

**3. Save IPS (ITI-65 - Provide Document Bundle):**
Store the generated IPS in National Node A via the IPS Mediator.
```bash
curl -X POST http://localhost:3000/fhir/Bundle \
     -H "Content-Type: application/json" \
     -d @examples/ips-lac-webinar.json
```

---

### Paso 1: Origen (País A) - Patient Mobile App

The patient retrieves their IPS and generates a VHL to share it.

**1. Find Document References (ITI-67):**
```bash
curl -G http://localhost:8080/fhir/DocumentReference \
     --data-urlencode "patient.identifier=18922652-7" \
     --data-urlencode "status=current" \
     -H "Accept: application/fhir+json"
```

**2. Retrieve IPS (ITI-68):**
```bash
# Using the ID obtained from DocumentReference
curl -X GET http://localhost:8080/fhir/Bundle/f50a5146-7d08-4f4d-b7a9-eb8a05d513a0 \
     -H "Accept: application/fhir+json"
```

**3. Create VHL (VSHC Issuance):**
The app sends the IPS content to the VHL Service to generate the link and QR code.
```bash
curl -X POST http://localhost:8182/v2/vshcIssuance \
     -H "Content-Type: application/json" \
     -d '{
       "expiresOn": "2026-12-31T23:59:59Z",
       "jsonContent": "{\"resourceType\":\"Bundle\",...}" 
     }'
```
*(Note: `jsonContent` should be the stringified version of the IPS Bundle found in `examples/ips-lac-webinar.json`)*

---

### Paso 2: Destino (País B)

The patient presents the QR code to the HIS in Country B.

**1. Validate VHL (VSHC Validation):**
The HIS in Country B validates the QR code content (HC1:...) against the GDHCN trust network.
```bash
curl -X POST http://localhost:8182/v2/vshcValidation \
     -H "Content-Type: application/json" \
     -d '{
       "qrCodeContent": "HC1:6BFOX..."
     }'
```

Additionally, the content can be manually validated using the **RACSEL ITB Validator**: [https://hcert-validator.racsel.org/ui](https://hcert-validator.racsel.org/ui)

**2. Retrieve VHL Manifest:**
After validation, the HIS requests the manifest which lists the available resources.
```bash
curl -X POST http://localhost:8182/v2/manifests/1a60eefd-8632-4b62-9494-8685d17017b2 \
     -H "Content-Type: application/json" \
     -d '{
       "recipient": "LACPass HIS Client",
       "passcode": "1234"
     }'
```

**3. Retrieve IPS Content:**
The HIS retrieves the actual IPS JSON data using the link provided in the manifest.
```bash
curl -X GET http://localhost:8182/v2/ips-json/1a60eefd-8632-4b62-9494-8685d17017b2 \
     -H "Accept: application/fhir+json"
```

**4. Record Local Consultation (ITI-65):**
HIS Country B stores the new IPS (IPS_B) generated during the local visit.
```bash
curl -X POST http://localhost:3000/fhir/Bundle \
     -H "Content-Type: application/json" \
     -d @examples/ips-lac-webinar.json
```

---

### Paso 3: Retorno (País A)

The patient returns to Country A and merges the information.

**1. Merge IPS:**
The patient app performs a merge of the original `IPS_A` and the new `IPS_B`.

**2. Update National Node A:**
The merged IPS is stored back in Country A's national infrastructure.
```bash
curl -X POST http://localhost:3000/fhir/Bundle \
     -H "Content-Type: application/json" \
     -d @merged-ips.json
```

---

## Example Files Summary

| File | Description |
| --- | --- |
| `ips-lac-webinar.json` | Baseline IPS Bundle for transfers and VHL creation. |
| `track11.mmd` | Sequence diagram for the entire cross-border flow. |
