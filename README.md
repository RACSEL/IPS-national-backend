# IPS National Backend

Docker compose project containing all services required for the implementation of IPS (International Patient Summary). 
The services created by the compose are:
 - Hapi FHIR (Spring implementation of FHIR)
 - Hapi FHIR Database (Psql database for the FHIR server)
 - Elastic Search (Used by Snowstorm) 
 - Snowstorm (SNOMED CT Terminology server)
 - Snowstorm Browser (Web UI for Snowstorm)
 - LACPass IPS Viewer
 - DDCC Mediator and service
 - Bundle signer service
 - IPS Mediator for MHD Transactions

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

You need to provide a private key in the directory `cert-data` in PEM format. See the cert-data README for more information.  


### Testing

* Check whether the HAPI FHIR server is running in `http://localhost:8080` 

* Check whether the Snowstorm and Snowstorm browser server is running in `http://localhost:8082` Also check if the IPS terms were correctly uploaded.

* Test creating an IPS resource directly using the bundle endpoint. For example use this command

      curl -i -X POST http://localhost:8080/fhir/Bundle -H "Content-Type: application/json" -d @examples/ips-sample-1.json

* Test creating an DDCC resource using the provided service. For example use this command

      curl -i -X POST http://localhost:4321/ddcc -H "Content-Type: application/json" -d @examples/ddcc-sample-1.json  

* Check out the LACPass IPS Viewer running in `http://localhost:8085`. You can input IPS json directly or querying the HAPI FHIR server. 

In all cases, replace `localhost` with your server IP if needed.

### IPS Transactions

This repository includes the IPS mediator service which is a FHIR interceptor or API Gateway that transforms the incoming request to implement MHD Transactions. 

The following MHD transactions are supported

#### ITI-65 - Provide Document

Reference: https://profiles.ihe.net/ITI/MHD/ITI-65.html

This endpoint recieves an IPS Bundle and transform it to a FHIR transaction adding the Patient Folder (List) and the Document Reference as explained in the implementation guide.

Example command:

    curl -i -X POST http://localhost:3000/fhir/Bundle -H "Content-Type: application/json" -d @examples/ips-sample-1.json


#### ITI-66 - Find Document Lists

Reference: https://profiles.ihe.net/ITI/MHD/ITI-66.html

This endpoint recieves a patient identifier and gives the list of document and their references.

Example command:

    curl -i -X GET http://localhost:8080/fhir/List/?patient.identifier=CY/Passport-HG-1112&_format=json&status=current

Note that the parameter `patient.identifier` is defined with the value of the identifier of the patient to be queried.


#### ITI-67 - Find Document References

Reference: https://profiles.ihe.net/ITI/MHD/ITI-67.html

This endpoint recieves a patient identifier and gives the list of document references for this patient.

Example command:

    curl -i -X GET http://localhost:8080/fhir/DocumentReference/?patient.identifier=CY/Passport-HG-1112&_format=json&status=current

Note that the parameter `patient.identifier` is defined with the value of the identifier of the patient to be queried.


#### ITI-68 - Provide Document

Reference: https://profiles.ihe.net/ITI/MHD/ITI-68.html

This endpoint returns the IPS for a patient. The URL is retrtieved from the result of the ITI-67 request. Specifically the url will be in the `content > attachment > url` attribute of each entry.

Example command:

    curl -i -X GET http://lacpass.create.cl:8080/fhir/Bundle/IPS-examples-Bundle-01?_format=json
