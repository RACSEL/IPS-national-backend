require('dotenv').config();

module.exports = {
  development: {
    hapiFhir: process.env.DEV_HAPI_FHIR,
    externalFhir: process.env.EXTERNAL_HAPI_FHIR,
    ddccURL: process.env.DDCC_URL,
    privateKeyFile: process.env.DEV_PRIVATE_KEY_FILE,
    issuerCountryCode: process.env.ISSUER_COUNTRY_CODE || 'XX',
    hcertKid: process.env.DSC_KID || 'default_kid',
  },
  test: {
    hapiFhir: process.env.TEST_HAPI_FHIR,
    externalFhir: process.env.EXTERNAL_HAPI_FHIR,
    ddccURL: process.env.DDCC_URL,
    privateKeyFile: process.env.TEST_PRIVATE_KEY_FILE,
    issuerCountryCode: process.env.ISSUER_COUNTRY_CODE || 'XX',
    hcertKid: process.env.DSC_KID || 'default_kid',
  },
  production: {
    hapiFhir: process.env.PROD_HAPI_FHIR,
    externalFhir: process.env.EXTERNAL_HAPI_FHIR,
    ddccURL: process.env.DDCC_URL,
    privateKeyFile: process.env.PROD_PRIVATE_KEY_FILE,
    issuerCountryCode: process.env.ISSUER_COUNTRY_CODE || 'XX',
    hcertKid: process.env.DSC_KID || 'default_kid',
  },
};
