# IPS Proxy 


[![status-badge](https://rpi.belisario.dev/api/badges/belisariops/ips-proxy/status.svg)](https://rpi.belisario.dev/belisariops/ips-proxy)

## Requirements

```
Node ~v18.14.0
Npm ~v9.3.1
```

## Configutation

First create a `config.json` file. We can copy the existing `./config/config.sample.json` file using:

```bash
$ cp ./config/config.sample.json ./config/config.json
```

You can check the available environment variables that are used in the [configuration file](./config/config.sample.js).
Once the configuration file is correctly set, we can install the project dependencies using:

```bash
$ npm install
```

### Run

To run this project there are two options:

```bash
$ npm run dev      # Runs the API with hot reload and also runs table migrations
$ npm run start    # Runs only the API
```