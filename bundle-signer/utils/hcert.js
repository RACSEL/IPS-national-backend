const crypto = require('crypto');
const cbor = require('cbor');
const base45 = require('base45');
const pako = require('pako');

/**
 * Derives KID from Private Key
 */
function getKid(privateKeyPem) {
  try {
    const privateKey = crypto.createPrivateKey(privateKeyPem);
    const publicKey = crypto.createPublicKey(privateKey);
    const publicKeyDer = publicKey.export({ type: 'spki', format: 'der' });
    return crypto.createHash('sha256').update(publicKeyDer).digest().slice(0, 8);
  } catch (err) {
    console.error('Error deriving KID:', err.message);
    return Buffer.from('default_kid');
  }
}

/**
 * Signs a payload and returns HC1 string
 */
function signHcert(payload, privateKeyPem, issuer = 'XX', subclaim = -6, expirationMonths = 12) {
  const now = Math.floor(Date.now() / 1000);
  const exp = now + (expirationMonths * 30 * 24 * 60 * 60);

  // 1. Build CWT Structure
  const hcertMap = new Map();
  hcertMap.set(parseInt(subclaim, 10), payload);

  const cwtMap = new Map();
  cwtMap.set(1, issuer);          // Issuer
  cwtMap.set(6, now);             // Issued At
  cwtMap.set(4, exp);             // Expiration
  cwtMap.set(-260, hcertMap);     // Health Certificate Claim

  const cborPayload = cbor.encode(cwtMap);

  // 2. Prepare COSE Headers
  const kid = getKid(privateKeyPem);

  // Protected header: alg: -7 (ES256)
  const protectedHeader = cbor.encode(new Map([[1, -7]]));

  // Unprotected header: kid: 4
  const unprotectedHeader = new Map([[4, kid]]);

  // 3. Create Signature Structure (Sig_structure)
  const sigStructure = cbor.encode([
    'Signature1',
    protectedHeader,
    Buffer.alloc(0), // external_aad
    cborPayload,
  ]);

  // 4. Sign
  const signature = crypto.sign(
    'sha256',
    sigStructure,
    {
      key: privateKeyPem,
      dsaEncoding: 'ieee-p1363', // COSE uses raw R+S
    },
  );

  // 5. Build COSE_Sign1 array
  const coseSign1 = [
    protectedHeader,
    unprotectedHeader,
    cborPayload,
    signature,
  ];

  const taggedCose = new cbor.Tagged(18, coseSign1);
  const signedCbor = cbor.encode(taggedCose);

  // 6. Compress (ZLib)
  const compressed = pako.deflate(signedCbor);

  // 7. Base45 Encode
  const b45 = base45.encode(compressed);

  // 8. Prefix
  return `HC1:${b45}`;
}

/**
 * Transforms FHIR resources to ICVP payload
 */
function buildICVPPayload(patient, immunization) {
  const name = patient.name?.[0]?.text || (`${patient.name?.[0]?.given?.join(' ')} ${patient.name?.[0]?.family}`);
  const dob = patient.birthDate;

  const productIDExtension = immunization.extension?.find((e) => e.url?.includes('StructureDefinition/ProductID'));
  const productID = productIDExtension?.valueCoding?.code;

  if (!productID) {
    throw new Error('ProductID extension not found in immunization');
  }

  const [dt] = immunization.occurrenceDateTime?.split('T') || [];
  const payload = {
    n: name,
    dob,
    v: {
      vp: productID,
      dt,
      bo: immunization.lotNumber,
    },
  };

  // Optional fields
  if (patient.gender) {
    payload.s = patient.gender;
  }

  const nationalityExt = patient.extension?.find((e) => e.url?.includes('/StructureDefinition/patient-nationality'));
  if (nationalityExt?.valueCodeableConcept?.coding?.[0]?.code) {
    payload.ntl = nationalityExt.valueCodeableConcept.coding[0].code;
  }

  const taxIdentifier = patient.identifier?.find((id) => id.type?.coding?.some((coding) => coding.code === 'TAX'))?.value || patient.identifier?.[0]?.value;
  if (taxIdentifier) {
    payload.nid = taxIdentifier;
    payload.ndt = 'NI'; // Default to NI if we have an identifier
  }

  const guardianName = `${patient.contact?.[0]?.name?.[0]?.given?.join(' ') || ''} ${patient.contact?.[0]?.name?.[0]?.family || ''}`;
  if (guardianName.trim()) {
    payload.gn = guardianName.trim();
  }

  if (immunization.performer?.[0]?.actor?.display) {
    payload.v.cn = immunization.performer[0].actor.display;
  }

  if (immunization.manufacturer?.display) {
    payload.v.is = immunization.manufacturer.display;
  }

  if (immunization.occurrenceDateTime) {
    const [vls] = immunization.occurrenceDateTime.split('T');
    payload.v.vls = vls;
  }

  if (immunization.expirationDate) {
    const [vle] = immunization.expirationDate.split('T');
    payload.v.vle = vle;
  }

  return payload;
}

