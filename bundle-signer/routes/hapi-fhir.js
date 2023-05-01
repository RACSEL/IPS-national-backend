const express = require('express');
const axios = require('axios');
const crypto = require('crypto');
const canonicalize = require('../utils/canonicalize');

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

/* Bundle. */
router.all('/Bundle', async (req, res) => {
  const FHIR_URL = req.app.get('hapiFhir');
  let url = `${FHIR_URL}/Bundle`;
  req.body = addSignature(req.body, req.app.get('privateKey'));
  if (req.body?.type === 'document' && req.method === 'POST') {
    // Convert the document to a transaction to force the creation of resources
    // This only will happen if a new Bundle is created, it does not work for PUT method
    // Add the document as an entry, so it is also created
    req.body.entry.push({
      resource: JSON.parse(JSON.stringify(req.body)),
      request: { method: req.method, url: 'Bundle' },
    });
    req.body.entry.forEach((_, index) => {
      req.body.entry[index].request.method = req.method;
    });

    if (req.method === 'POST') {
      url = FHIR_URL;
    } else if (req.method === 'PUT') {
      url = `${url}/${req.body.id}`;
    }
    req.body.type = 'transaction';
  }
  axios.request(
    {
      url,
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

/* All requests will be passed to the FHIR server. */
router.all('/*', async (req, res) => {
  const FHIR_URL = req.app.get('hapiFhir');
  axios.request(
      {
        url: 'http://lacpass.create.cl:8080',
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
