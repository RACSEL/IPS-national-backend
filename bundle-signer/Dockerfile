FROM node:18.15.0-alpine3.17
RUN apk upgrade --update-cache --available && \
    apk add openssl && \
    rm -rf /var/cache/apk/* \

# Create app directory
WORKDIR /usr/src/app

# Install app dependencies
# A wildcard is used to ensure both package.json AND package-lock.json are copied
# where available (npm@5+)
COPY package*.json ./

RUN npm install
# If you are building your code for production
# RUN npm ci --only=production

# Bundle app source
COPY . .
CMD [ "cp", "config/config.sample.js", "config/config.js" ]
CMD [ "sh", "static/create_pem_files.sh"]

EXPOSE 3000
CMD [ "npm", "start" ]