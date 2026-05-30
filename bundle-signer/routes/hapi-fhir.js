const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const { v4: uuidv4 } = require('uuid');
const canonicalize = require('../utils/canonicalize');
const { createDocumentReference, createSubmissionSet } = require('../utils/transactions');
const { buildDDCCQR } = require('../utils/ddcc');
const { buildDVCQR } = require('../utils/dvc');
const { buildICVPQR } = require('../utils/icvp');
const {
  buildICVPPayload, buildMeOWPayload, signHcert, createHCERTBundleResponse,
} = require('../utils/hcert');

const router = express.Router();

/*
 *  Will pass all request to FHIR server, but will sign all bundle requests
 *  And if a bundle document is sent, it will force it to create all resources in it
 */

/**
 *
 * @param body of the request
 * @param privateKey of the signer
 * @returns Signed body
 */
function addSignature(body, privateKey) {
  // Only sign bundles and bundle document
  if (body.resourceType !== 'Bundle' && body.type !== 'document') {
    return body;
  }
  const sign = crypto.sign('SHA256', canonicalize(body), privateKey);
  const signature = {
    type: [
      {
        system: 'urn:iso-astm:E1762-95:2013',
        code: '1.2.840.10065.1.12.1.5',
      },
    ],
    when: new Date().toISOString(),
    who: { // Party represented, can be Practitioner, PractitionerRoles, RelatedPerson, Organization
      identifier: { // Identifier of the signer in a system
        value: 'LACPass',
      },
    },
    data: sign.toString('base64'),
  };
  return Object.assign(body, { signature });
}

async function validateIPS(ips) {
  try {
    const val = await axios.request({
      url: 'http://lacpass.create.cl:5002/api/ips-validator',
      method: 'POST',
      data: {
        ips,
      },
    });
    return val.data;
  } catch (e) {
    return {
      validate: false,
      error: 'Request body is not a valid IPS',
    };
  }
}

/* Provide Document ITI-65. */
router.all('/Bundle', async (req, res) => {
  try {
    console.log('ITI-65');
    const FHIR_URL = req.app.get('hapiFhir');
    const FHIR_EXTERNAL_URL = req.app.get('externalFhir');

    const validation = await validateIPS(req.body);
    if (validation.validate == false) {
      res.status(400);
      res.send(validation);
      return;
    }

    req.body = addSignature(req.body, req.app.get('privateKey'));
    const originalBundleIPS = JSON.parse(JSON.stringify(req.body));
    const transaction = {
      resourceType: 'Bundle',
      id: uuidv4(),
      meta: {
        profile: [
          'https://profiles.ihe.net/ITI/MHD/StructureDefinition/IHE.MHD.Minimal.ProvideBundle',
        ],
        security: [
          {
            system: 'http://terminology.hl7.org/CodeSystem/v3-ActReason',
            code: 'HTEST',
          },
        ],
      },
      type: 'transaction',
      timestamp: new Date().toISOString(),
      entry: [],
    };

    if (req.body?.type === 'document' && req.method === 'POST') {
      // Create a copy of the original Bundle IPS
      const bundleIPS = JSON.parse(JSON.stringify(req.body));

      let docId = bundleIPS.id;
      if (docId == null) {
        docId = uuidv4();
        bundleIPS.id = docId;
      }

      // Convert the document to a transaction to force the creation of resources
      // This only will happen if a new Bundle is created, it does not work for PUT method
      // Add the document as an entry, so it is also created
      // req.body.entry.forEach((e, index) => {
      //   let url = e.resource.id ? `${e.resource.resourceType}/${e.resource.id}` : undefined;
      //   // console.log(url);
      //   req.body.entry[index].request = {
      //     method: req.method,
      //     url: url
      //   };
      //   if(url){
      //     req.body.entry[index].fullUrl = url;
      //     bundleIPS.entry[index].fullUrl = url;
      //   }
      // });

      const patient = JSON.parse(JSON.stringify(bundleIPS.entry.find((e) => e.resource && e.resource.resourceType == 'Patient')));
      patient.request = { method: 'PUT', url: `Patient/${patient.resource.id}` };
      transaction.entry.push(patient);

      // Add bundle to the entries
      transaction.entry.push({
        fullUrl: `urn:uuid:${docId}`,
        resource: JSON.parse(JSON.stringify(bundleIPS)),
        request: { method: 'POST', url: 'Bundle' },
      });

      // req.body.type = 'transaction';

      // Create Document Reference and SubmissionSet required for ITI-65 compliance
      const docRefId = uuidv4();
      transaction.entry.push(createDocumentReference(bundleIPS, docRefId, docId, FHIR_EXTERNAL_URL));
      transaction.entry.push(createSubmissionSet(bundleIPS, docRefId, docId));
    }

    console.log('--------');
    console.log(JSON.stringify(transaction));
    console.log('--------');
    // Send the request to the server
    axios.request(
      {
        url: FHIR_URL,
        method: 'POST',
        maxBodyLength: Infinity,
        data: JSON.stringify(transaction),
        headers: {
          'Content-Type': 'application/json',
        },
      },
    ).then((response) => {
      console.log(response.data);
      res.status(response.status);
      res.send(response.data);

      // const bundleIPS = JSON.parse(JSON.stringify(req.body));
      const docId = response.data.entry[response.data.entry.length - 3].response.location.split('/')[1];
      originalBundleIPS.id = docId;
      console.log(`${FHIR_URL}/Bundle/${docId}`);
      axios.request({
        url: `${FHIR_URL}/Bundle/${docId}`,
        method: 'PUT',
        data: originalBundleIPS,
      });

      const docRefId = response.data.entry[response.data.entry.length - 2].response.location.split('/')[1];
      axios.request({
        url: `${FHIR_URL}/DocumentReference/${docRefId}`,
        method: 'GET',
      }).then((docRefRes) => {
        const docRef = docRefRes.data;
        docRef.content[0].attachment.url = `${FHIR_EXTERNAL_URL}/Bundle/${docId}`;
        axios.request({
          url: `${FHIR_URL}/DocumentReference/${docRefId}`,
          method: 'PUT',
          data: docRef,
        });
      });
    })
      .catch((err) => {
        console.log('ERROR');
        console.error(err);
        // res.status(err.response.status);
        // res.end(err.response.data);
      });
  } catch (e) {
    res.status(500);
    res.end('ERROR');
  }
});

