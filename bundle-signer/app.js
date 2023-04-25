require('dotenv').config();
const express = require('express');
const cookieParser = require('cookie-parser');
const logger = require('morgan');
const cors = require('cors');
const config = require('./config/config');
const signature = require('./utils/signature');

const env = process.env.NODE_ENV || 'development';

const verifyRouter = require('./routes/verify');
const hapiFhirRouter = require('./routes/hapi-fhir');
const indexRouter = require('./routes/index');

const app = express();

app.use(logger('dev'));
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());

// Endpoints
app.use('/verify', verifyRouter);
app.use('/fhir', hapiFhirRouter);
app.use('/*', indexRouter);

// Set config variables
app.set('hapiFhir', config[env]?.hapiFhir);
app.set('privateKey', signature.privateKey);
app.set('publicKey', signature.publicKey);

module.exports = app;
