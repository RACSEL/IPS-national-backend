if [ ! -f ./key.pem ]; then
  openssl req \
      -new \
      -newkey rsa:4096 \
      -days 365 \
      -nodes \
      -x509 \
      -subj "/C=CL/ST=Metropolitana/L=Santiago/O=Create/CN=lacpass.create.cl" \
      -keyout key.pem \
      -out cert.pem
else
  echo "Private key already exists"
fi
