if [ ! -f ./key.pem ]; then
  echo "Private key file not found"
else
  openssl req \
      -new \
      -newkey rsa:4096 \
      -days 365 \
      -nodes \
      -x509 \
      -subj "/C=CL/ST=Metropolitana/L=Santiago/O=Create/CN=lacpass.create.cl" \
      -keyout key.pem \
      -out cert.pem
fi