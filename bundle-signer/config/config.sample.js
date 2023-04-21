require('dotenv').config();

module.exports = {
  development: {
    hapiFhir: process.env.DEV_HAPI_FHIR,
    privateKeyFile: process.env.DEV_PRIVATE_KEY_FILE,
  },
  test: {
    hapiFhir: process.env.TEST_HAPI_FHIR,
    privateKeyFile: process.env.TEST_PRIVATE_KEY_FILE,
  },
  production: {
    hapiFhir: process.env.PROD_HAPI_FHIR,
    privateKeyFile: process.env.PROD_PRIVATE_KEY_FILE,
  },
};