router.get('/Bundle/:id/([\$])ddcc', async (req, res) => {
  try {
    console.log('TEST');
    const FHIR_URL = req.app.get('hapiFhir');
    const DDCC_URL = req.app.get('ddccURL');

    const url = `${FHIR_URL}/Bundle/${req.params.id}`;

    let ips = await axios.get(url).catch((err) => {
      console.error(err);
      return { error: true };
    });
    ips = ips.data;
    if (!ips) {
      res.status(400).send({ error: 'IPS is empty or not valid' });
      return;
    }

    const { immunizationId, organizationId } = req.query;

    let patient = ips.entry.find((e) => e.resource && e.resource.resourceType == 'Patient');
    let immunization = immunizationId
      ? ips.entry.find((e) => e.resource && e.resource.resourceType == 'Immunization' && (e.resource.id == immunizationId || e.fullUrl.indexOf(immunizationId) >= 0))
      : ips.entry.find((e) => e.resource && e.resource.resourceType == 'Immunization');
    let organization = organizationId
      ? ips.entry.find((e) => e.resource && e.resource.resourceType == 'Organization' && (e.resource.id == organizationId || e.fullUrl.indexOf(organizationId) >= 0))
      : ips.entry.find((e) => e.resource && e.resource.resourceType == 'Organization');
    let composition = ips.entry.find((e) => e.resource && e.resource.resourceType == 'Composition');

    if (!patient || !immunization || !organization || !composition) {
      res.status(400).send({ error: 'IPS has no patient or immunization or organization or compoosition' });
      return;
    }

    patient = patient.resource;
    immunization = immunization.resource;
    organization = organization.resource;
    composition = composition.resource;
    // console.log(patient, immunization);

    const qr = buildDDCCQR(patient, immunization, organization, composition);
    console.log(JSON.stringify(qr));

    console.log(DDCC_URL);
    const resp = await axios.post(DDCC_URL, qr);
    res.status(resp.status).send(resp.data);
  } catch (e) {
    res.status(500);
    res.end('ERROR');
  }
});

