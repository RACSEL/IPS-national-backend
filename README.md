# IPS National Backend

Docker compose project containing all services required for the implementation of IPS (International Patient Summary). 
The services created by the compose are:
 - Hapi FHIR (Spring implementation of FHIR)
 - Hapi FHIR Database (Psql database for the FHIR server)
 - Elastic Search (Used by Snowstorm) 
 - Snowstorm (SNOMED CT Terminology server)
 - Snowstorm Browser (Web UI for Snowstorm)
 - LACPass IPS Viewer
 - DDCC Mediator IPS and service
 - Bundle signer service
 - IPS Mediator for MHD Transactions
 - IPS to DDCC transformation operation

> **Note**:
> The services require at least 12GB of ram to run.

## Requirements

- Docker version >20.10.8 
- Docker compose version >1.29.2


To run the services use: 

```bash
$ docker-compose up -d
```

### Configuration

If you need to change any of the default value, you can edit `docker-compose.yml`. In the case of the FHIR server, to see the available environment variables you can pass see `hapi-config/application.yaml`.

In particular you should change the variable `EXTERNAL_HAPI_FHIR` to the actual public URL to the FHIR server.

You need to provide a private key(**DSC01privkey.key**) and cert(**DSCcert.pem**) in the directory `cert-data`.  

You also need to add the 3 digit country code(alpha-3-code) in docker-compose.yml in the **ddcc** service, e.g. **ARG** for Argentina

```
COUNTRY_CODE: 'ARG'
```

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


#### ITI-68 - Retrieve Document

Reference: https://profiles.ihe.net/ITI/MHD/ITI-68.html

This endpoint returns the IPS for a patient. The URL is retrtieved from the result of the ITI-67 request. Specifically the url will be in the `content > attachment > url` attribute of each entry.

Example command:

    curl -i -X GET http://lacpass.create.cl:8080/fhir/Bundle/IPS-examples-Bundle-01?_format=json


### Transformations

The IPS mediator includes a FHIR operation called `$ddcc` which transforms IPS Bundles to DDCC documents. It is mandatory for this operation to work that the stored IPS have at least one `Immunization` resource.

This is an example to use the transformation oepration:

    curl -i --request GET 'http://localhost:3000/fhir/Bundle/fb06a834-6b55-4ac3-a856-82489eb4d69d/$ddcc'

Where `fb06a834-6b55-4ac3-a856-82489eb4d69d` is the id of the IPS Bundle. This endpoint returns the DDCC Bundle associated to the requested IPS.

This transformation retrieves a previously stored IPS and checks whether the `Immunization` resource is present. The process extracts the information from the IPS to build the QuestionnaryResponse with the DDCC structure. This QuestionnarieResponse is sent to the DDCC module to generate the document.

Optionally, if the IPS has more than one `Immunization` resource, you can pass the query argument `immunizationId` to specify the id of the `Immunization` resource tto transform. For example:

    curl -i --request GET 'http://localhost:3000/fhir/Bundle/fb06a834-6b55-4ac3-a856-82489eb4d69d/$ddcc?immunizationId=6fef12e7-64ad-4792-b2ad-5d6b699588fc'

### LACCHAIN SETUP, ONBOARD HELPER ###

In the folder `lacchain-setup-helper` you will find a shell script called `client-helper.sh` which will help you setup the lacpass-lacchain component before using it. You just need to run the script once. To find a fully detailed instructions please check the following documentation:

* [Setup English Documentation](https://github.com/lacchain/LACPass-LACChain-Component/blob/main/README.md)
* [Setup Spanish Documentation](https://github.com/lacchain/LACPass-LACChain-Component/blob/main/LEEME.md)

### LACCHAIN SENDING HEALTH CERTIFICATES TO PATIENT WALLETS ###

Once you have completed the previous section **LACCHAIN SETUP, ONBOARD HELPER** you will be ready to Send Health Certificates to your Patients Wallets; for that please take a look at the following instructions:

* [Send health certificates - English Documentation](https://github.com/lacchain/LACPass-LACChain-Component/blob/main/README.md#sending-health-certificates-wrapped-as-verifiable-credentials)
* [Send health certificates - Spanish Documentation](https://github.com/lacchain/LACPass-LACChain-Component/blob/main/LEEME.md#enviando-certificados-de-salud-contenidos-en-credenciales-verificables)
