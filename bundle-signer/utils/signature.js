const fs = require('fs');
const crypto = require('crypto');
const process = require('process');

const env = process.env.NODE_ENV || 'development';
const config = require('../config/config')[env]; // eslint-disable-line

let privateKey;
let publicKey;
if (fs.existsSync(config.privateKeyFile)) {
  const file = fs.readFileSync(config.privateKeyFile) || null;
  publicKey = crypto.createPublicKey({ key: file, format: 'pem' });
  privateKey = crypto.createPrivateKey({ key: file, format: 'pem' });
} else {
  const keyPair = crypto.generateKeyPairSync('ec', { namedCurve: 'P-256' });
  privateKey = keyPair.privateKey;
  publicKey = keyPair.publicKey;
}

module.exports = {
  privateKey: privateKey.export({ format: 'pem', type: 'pkcs8' }),
  publicKey: publicKey.export({ format: 'pem', type: 'spki' }),
  jwkPrivateKey: privateKey.export({ format: 'jwk', type: 'spki' }),
  jwkPublicKey: publicKey.export({ format: 'jwk', type: 'spki' }),
};
