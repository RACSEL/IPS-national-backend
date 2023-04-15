const express = require('express');
// eslint-disable-next-line import/no-extraneous-dependencies
const { Proxy } = require('axios-express-proxy');
const config = require('../config/config');

const env = process.env.NODE_ENV || 'development';

const router = express.Router();
const PROXY_URL = config[env].hapiFhir.replace('/fhir', '');
/* GET home page. */
router.get('/', (req, res) => Proxy(PROXY_URL, req, res));

module.exports = router;
