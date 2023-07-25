const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const { v4: uuidv4 } = require("uuid");
const canonicalize = require('../utils/canonicalize');
const { createDocumentReference, createSubmissionSet } = require('../utils/transactions');
const { buildDDCCQR } = require('../utils/ddcc');

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
        value: 'example-practitioner',
        system: 'example.system.com',
      },
    },
    data: sign.toString('base64'),
  };
  return Object.assign(body, { signature });
}

/* Provide Document ITI-65. */
router.all('/Bundle', async (req, res) => {
  console.log("ITI-65");
  const FHIR_URL = req.app.get('hapiFhir');
  const FHIR_EXTERNAL_URL = req.app.get('externalFhir');

  let url = `${FHIR_URL}/Bundle`;
  req.body = addSignature(req.body, req.app.get('privateKey'));
  if (req.body?.type === 'document' && req.method === 'POST') {
    // Create a copy of the original Bundle IPS
    const bundleIPS = JSON.parse(JSON.stringify(req.body));

    let docId = bundleIPS.id;
    if(docId == null){
      docId = uuidv4();
      bundleIPS.id = docId;
    }

    // Convert the document to a transaction to force the creation of resources
    // This only will happen if a new Bundle is created, it does not work for PUT method
    // Add the document as an entry, so it is also created
    req.body.entry.forEach((e, index) => {
      let url = e.resource.id ? `${e.resource.resourceType}/${e.resource.id}` : undefined;
      // console.log(url);
      req.body.entry[index].request = {
        method: req.method,
        url: url
      };
      if(url){
        req.body.entry[index].fullUrl = url;
        bundleIPS.entry[index].fullUrl = url;
      }
    });

    // Add bundle to the entries
    req.body.entry.push({
      fullUrl:  "Bundle/" + docId,
      resource: JSON.parse(JSON.stringify(bundleIPS)),
      request: { method: "PUT", url: 'Bundle/' + docId },
    });

    if (req.method === 'POST') {
      url = FHIR_URL;
    } else if (req.method === 'PUT') {
      url = `${url}/${req.body.id}`;
    }
    req.body.type = 'transaction';

    // Create Document Reference and SubmissionSet required for ITI-65 compliance
    const docRefId = uuidv4();
    req.body.entry.push(createDocumentReference(bundleIPS, docRefId, docId, FHIR_EXTERNAL_URL));
    req.body.entry.push(createSubmissionSet(bundleIPS, docRefId, docId));
  }


  //console.log(req.body);
  // Send the request to the server
  axios.request(
    {
      url,
      method: req.method,
      data: req.body,
      params: req.params,
    },
  ).then((response) => {
    // console.log(response.data);
    res.status(response.status);
    res.end(JSON.stringify(response.data));
  })
  .catch((err) => {
    console.log("ERROR");
    console.error(err.response.data);
    res.status(err.response.status);
    res.end(JSON.stringify(err.response.data));
  });
});

router.get("/Bundle/:id/([\$])ddcc", async (req, res) => {
  console.log("TEST");
  const FHIR_URL = req.app.get('hapiFhir');
  const DDCC_URL = req.app.get('ddccURL');

  const url = `${FHIR_URL}/Bundle/${req.params.id}`;
  let ips = await axios.get(url);
  ips = ips.data;
  if(!ips){
    res.status(400).send({"error": "IPS is empty or not valid"});
    return;
  }

  let patient = ips.entry.find(e => e.resource && e.resource.resourceType == "Patient");
  let immunization = ips.entry.find(e => e.resource && e.resource.resourceType == "Immunization");
  let organization = ips.entry.find(e => e.resource && e.resource.resourceType == "Organization");

  if(!patient || !immunization || !organization){
    res.status(400).send({"error": "IPS has no patient or immunization or organization"});
    return;
  }

  patient = patient.resource;
  immunization = immunization.resource;
  organization = organization.resource;
  // console.log(patient, immunization);

  let qr = buildDDCCQR(patient, immunization, organization);
  console.log(JSON.stringify(qr));

  console.log(DDCC_URL);
  let resp = await axios.post(DDCC_URL, qr);
  res.status(resp.status).send(resp.data);

});

/* All requests will be passed to the FHIR server. */
router.all('/*', async (req, res) => {
  console.log("forward");
  const FHIR_URL = req.app.get('hapiFhir');
  axios.request(
      {
        url: FHIR_URL,
        method: req.method,
        data: req.body,
        params: req.params,
      },
  ).then((response) => {
    res.status(response.status).send(response.data);
  })
      .catch((err) => {
        res.status(err.response.status).send(err.response.data);
      });
});

module.exports = router;
