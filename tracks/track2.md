# Technical Documentation: International Certificate of Vaccination or Prophylaxis (Track 2)

This document describes the technical implementation of the International Certificate of Vaccination or Prophylaxis (ICVP) flow, which allows patients to generate a verifiable digital version of their vaccination certificates.

## Overview

The flow involves creating an IPS document that includes ICVP-specific immunization data. The patient can then retrieve this document and generate a secure HCERT (QR Code) for international travel and verification.

---

## Technical Details and FHIR Interactions

### Paso 0: Generar IPS (País A)

The Healthcare Information System (HIS) in Country A generates an IPS compliant with the ICVP profile.

**1. Patient Discovery (ITI-78):**
```bash
curl -G http://localhost:8080/fhir/Patient \
     --data-urlencode "identifier=19034071-6" \
     -H "Accept: application/fhir+json"
```

**2. Terminology Lookup (ITI-98 / ITI-101):**
Retrieve ICVP vaccine codes (e.g., Yellow Fever) from the terminology server.
```bash
curl -G http://localhost:8082/fhir/ValueSet/$expand \
     --data-urlencode "url=http://smart.who.int/pcmt-vaxprequal/CodeSystem/PreQualVaccineType" \
     --data-urlencode "filter=Yellow Fever" \
     -H "Accept: application/fhir+json"
```

**3. Save IPS ICVP (ITI-65 - Provide Document Bundle):**
Store the IPS Bundle in the National Node (port **8080**).
```bash
curl -X POST http://localhost:8080/fhir \
     -H "Content-Type: application/fhir+json" \
     -d @examples/example_icvp_0511.json
```

---

### Paso 1: Generar QR ICVP (Patient App)

The patient retrieves the IPS and generates the digital certificate.

**1. Find Document References (ITI-67):**
```bash
curl -G http://localhost:8080/fhir/DocumentReference \
     --data-urlencode "patient.identifier=19034071-6" \
     --data-urlencode "status=current" \
     -H "Accept: application/fhir+json"
```

**2. Retrieve IPS ICVP (ITI-68):**
```bash
# Example [UUID] obtained from DocumentReference
curl -X GET http://localhost:8080/fhir/Bundle/f50a5146-7d08-4f4d-b7a9-eb8a05d513a0 \
     -H "Accept: application/fhir+json"
```

**3. Create QR ICVP ($icvp):**
The App calls the `$icvp` operation on the IPS Mediator (port **3000**) via a **GET** request to generate the verifiable QR code.
```bash
curl -X GET http://localhost:3000/fhir/Bundle/f50a5146-7d08-4f4d-b7a9-eb8a05d513a0/$icvp \
     -H "Accept: application/json"
```

---

### Paso 2: Verificación en País B

The border authority or healthcare provider in Country B verifies the certificate.

**1. Validate Signature:**
The system validates the HCERT signature against the Global Digital Health Certification Network (GDHCN).

**2. Validate Content:**
The system uses the Internal Testing Tool (ITB) to ensure the immunization data (e.g., Yellow Fever) matches the required international standards. An example instance of this validator is available at: [https://hcert-validator.racsel.org/ui](https://hcert-validator.racsel.org/ui)

**3. Visualization:**
The ICVP details are displayed to the authority for final clearance.

---

## Example Files Summary

| File | Description |
| --- | --- |
| `example_icvp_0511.json` | Sample IPS Bundle containing ICVP-compliant immunization resources. |
| `track2.mmd` | Sequence diagram defining the technical flow. |
