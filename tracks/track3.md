# Technical Documentation: Medication Overview and HCERT (Track 3)

This document describes the technical implementation of the Medication Overview (MEOW) flow and the generation of Health Certificates (HCERT) for medications between Country A and Country B.

## Overview

The flow allows a Health Information System (HIS) in Country A to generate a Medication Overview for a patient. The patient can then retrieve this overview via a mobile app, select a medication, and generate a secure HCERT (QR Code) to be verified at a pharmacy in Country B.

---

## Technical Details and FHIR Interactions

### Paso 0: Generar Medication Overview (País A)

The HIS of Country A identifies the patient and prepares the medication summary.

**1. Patient Discovery (ITI-78):**
```bash
curl -G http://localhost:8080/fhir/Patient \
     --data-urlencode "identifier=12345" \
     -H "Accept: application/fhir+json"
```

**2. Terminology Lookup (ITI-98 / ITI-101):**
Retrieve medication codes (e.g., SNOMED CT) from the terminology server.
```bash
curl -G http://localhost:8082/fhir/ValueSet/$expand \
     --data-urlencode "url=http://snomed.info/sct?fhir_vs" \
     --data-urlencode "filter=Atorvastatin" \
     -H "Accept: application/fhir+json"
```

**3. Provide Document Bundle (ITI-65):**
The HIS sends the Medication Overview Transaction to the National Node on port **8080**. This includes the Patient, DocumentReference, and the MedicationOverview Bundle.
```bash
curl -X POST http://localhost:8080/fhir \
     -H "Content-Type: application/fhir+json" \
     -d @examples/track3/iti65-transaction-medication.json
```

---

### Paso 1: Generar QR Medicamento HCERT (Patient App)

The patient retrieves their medications and generates a verifiable QR code.

**1. Find Document References (ITI-67):**
Search for "Medication summary" documents (LOINC `56445-0`).
```bash
curl -G http://localhost:8080/fhir/DocumentReference \
     --data-urlencode "patient.identifier=12345" \
     --data-urlencode "type=56445-0" \
     --data-urlencode "status=current" \
     -H "Accept: application/fhir+json"
```
```

**2. Retrieve Medication Overview (ITI-68):**
```bash
# Example ID [UUID] obtained from the DocumentReference content URL
curl -X GET http://localhost:8080/fhir/Bundle/68c15694-52f1-4171-bc01-e63d666d2a71 \
     -H "Accept: application/fhir+json"
```

**3. Create QR Medicamento HCERT ($meow):**
The App calls the `$meow` operation on the IPS Mediator (port **3000**) using a **GET** request to generate the HCERT for the selected Medication Overview.
```bash
curl -X GET http://localhost:3000/fhir/Bundle/68c15694-52f1-4171-bc01-e63d666d2a71/$meow \
     -H "Accept: application/json"
```

---

### Paso 2: Verificación en País B (Pharmacy)

The pharmacist in Country B scans the QR code to verify the medication's authenticity.

**1. Validate Signature (GDHCN):**
The pharmacy system validates the HCERT signature against the Global Digital Health Certification Network.

**2. Validate HCERT Content (ITB):**
The Internal Testing/Validation Tool (ITB) ensures the HCERT content is compliant with the MEOW profile. An example instance of this validator is available at: [https://hcert-validator.racsel.org/ui](https://hcert-validator.racsel.org/ui)

**3. Visualization:**
The pharmacy system displays the medication details (e.g., Atorvastatin 20 mg) for dispensing.

---

## Example Files Summary

| File | Description |
| --- | --- |
| `iti65-transaction-medication.json` | MHD Transaction for submitting a Medication Overview. |
| `medication-overview-example.json` | Sample Medication Overview Bundle compliant with the IHE MEOW profile. |
| `track3.mmd` | Sequence diagram defining the technical flow. |
