const express = require('express');
const crypto = require('crypto');
const axios = require('axios');
const canonicalize = require('../utils/canonicalize');

const router = express.Router();


router.get('/:bundleId', async (req, res) => {
    const FHIR_URL = req.app.get('hapiFhir');
    const url = `${FHIR_URL}/Bundle/${req.params.bundleId}`;
    const publicKey = req.app.get('publicKey');
    await axios.get(url).then(response => {
        const bundle = response.data;
        const signature = Object.assign({}, bundle.signature);
        // Delete all keys that were not present when it was signed
        delete bundle.id;
        delete bundle.signature;
        delete bundle.meta;
        bundle.entry.forEach((elem) => {
            delete elem.resource.meta;
        })
        // TODO need to check who created/updated the bundle to validate with the correct public key
        return res.status(200).send({
            verified: crypto.verify(
                "SHA256",
                canonicalize(bundle),
                publicKey,
                Buffer.from(signature.data, 'base64')
            )
        });
    }).catch((err) => {
        res.status(err.response.status).send(err.response.data);
    });

});

module.exports = router;