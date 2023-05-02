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
        profile: ["http://hl7.org/fhir/uv/ips/StructureDefinition/Bundle-uv-ips"]
    }
    entry.resource.status = "current"
    let identifier = {
        "system": "https://profiles.ihe.net/ITI/MHD/StructureDefinition/IHE.MHD.Comprehensive.DocumentReference",
        "value": docId
    }
    entry.resource.identifier = [identifier]
    entry.resource.masterIdentifier = identifier
    entry.resource.subject = bundleIPS.entry[0].resource.subject
    entry.resource.date = bundleIPS.timestamp
    entry.resource.content = [
        {
            attachment: {
                contentType: "application/fhir+json",
                url: FHIR_URL + "/Bundle/" + docId
            }
        }
    ]
    return entry
}

const createSubmissionSet = (bundleIPS, docRefId, docId) => {
    let submissionSetId = uuidv4();
    let entry = postPDBEntry("List", submissionSetId);
    entry.resource.extension = [
      {
        url: "http://profiles.ihe.net/ITI/MHD/StructureDefinition/ihe-sourceId",
        valueIdentifier: {
          system: "origin",
          value: "LACPass"
        }
      }
    ]
    entry.resource.identifier = [
      {
        use: "usual",
        system: "https://profiles.ihe.net/ITI/MHD/StructureDefinition/IHE.MHD.Minimal.SubmissionSet",
        value: submissionSetId
      },
      {
        use: "official",
        system: "https://profiles.ihe.net/ITI/MHD/StructureDefinition/IHE.MHD.Minimal.SubmissionSet",
        value: submissionSetId
      }
    ]
    entry.resource.subject = bundleIPS.entry[0].resource.subject
    entry.resource.status = "current"
    entry.resource.mode = "working"
    entry.resource.code = {
      coding: [
        {
          system: "http://profiles.ihe.net/ITI/MHD/CodeSystem/MHDlistTypes",
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