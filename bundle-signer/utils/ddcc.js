const { v4: uuidv4 } = require("uuid");

function createQR(){
    let id = uuidv4();
    let today = (new Date()).toISOString().substring(0,10);
    return {
        "resourceType": "Bundle",
        "id": id,
        "meta": {
          "profile": [
            "http://worldhealthorganization.github.io/ddcc/StructureDefinition/DDCCSubmitHealthEventRequest"
          ]
        },
        "type": "batch",
        "entry": [
          {
            "fullUrl": "http://www.example.org/fhir/Parameters/DDCCDemoParameters-1",
            "resource": {
              "resourceType": "Parameters",
              "id": id + "-params",
              "meta": {
                "profile": [
                  "http://worldhealthorganization.github.io/ddcc/StructureDefinition/DDCCGenerateHealthCertificateParameters"
                ]
              },
              "parameter": [
                {
                  "name": "response",
                  "resource": {
                    "resourceType": "QuestionnaireResponse",
                    "id": id + "-response",
                    "meta": {
                      "profile": [
                        "http://worldhealthorganization.github.io/ddcc/StructureDefinition/DDCCQuestionnaireResponse"
                      ]
                    },
                    "questionnaire": "http://worldhealthorganization.github.io/ddcc/DDCCVSCoreDataSetQuestionnaire",
                    "status": "completed",
                    "authored": today,
                    "item": [
                      {
                        "linkId": "name",
                        "answer": [
                          {
                            "valueString": "Eddie2 Murphy"
                          }
                        ]
                      },
                      {
                        "linkId": "birthDate",
                        "answer": [
                          {
                            "valueDate": "1986-09-19"
                          }
                        ]
                      },
                      {
                        "linkId": "identifier",
                        "answer": [
                          {
                            "valueString": "1234567890"
                          }
                        ]
                      },
                      {
                        "linkId": "sex",
                        "answer": [
                          {
                            "valueCoding": {
                              "code": "male",
                              "system": "http://hl7.org/fhir/administrative-gender"
                            }
                          }
                        ]
                      },
                      {
                        "linkId": "vaccine",
                        "answer": [
                          {
                            "valueCoding": {
                              "code": "XM9QW8",
                              "system": "http://id.who.int/icd11/mms"
                            }
                          }
                        ]
                      },
                      {
                        "linkId": "brand",
                        "answer": [
                          {
                            "valueCoding": {
                              "code": "TEST",
                              "system": "http://worldhealthorganization.github.io/ddcc/CodeSystem/DDCC-Example-Test-CodeSystem"
                            }
                          }
                        ]
                      },
                      {
                        "linkId": "lot",
                        "answer": [
                          {
                            "valueString": "PT123F"
                          }
                        ]
                      },
                      {
                        "linkId": "date",
                        "answer": [
                          {
                            "valueDate": "2021-07-08"
                          }
                        ]
                      },
                      {
                        "linkId": "dose",
                        "answer": [
                          {
                            "valueInteger": 3
                          }
                        ]
                      },
                      {
                        "linkId": "ma_holder",
                        "answer": [
                          {
                            "valueCoding": {
                              "code": "TEST",
                              "system": "http://worldhealthorganization.github.io/ddcc/CodeSystem/DDCC-Example-Test-CodeSystem"
                            }
                          }
                        ]
                      },
                      {
                        "linkId": "country",
                        "answer": [
                          {
                            "valueCoding": {
                              "code": "USA",
                              "system": "urn:iso:std:iso:3166"
                            }
                          }
                        ]
                      },
                      {
                        "linkId": "centre",
                        "answer": [
                          {
                            "valueString": "Vaccination Site"
                          }
                        ]
                      },
                      {
                        "linkId": "pha",
                        "answer": [
                          {
                            "valueString": "wA69g8VD512TfTTdkTNSsG1"
                          }
                        ]
                      },
                      {
                        "linkId": "hcid",
                        "answer": [
                          {
                            "valueString": "111000112"
                          }
                        ]
                      }
                    ]
                  }
                }
              ]
            },
            "request": {
              "method": "POST",
              "url": "QuestionnaireResponse/$generateHealthCertificate"
            }
          }
        ]
    }; 
}

function addAnswer(qr, name, value){
  if(value == null){
    return qr;
  }
  let i = qr.entry[0].resource.parameter[0].resource.item.findIndex(e => e["linkId"] == name);
  let q = qr.entry[0].resource.parameter[0].resource.item[i]["answer"][0];
  if(q.valueString){
      qr.entry[0].resource.parameter[0].resource.item[i]["answer"][0]["valueString"] = value;
      return qr;
  }
  if(q.valueDate){
      qr.entry[0].resource.parameter[0].resource.item[i]["answer"][0]["valueDate"] = value;
      return qr;
  }
  if(q.valueInteger){
      qr.entry[0].resource.parameter[0].resource.item[i]["answer"][0]["valueInteger"] = value;
      return qr;
  }
  if(q.valueCoding){
      qr.entry[0].resource.parameter[0].resource.item[i]["answer"][0]["valueCoding"]["code"] = value;
      return qr;
  }
}


function buildDDCCQR(patient, immunization, organization){
    let qr = createQR();
    qr = addAnswer(qr, "name", patient["name"][0]["given"].join(" ") + " " + patient["name"][0]["family"]);
    qr = addAnswer(qr, "birthDate", patient["birthDate"]);
    qr = addAnswer(qr, "identifier", patient["identifier"][0]["value"]);
    qr = addAnswer(qr, "sex", patient["gender"]);
    qr = addAnswer(qr, "vaccine", immunization["vaccineCode"]["coding"][0]["code"]);
    let ext = immunization["extension"] ? immunization["extension"].find(e => e["url"] == "http://worldhealthorganization.github.io/ddcc/StructureDefinition/DDCCEventBrand") : null;
    if(ext && ext["valueCoding"] && ext["valueCoding"]["code"]){
      qr = addAnswer(qr, "brand", ext["valueCoding"]["code"]);
    }
    qr = addAnswer(qr, "lot", immunization["lotNumber"]);
    qr = addAnswer(qr, "date", immunization["occurrenceDateTime"]);
    qr = addAnswer(qr, "dose", immunization["protocolApplied"] ? immunization["protocolApplied"][0]["doseNumberPositiveInt"] || 1 : 1);
    
    let ext2 = immunization["extension"] ? immunization["extension"].find(e => e["url"] == "http://worldhealthorganization.github.io/ddcc/StructureDefinition/DDCCCountryOfEvent") : null;
    if(ext2 && ext2["valueCode"]){
      qr = addAnswer(qr, "country", ext2["valueCode"]);
    }
    
    // qr = addAnswer(qr, "centre", null);
    qr = addAnswer(qr, "pha", organization["id"]);

    let ext3 = immunization["extension"] ? immunization["extension"].find(e => e["url"] == "http://worldhealthorganization.github.io/ddcc/StructureDefinition/DDCCVaccineMarketAuthorization") : null;
    if(ext3 && ext3["valueCoding"] && ext3["valueCoding"]["code"]){
      qr = addAnswer(qr, "ma_holder", ext3["valueCoding"]["code"]);
    }

    // qr = addAnswer(qr, "ma_holder", null);
    qr = addAnswer(qr, "hcid", immunization["id"]);
    return qr 
}

module.exports = {
    buildDDCCQR
}