const { v4: uuidv4 } = require("uuid");

function createQR(){
    let id = uuidv4();
    let today = (new Date()).toISOString().substring(0,10);
    return {
      "resourceType" : "QuestionnaireResponse",
      "id" : id,
      "text" : {
        "status" : "generated",
        "div" : "<div xmlns=\"http://www.w3.org/1999/xhtml\"></div>"
      },
      "questionnaire" : "http://smart.who.int/icvp/Questionnaire/Questionnaire-DVCModel",
      "status": "completed",
      "item": [
        {
          "linkId" : "name",
          "answer" : [
            {
              "valueString" : "Aulo Agerio"
            }
          ]
        },
        {
          "linkId" : "dob",
          "answer" : [
            {
              "valueDate" : "1905-08-23"
            }
          ]
        },
        {
          "linkId" : "sex",
          "answer" : [
            {
              "valueCoding" : {
                "system" : "http://terminology.hl7.org/CodeSystem/v2-0001",
                "code" : "M"
              }
            }
          ]
        },
        {
          "linkId" : "nationality",
          "answer" : [
            {
              "valueCoding" : {
                "system" : "urn:iso:std:iso:3166",
                "code" : "CL"
              }
            }
          ]
        },
        {
          "linkId" : "nid",
          "answer" : [
            {
              "valueString" : "16337361-9"
            }
          ]
        },
        {
          "linkId" : "guardian",
          "item" : [
            {
              "linkId" : "guardianName",
              "answer" : [
                {
                  "valueString" : "Juan Medina"
                }
              ]
            },
            {
              "linkId" : "guardianRelationship",
              "answer" : [
                {
                  "valueCoding" : {
                    "system" : "http://smart.who.int/icvp/CodeSystem/DVCRelationshipStatus",
                    "code" : "Parent"
                  }
                }
              ]
            }
          ]
        },
        {
          "linkId" : "vaccineDetails",
          "item" : [
            {
              "linkId" : "doseNumber",
              "answer" : [
                {
                  "valueCoding" : {
                    "system" : "http://smart.who.int/icvp/CodeSystem/doseNumber",
                    "code" : "Primary"
                  }
                }
              ]
            },
            {
              "linkId" : "disease",
              "answer" : [
                {
                  "valueCoding" : {
                    "system" : "http://id.who.int/icd/release/11/mms",
                    "code" : "1D47"
                  }
                }
              ]
            },
            {
              "linkId" : "vaccineClassification",
              "answer" : [
                {
                  "valueCoding" : {
                    "system" : "http://id.who.int/icd/release/11/mms",
                    "code" : "XM0N24"
                  }
                }
              ]
            },
            {
              "linkId" : "vaccineTradeItem",
              "answer" : [
                {
                  "valueString" : "1"
                }
              ]
            },
            {
              "linkId" : "date",
              "answer" : [
                {
                  "valueDate" : "1904-08-23"
                }
              ]
            },
            {
              "linkId" : "clinicianName",
              "answer" : [
                {
                  "valueString" : "Vacunador"
                }
              ]
            },
            {
              "linkId" : "issuer",
              "answer" : [
                {
                  "valueString" : "reference to organzation"
                }
              ]
            },
            {
              "linkId" : "manufacturerId",
              "answer" : [
                {
                  "valueString" : "25"
                }
              ]
            },
            {
              "linkId" : "manufacturer",
              "answer" : [
                {
                  "valueString" : "HIPRA"
                }
              ]
            },
            {
              "linkId" : "batchNo",
              "answer" : [
                {
                  "valueString" : "123123123"
                }
              ]
            },
            {
              "linkId" : "validityPeriod",
              "item" : [
                {
                  "linkId" : "startDate",
                  "answer" : [
                    {
                      "valueDate" : "2015-02-07"
                    }
                  ]
                },
                {
                  "linkId" : "endDate",
                  "answer" : [
                    {
                      "valueDate" : "2015-02-07"
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]    
    }
    
}

function addAnswer(qr, name, value){
  let i = qr.item.findIndex(e => e["linkId"] == name);
  if(value == null){
    if (i !== -1) {
      qr.item.splice(i, 1); // Remove the item if value is null
    }
    return qr;
  }
  let q = qr.item[i]["answer"][0];
  if(q.valueString){
      qr.item[i]["answer"][0]["valueString"] = value;
      return qr;
  }
  if(q.valueDate){
      qr.item[i]["answer"][0]["valueDate"] = value;
      return qr;
  }
  if(q.valueInteger){
      qr.item[i]["answer"][0]["valueInteger"] = value;
      return qr;
  }
  if(q.valueCoding){
      qr.item[i]["answer"][0]["valueCoding"]["code"] = value;
      return qr;
  }
}

function addItem(qr, name, value, itemName){
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

function buildDVCQR(patient, immunization, organization, composition){
    let qr = createQR();
    //items obligatorios
    qr = addAnswer(qr, "name", patient["name"][0]["given"].join(" ") + " " + patient["name"][0]["family"]);
    qr = addAnswer(qr, "dob", patient["birthDate"]);
    qr = addItem(qr, "vaccineDetails", immunization["protocolApplied"] ? immunization["protocolApplied"][0]["doseNumberPositiveInt"] || 1 : 1, "doseNumber");
    qr = addItem(qr, "vaccineDetails", immunization["protocolApplied"][0]["targetDisease"][0]["coding"][0]["code"], "disease");
    qr = addItem(qr, "vaccineDetails", immunization["vaccineCode"]["coding"][0]["code"], "vaccineClassification");
    qr = addItem(qr, "vaccineDetails", immunization["occurrenceDateTime"], "date");
    qr = addItem(qr, "vaccineDetails", organization["name"], "manufacturer");
    qr = addItem(qr, "vaccineDetails", immunization["lotNumber"], "batchNo");

    //opcionales
    qr = addAnswer(qr, "sex", patient["gender"] || null);
    qr = addAnswer(qr, "nationality", patient["address"]?.[0]?.["country"] || null);
    qr = addAnswer(qr, "nid", patient["identifier"]?.[1]?.["value"] || null);

    qr = addItem(qr, "guardian", patient["contact"]?.[0]?.["name"]?.[0]?.["given"].join(" ") + " " + patient["contact"]?.[0]?.["name"]?.[0]?.["family"] || null, "guardianName");
    qr = addItem(qr, "guardian", patient["contact"]?.[0]?.["relationship"]?.["coding"]?.[0]?.["code"] || null, "guardianRelationship");

    qr = addAnswer(qr, "vaccineTradeItem", immunization["identifier"]?.[0]?.["value"] || null);
    //clinicianName
    qr = addItem(qr, "vaccineDetails", immunization["manufacturer"]?.["reference"] || null, "issuer");
    qr = addItem(qr, "vaccineDetails", organization["identifier"]?.[0]?.["value"] || null, "manufacturerId");
    let vaccineDetailsId = qr.item.findIndex(e => e["linkId"] == "vaccineDetails");
    qr[vaccineDetailsId] = addItem(vaccineDetails, "validityPeriod", immunization["occurrenceDateTime"] || null, "startDate");
    qr[vaccineDetailsId] = addItem(vaccineDetails, "validityPeriod", immunization["expirationDate"] || null, "endDate");

    return qr 
}

module.exports = {
    buildDVCQR,
}