FROM node:18.15.0-alpine3.17
RUN apk upgrade --update-cache --available && \
    apk add --no-cache openssl && \
    rm -rf /var/cache/apk/*

# Create app directory
WORKDIR /usr/src/app

# Install app dependencies
COPY package*.json ./

RUN npm install

# Bundle app source
COPY . .

EXPOSE 3000
CMD [ "sh", "-c", "cp config/config.sample.js config/config.js && cd static && sh create_pem_files.sh && cd .. && npm start" ]