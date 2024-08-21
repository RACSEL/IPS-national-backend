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
- HAPI FHIR 6.0.1+


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

* Check whether the Snowstorm and Snowstorm browser server is running in `http://localhost:8082` Also check if the terms were correctly uploaded.

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

## Terminology Server

An instance of `elasticsearch`, `snowstorm` and `snowstorm-browser` are provided within the docker compose services. Also an initialization script `init_snowstorm.sh` is executed the first time those services are deployed. By default this scripts loads the terms for spanish corpus into the server.

The Snowstorm instance is pre-loaded with the latest version of the Latin-America Spanish Edition.

Check access to the browser by navigating to `http://localhost:8082`

### Converting local terminologies to FHIR (Connectathon 2024)

An [XLSX sepreadsheet](./fhir-terminology/Subsets_Conectathon_Template.xlsx) is provided as a template to facilitate the creation of the necessary terminology artifacts for the connectathon. The spreadsheet provides a mechanism to load local terminologies and mas to SNOMED CT, ICD-10 or ICD-11, as required.

For this exercise, connectathon participants should edit the spreadheet, entering values for any local codes used on their system that matches the refence list of the RACSEL connectathon. This spreadsheet will be converted in FHIR resources using a [custom conversion script](./fhir-terminology/racsel-convert-xlsx-to-fhir.py) provided in this project. All the necessary files are available in the [Terminoloy folder](./fhir-terminology/). All the edits should be performed on the [template spreassheet](./fhir-terminology/Subsets_Conectathon_Template.xlsx), the test data files are only provided for validation purposes.

To run transformation script you need to have [Python installed in your computer](https://www.python.org/downloads/). To execute the conversion use this command (the Python executable can be named python3, python or py depending on your setup):

    python3 racsel-convert-xlsx-to-fhir.py Subsets_Conectathon_Test_Data.xlsx

There is an option parameter to split the local code system by domain (Diagnosis, medication, etc), this is required if the local codes can overlap between different domains, i.e. if a diagonosisc an have the same local code as a medication. Yo use this split conversion you can run:

    python3 racsel-convert-xlsx-to-fhir.py Subsets_Conectathon_Test_Data.xlsx -splitcs

Users should complete all the necessary fields in the template, and then run the Python script. The result of the script run will be a FHIR Package that incldes all necessary resources:
- CodeSystems
    - RACSEL: a code system with all codes in RACSEL common terms
    - ICD-10 fragment: only the codes used in the connectathon
    - ICD-11 fragment: only the codes used in the connectathon
    - Local Code System: the local codes provided by the user
- ValueSet
    - SNOMED Value Sets: one per section plus a general value set
    - ICD-10: all codes
    - ICD-11: all codes
    - RACSEL: one per section plus a general value set
    - Local Codes: one per section plus a general value set
- ConceptMaps
    - Local to SNOMED
    - Local to FHIR
    - Local to ICD-10
    - Local to ICD-11
    - ICD-11 to SNOMED
    - ICD-10 to SNOMED (Custom reverse map)
    - SNOMED to ICD-10 (Official map, already included in the SNOMED release)

### Loading FHIR Resources in the terminology server

The previous step generates a FHIR package, the current version of Snowstorm supports loading FHIR resources in the FHIR Package using the "load-package" endpoint.

Example of uploading the package from the command line:

    curl --form file=@racsel_fhir_package.tgz --form resourceUrls="*" http://localhost:8080/fhir-admin/load-package