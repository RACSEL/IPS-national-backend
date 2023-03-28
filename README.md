# IPS National Backend

Docker compose project containing all services required for the implementation of IPS (International Patient Summary). 
The services created by the compose are:
 - Hapi FHIR (Spring implementation of FHIR)
 - Hapi FHIR Database (Psql database for the FHIR server)
 - Elastic Search (Used by Snowstorm) 
 - Snowstorm (SNOMED CT Terminology server)
 - Snowstorm Browser (Web UI for Snowstorm)
 - DDCC Mediator and service

> **Note**:
> The services require at least 8GB of ram to run.

## Requirements

- Docker version >20.10.8 
- Docker compose version >1.29.2


To run the services use: 

```bash
$ docker-compose up -d
```

### Configuration

If you need to change any of the default value, you can edit `docker-compose.yml`. In the case of the FHIR server, 
to see the available environment variables you can pass see `hapi-config/application.yaml`.

### Testing

* Check whether the HAPI FHIR server is running in `http://localhost:8080` 

* Check whether the Snowstorm and Snowstorm browser server is running in `http://localhost:8082` Also check if the IPS terms were correctly uploaded.

* Test creating an IPS resource directly using the bundle endpoint. For example use this command

      curl -i -X POST http://localhost:8080/fhir/Bundle -H "Content-Type: application/json" -d examples/ips-sample-1.json

* Test creating an DDCC resource using the provided service. For example use this command

      curl -i -X POST http://localhost:4321/ddcc -H "Content-Type: application/json" -d examples/ddcc-sample-1.json  

In all cases, replace `localhost` with your server IP if needed.