/**
 * Transforms FHIR resources to MedicationOverview payload
 */
function buildMeOWPayload(patient, medicationStatement) {
  const name = patient.name?.[0]?.text || (`${patient.name?.[0]?.given?.join(' ')} ${patient.name?.[0]?.family}`);
  const dob = patient.birthDate;
  const gender = patient.gender;

  const payload = {
    n: name,
    dob,
    s: gender,
    m: [],
  };

  // Optional patient fields
  const nationalityExt = patient.extension?.find((e) => e.url?.includes('/StructureDefinition/patient-nationality'));
  if (nationalityExt?.valueCodeableConcept?.coding?.[0]?.code) {
    payload.nt = nationalityExt.valueCodeableConcept.coding[0].code;
  }

  const taxIdentifier = patient.identifier?.find((id) => id.type?.coding?.some((coding) => coding.code === 'TAX')) || patient.identifier?.[0];
  if (taxIdentifier) {
    payload.id = taxIdentifier.value;
    payload.dt = taxIdentifier.type?.coding?.[0]?.code || 'NI';
  }

  // Medication line
  const medicationCode = medicationStatement.medicationCodeableConcept?.coding?.[0]?.code;
  if (!medicationCode) {
    throw new Error('Medication code not found in MedicationStatement');
  }

  const [es] = medicationStatement.effectivePeriod?.start?.split('T') || [];
  const [ee] = medicationStatement.effectivePeriod?.end?.split('T') || [];
  const [da] = medicationStatement.dateAsserted?.split('T') || [];

  const treatmentLine = {
    m: medicationCode,
  };

  if (es) treatmentLine.es = es;
  if (ee) treatmentLine.ee = ee;
  if (da) treatmentLine.da = da;

  if (medicationStatement.dosage?.[0]?.text) {
    treatmentLine.d = medicationStatement.dosage[0].text;
  }
  if (medicationStatement.reasonCode?.[0]?.text) {
    treatmentLine.r = medicationStatement.reasonCode[0].text;
  }

  // Adherence status
  if (medicationStatement.adherence?.code?.coding?.[0]?.code) {
    treatmentLine.a = medicationStatement.adherence.code.coding[0].code;
  }

  payload.m.push(treatmentLine);

  return payload;
}

/**
 * Creates a FHIR Bundle response for HCERT
 */
function createHCERTBundleResponse(hc1, typeCode = 'icvp', typeSystem = 'http://worldhealthorganization.github.io/icvp/CodeSystem/DVC-QR-Type-CodeSystem') {
  return {
    resourceType: 'Bundle',
    type: 'batch-response',
    entry: [
      {
        resource: {
          resourceType: 'DocumentReference',
          status: 'current',
          type: {
            coding: [
              {
                system: typeSystem,
                code: typeCode,
              },
            ],
          },
          content: [
            {
              attachment: {
                contentType: 'plain/text',
                data: hc1,
              },
              format: {
                code: 'hc1',
              },
            },
          ],
        },
        response: {
          status: '200',
        },
      },
    ],
  };
}

module.exports = {
  signHcert,
  buildICVPPayload,
  buildMeOWPayload,
  createHCERTBundleResponse,
};
