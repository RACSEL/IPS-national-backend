const { v4: uuidv4 } = require("uuid");

function createQRICVP() {
    let id = uuidv4();
    let today = (new Date()).toISOString().substring(0, 10);
    return {
        "resourceType": "QuestionnaireResponse",
        "id": id,
        "text": {
            "status": "generated",
            "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\"></div>"
        },
        "questionnaire": "http://smart.who.int/icvp/Questionnaire/ICVP",
        "status": "completed",
        "item": [
            {
                "linkId": "name",
                "answer": [
                    {
                        "valueString": "" // Sergio Peñafiel
                    }
                ]
            },
            {
                "linkId": "dob",
                "answer": [
                    {
                        "valueDate": ""  // YYYY-MM-DD
                    }
                ]
            },
            {
                "linkId": "sex",
                "answer": [
                    {
                        "valueCoding": {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0001",
                            "code": ""   // male | female
                        }
                    }
                ]
            },
            {
                "linkId": "nid",
                "answer": [
                    {
                        "valueString": ""   // eg 1892265-2
                    }
                ]
            },
            {
                "linkId": "nationality",
                "answer": [
                    {
                        "valueCoding": {
                            "system": "urn:iso:std:iso:3166",
                            "code": ""   // 3-letter ISO eg CHL
                        }
                    }
                ]
            },
            {
                "linkId": "ndt",
                "answer": [
                    {
                        "valueCoding": {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "NI"    // NI | PPN
                        }
                    }
                ]
            },
            {
                "linkId": "guardian",
                "item": [
                    {
                        "linkId": "guardianName",
                        "answer": [
                            {
                                "valueString": ""    // eg Antonio Rojas
                            }
                        ]
                    },
                    {
                        "linkId": "guardianRelationship",
                        "answer": [
                            {
                                "valueCoding": {
                                    "system": "http://smart.who.int/trust-phw/CodeSystem/DVCRelationshipStatus",
                                    "code": "Guardian"  // Parent | Guardian
                                }
                            }
                        ]
                    }
                ]
            },
            {
                "linkId": "vaccineDetails",
                "item": [
                    {
                        "linkId": "productID",
                        "answer": [
                            {
                                "valueCoding": {
                                    "system": "http://smart.who.int/pcmt-vaxprequal/CodeSystem/PreQualProductIDs",
                                    "code": ""  // PreQual codes
                                }
                            }
                        ]
                    },
                    {
                        "linkId": "date",
                        "answer": [
                            {
                                "valueDate": ""   // YYYY-MM-DD
                            }
                        ]
                    },
                    {
                        "linkId": "clinicianName",
                        "answer": [
                            {
                                "valueString": ""  // eg Juan Castro
                            }
                        ]
                    },
                    {
                        "linkId": "batchNo.text",
                        "answer": [
                            {
                                "valueString": ""  // eg A1234
                            }
                        ]
                    },
                    {
                        "linkId": "issuer",
                        "answer": [
                            {
                                "valueString": ""  // eg MIN Salud
                            }
                        ]
                    },
                    {
                        "linkId": "validityPeriod",
                        "item": [
                            {
                                "linkId": "startDate",
                                "answer": [
                                    {
                                        "valueDate": ""   // YYYY-MM-DD
                                    }
                                ]
                            },
                            {
                                "linkId": "endDate",
                                "answer": [
                                    {
                                        "valueDate": ""   // YYYY-MM-DD
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
    };
}

function addAnswer(qr, name, value) {
    let i = qr.item.findIndex(e => e["linkId"] == name);
    if (value == null) {
        if (i !== -1) {
            qr.item.splice(i, 1); // Remove the item if value is null
        }
        return qr;
    }
    let q = qr.item[i]["answer"][0];
    if (q.valueString != null) {
        qr.item[i]["answer"][0]["valueString"] = value;
        return qr;
    }
    if (q.valueDate != null) {
        qr.item[i]["answer"][0]["valueDate"] = value;
        return qr;
    }
    if (q.valueInteger != null) {
        qr.item[i]["answer"][0]["valueInteger"] = value;
        return qr;
    }
    if (q.valueCoding != null) {
        qr.item[i]["answer"][0]["valueCoding"]["code"] = value;
        return qr;
    }
}

function addItem(qr, name, value, itemName) {
    let i = qr.item.findIndex(e => e["linkId"] == name);
    if (i === -1) return qr;
    let q = qr.item[i];
    qr.item[i] = addAnswer(q, itemName, value);

    let parentItem = qr.item[i];
    if (parentItem.item.length === 0) {
        qr.item.splice(i, 1);
    }

    return qr

}

function buildICVPQR(patient, immunization) {
    let qr = createQRICVP();
    //items obligatorios
    qr = addAnswer(qr, "name", patient["name"][0]["text"] || (patient["name"][0]["given"].join(" ") + " " + patient["name"][0]["family"]));
    qr = addAnswer(qr, "dob", patient["birthDate"]);
    let productIDExtension = immunization["extension"] ? immunization["extension"].find(e => e["url"].indexOf("StructureDefinition/ProductID") >= 0) : null;
    let productID = productIDExtension?.["valueCoding"]?.["code"];
    if (!productID) {
        console.warn("ProductID extension not found in immunization");
        return null;
    }
    qr = addItem(qr, "vaccineDetails", productID, "productID");
    qr = addItem(qr, "vaccineDetails", immunization["occurrenceDateTime"].split("T")[0], "date");
    qr = addItem(qr, "vaccineDetails", immunization["lotNumber"], "batchNo.text");

    //opcionales
    qr = addAnswer(qr, "sex", patient["gender"] || null);
    let ext = patient["extension"] ? patient["extension"].find(e => e["url"].indexOf("/StructureDefinition/patient-nationality") >= 0) : null;
    if (ext && ext["valueCodeableConcept"] && ext["valueCodeableConcept"]["coding"] && ext["valueCodeableConcept"]["coding"]["code"]) {
        qr = addAnswer(qr, "nationality", ext["valueCodeableConcept"]["coding"]["code"]);
    } else {
        qr = addAnswer(qr, "nationality", null);
    }
    const taxIdentifier = patient["identifier"]?.find(id =>
        id["type"]?.["coding"]?.some(coding => coding["code"] === "TAX")
    )?.["value"] || patient["identifier"][0]["value"];
    qr = addAnswer(qr, "nid", taxIdentifier);

    const guardianGiven = patient["contact"]?.[0]?.["name"]?.[0]?.["given"]?.join(" ") || "";
    const guardianFamily = patient["contact"]?.[0]?.["name"]?.[0]?.["family"] || "";
    const guardianName = (guardianGiven + " " + guardianFamily).trim() || null;
    qr = addItem(qr, "guardian", guardianName, "guardianName");
    qr = addItem(qr, "guardian", patient["contact"]?.[0]?.["relationship"]?.["coding"]?.[0]?.["code"] || null, "guardianRelationship");

    qr = addItem(qr, "vaccineDetails", immunization["performer"]?.["reference"] || null, "clinicianName");
    qr = addItem(qr, "vaccineDetails", immunization["manufacturer"]?.["reference"] || null, "issuer");

    let vaccineDetailsId = qr.item.findIndex(e => e["linkId"] == "vaccineDetails");
    qr.item[vaccineDetailsId] = addItem(qr.item[vaccineDetailsId], "validityPeriod", immunization["occurrenceDateTime"]?.split("T")[0] || null, "startDate");
    qr.item[vaccineDetailsId] = addItem(qr.item[vaccineDetailsId], "validityPeriod", immunization["expirationDate"]?.split("T")[0] || null, "endDate");

    return qr
}

module.exports = {
    buildICVPQR,
}