router.get('/Bundle/:id/([\$])dvc', async (req, res) => {
  try {
    const FHIR_URL = req.app.get('hapiFhir');
    const DDCC_URL = req.app.get('ddccURL');

    const url = `${FHIR_URL}/Bundle/${req.params.id}`;

    let ips = await axios.get(url).catch((err) => {
      console.error(err);
      return { error: true };
    });
    ips = ips.data;
    if (!ips) {
      res.status(400).send({ error: 'IPS is empty or not valid' });
      return;
    }

    const { immunizationId, organizationId } = req.query;

    let patient = ips.entry.find((e) => e.resource && e.resource.resourceType == 'Patient');
    let immunization = immunizationId
      ? ips.entry.find((e) => e.resource && e.resource.resourceType == 'Immunization' && (e.resource.id == immunizationId || e.fullUrl.indexOf(immunizationId) >= 0))
      : ips.entry.find((e) => e.resource && e.resource.resourceType == 'Immunization');
    let organization = organizationId
      ? ips.entry.find((e) => e.resource && e.resource.resourceType == 'Organization' && (e.resource.id == organizationId || e.fullUrl.indexOf(organizationId) >= 0))
      : ips.entry.find((e) => e.resource && e.resource.resourceType == 'Organization');
    let composition = ips.entry.find((e) => e.resource && e.resource.resourceType == 'Composition');

    if (!patient || !immunization || !organization || !composition) {
      res.status(400).send({ error: 'IPS has no patient or immunization or organization or compoosition' });
      return;
    }

    patient = patient.resource;
    immunization = immunization.resource;
    organization = organization.resource;
    composition = composition.resource;
    // console.log(patient, immunization);

    const qr = buildDVCQR(patient, immunization, organization, composition);
    const bundle = {
      resourceType: 'Bundle',
      type: 'batch',
      entry: [
        {
          resource: qr,
          request: {
            method: 'POST',
            url: 'QuestionnaireResponse/$generateHealthCertificate',
          },
        },
      ],
    };
    console.log(JSON.stringify(bundle));

    console.log(DDCC_URL);
    const resp = await axios.post(`${DDCC_URL}icvp/`, bundle);
    res.status(resp.status).send(resp.data);
  } catch (e) {
    console.error(e);
    res.status(500);
    res.end('ERROR');
  }
});

router.get('/Bundle/:id/([\$])icvp', async (req, res) => {
  try {
    const FHIR_URL = req.app.get('hapiFhir');
    const DDCC_URL = req.app.get('ddccURL');

    const url = `${FHIR_URL}/Bundle/${req.params.id}`;

    let ips = await axios.get(url).catch((err) => {
      console.error(err);
      return { error: true };
    });
    ips = ips.data;
    if (!ips) {
      res.status(400).send({ error: 'IPS is empty or not valid' });
      return;
    }

    const { immunizationId } = req.query;

    let patient = ips.entry.find((e) => e.resource && e.resource.resourceType == 'Patient');
    let immunization = immunizationId
      ? ips.entry.find((e) => e.resource && e.resource.resourceType == 'Immunization' && (e.resource.id == immunizationId || e.fullUrl.indexOf(immunizationId) >= 0))
      : ips.entry.find((e) => e.resource && e.resource.resourceType == 'Immunization');

    if (!patient || !immunization) {
      res.status(400).send({ error: 'IPS has no patient or immunization' });
      return;
    }

    patient = patient.resource;
    immunization = immunization.resource;

    const qr = buildICVPQR(patient, immunization);
    if (qr == null) {
      res.status(422).send({
        error: 'IPS has missing information to create ICVP',
      });
      return;
    }

    const bundle = {
      resourceType: 'Bundle',
      type: 'batch',
      entry: [
        {
          resource: qr,
          request: {
            method: 'POST',
            url: 'QuestionnaireResponse/$generateHealthCertificate',
          },
        },
      ],
    };
    console.log(JSON.stringify(bundle));
    const resp = await axios.post(`${DDCC_URL}icvp/`, bundle);
    res.status(resp.status).send(resp.data);
  } catch (e) {
    console.error(e);
    res.status(500);
    res.end('ERROR');
  }
});

