const { v4: uuidv4 } = require("uuid");

const putPDBEntry = (resource) => {
    return {
      resource,
      request: {
        method: "PUT",
        url: resource.resourceType + "/" + resource.id
      }
    }
}
  
const postPDBEntry = (resourceType, tempId) => {
    return {
        fullUrl: "urn:uuid:" + tempId,
        resource: {
        resourceType: resourceType
        },
        request: {
        method: "POST",
        url: resourceType
        }
    };
}

const createDocumentReference = (bundleIPS, docRefId, docId, FHIR_URL) => {
    let entry = postPDBEntry("DocumentReference", docRefId)
    entry.resource.meta = {
        profile: ["https://profiles.ihe.net/ITI/MHD/StructureDefinition/IHE.MHD.Minimal.DocumentReference"]
    }
    entry.resource.status = "current"
    let identifier = {
        "system": "urn:ietf:rfc:3986",
        "value": "urn:uuid:" + docId
    }
    entry.resource.identifier = [identifier]
    entry.resource.masterIdentifier = identifier
    entry.resource.subject = bundleIPS.entry[0].resource.subject
    entry.resource.date = bundleIPS.timestamp
    entry.resource.content = [
        {
            attachment: {
                contentType: "application/fhir+json",
                url: FHIR_URL + "/Bundle/urn:uuid:" + docId
            }
        }
    ]
    return entry
}

const createSubmissionSet = (bundleIPS, docRefId, docId) => {
    let submissionSetId = uuidv4();
    let entry = postPDBEntry("List", submissionSetId);
    entry.resource.meta = {
      "profile": [
        "https://profiles.ihe.net/ITI/MHD/StructureDefinition/IHE.MHD.Minimal.SubmissionSet"
      ],
      "security": [
        {
          "system": "http://terminology.hl7.org/CodeSystem/v3-ActReason",
          "code": "HTEST"
        }
      ]
    };

    entry.resource.extension = [
      {
        url: "https://profiles.ihe.net/ITI/MHD/StructureDefinition/ihe-sourceId",
        valueIdentifier: {
          value: "LACPass"
        }
      }
    ]
    entry.resource.identifier = [
      {
        use: "usual",
        system: "urn:ietf:rfc:3986",
        value: "urn:oid:" + submissionSetId
      }
    ]
    entry.resource.subject = bundleIPS.entry[0].resource.subject
    entry.resource.status = "current"
    entry.resource.mode = "working"
    entry.resource.code = {
      coding: [
        {
          system: "https://profiles.ihe.net/ITI/MHD/CodeSystem/MHDlistTypes",
          code: "submissionset"
        }
      ]
    }
    entry.resource.date = bundleIPS.timestamp
    entry.resource.entry = [
      {
        item: { reference: "urn:uuid:" + docRefId }
      },
    ]
    return entry
}

module.exports = {
    createDocumentReference,
    createSubmissionSet
};