router.get('/Bundle/:id/([$])icvp2', async (req, res) => {
  try {
    const FHIR_URL = req.app.get('hapiFhir');
    const privateKey = req.app.get('privateKey');
    const issuerCountryCode = req.app.get('issuerCountryCode');

    const url = `${FHIR_URL}/Bundle/${req.params.id}`;

    let ips = await axios.get(url).catch((err) => {
      console.error(err);
      return { error: true };
    });
    ips = ips.data;
    if (!ips) {
      res.status(400).send({ error: 'IPS is empty or not valid' });
      return;
    }

    const { immunizationId } = req.query;

    let patient = ips.entry.find((e) => e.resource && e.resource.resourceType === 'Patient');
    let immunization = immunizationId
      ? ips.entry.find((e) => e.resource && e.resource.resourceType === 'Immunization' && (e.resource.id === immunizationId || e.fullUrl.indexOf(immunizationId) >= 0))
      : ips.entry.find((e) => e.resource && e.resource.resourceType === 'Immunization');

    if (!patient || !immunization) {
      res.status(400).send({ error: 'IPS has no patient or immunization' });
      return;
    }

    patient = patient.resource;
    immunization = immunization.resource;

    try {
      const payload = buildICVPPayload(patient, immunization);
      const hc1 = signHcert(payload, privateKey, issuerCountryCode);
      const response = createHCERTBundleResponse(hc1);
      res.json(response);
    } catch (err) {
      console.error(err);
      res.status(422).send({
        error: err.message,
      });
    }
  } catch (e) {
    console.error(e);
    res.status(500);
    res.end('ERROR');
  }
});

router.get('/Bundle/:id/([$])meow', async (req, res) => {
  try {
    const FHIR_URL = req.app.get('hapiFhir');
    const privateKey = req.app.get('privateKey');
    const issuerCountryCode = req.app.get('issuerCountryCode');

    const url = `${FHIR_URL}/Bundle/${req.params.id}`;

    let bundle = await axios.get(url).catch((err) => {
      console.error(err);
      return { error: true };
    });
    bundle = bundle.data;
    if (!bundle) {
      res.status(400).send({ error: 'Bundle is empty or not valid' });
      return;
    }

    const { medicationStatementId } = req.query;

    const patient = bundle.entry.find((e) => e.resource && e.resource.resourceType === 'Patient')?.resource;
    const medicationStatement = medicationStatementId
      ? bundle.entry.find((e) => e.resource && e.resource.resourceType === 'MedicationStatement' && (e.resource.id === medicationStatementId || e.fullUrl.indexOf(medicationStatementId) >= 0))?.resource
      : bundle.entry.find((e) => e.resource && e.resource.resourceType === 'MedicationStatement')?.resource;

    if (!patient || !medicationStatement) {
      res.status(400).send({ error: 'Bundle has no patient or medication statement' });
      return;
    }

    try {
      const payload = buildMeOWPayload(patient, medicationStatement);
      const hc1 = signHcert(payload, privateKey, issuerCountryCode, -7);
      const response = createHCERTBundleResponse(
        hc1,
        'meow',
        'http://worldhealthorganization.github.io/smart-ph4h/CodeSystem/MeOw-QR-Type-CodeSystem',
      );
      res.json(response);
    } catch (err) {
      console.error(err);
      res.status(422).send({
        error: err.message,
      });
    }
  } catch (e) {
    console.error(e);
    res.status(500);
    res.end('ERROR');
  }
});

/* All requests will be passed to the FHIR server. */
router.all('/*', async (req, res) => {
  try {
    console.log('forward');
    const FHIR_URL = req.app.get('hapiFhir');
    axios.request(
      {
        url: `${FHIR_URL}${req.path}`,
        method: req.method,
        data: req.body,
        params: req.query,
      },
    ).then((response) => {
      res.status(response.status).send(response.data);
    })
      .catch((err) => {
        res.status(err.response.status).send(err.response.data);
      });
  } catch (e) {
    res.status(500);
    res.end('ERROR');
  }
});

module.exports = router;
