import pandas as pd
import json
import uuid
import tarfile
import os
import tempfile
import argparse
import sys



# Constants
cie10_uri = "http://hl7.org/fhir/sid/icd-10"
cie11_uri = "http://id.who.int/icd/release/11/mms"
snomed_uri = "http://snomed.info/sct"
prequal_uri = "http://smart.who.int/pcmt-vaxprequal/CodeSystem/PreQualProductIDs"

temp_dir = tempfile.gettempdir()

def main():
    parser = argparse.ArgumentParser(description="Convert Excel terminology data to FHIR package with ValueSet-based concept maps.")
    parser.add_argument("source_file", help="The source file to process")

    args = parser.parse_args()

    print(f"Source file: {args.source_file}")
    print("Using unified CodeSystems with ValueSet-based concept maps")

    convert_to_fhir(args.source_file)


# Function to create a ValueSet JSON manually
def create_value_set_json(name, oid, concepts, uri=snomed_uri):
    value_set = {
        "resourceType": "ValueSet",
        "id": str(uuid.uuid4()),
        "url": f"http://racsel.org/fhir/ValueSet/{oid}",
        "name": name,
        "status": "active",
        "compose": {
            "include": [
                {
                    "system": uri,
                    "concept": [{"code": code, "display": display} for code, display in concepts]
                }
            ]
        }
    }
    return value_set

# Function to extract SNOMED concepts from a dataframe with unique rows
def extract_codes(df, code_col, display_col):
    return df.iloc[2:, [code_col, display_col]].dropna().drop_duplicates().values.tolist()

def extract_maps(df, source_code_col, source_display_col, target_code_col, target_display_col):
    return df.iloc[2:, [source_code_col, source_display_col, target_code_col, target_display_col]].dropna().values.tolist()

# Function to create a CodeSystem JSON fragment
def create_code_system_fragment(concepts_lists, code_system_uri, name):
    all_concepts = []
    # concepts are already extracted in the lists
    for concepts in concepts_lists:
        all_concepts.extend(concepts)
    
    code_system = {
        "resourceType": "CodeSystem",
        "id": str(uuid.uuid4()),
        "url": code_system_uri,
        "name": name,
        "version": "2024",
        "status": "active",
        "content": "fragment",
        "concept": [{"code": code, "display": display} for code, display in all_concepts]
    }
    return code_system

# Function to create a ConceptMap JSON
def create_concept_map(map_values, sourceUri, targetUri, name):
    conceptMap = {
        "resourceType": "ConceptMap",
        "id": str(uuid.uuid4()),
        "url": str(sourceUri) + "/" + name.replace(" ", "-").lower(),
        "name": name,
        "version": "2024",
        "status": "active",
        "sourceUri": sourceUri,
        "targetUri": targetUri,
        "group": []
    }
    
    # Add group if there map values
    add_group_to_concept_map(conceptMap, sourceUri, targetUri, map_values)

    return conceptMap

# Function to create a ValueSet-based ConceptMap JSON
def create_valueset_concept_map(map_values, sourceValueSetUrl, targetValueSetUrl, sourceSystemUri, targetSystemUri, name):
    conceptMap = {
        "resourceType": "ConceptMap",
        "id": str(uuid.uuid4()),
        "url": f"http://racsel.org/fhir/ConceptMap/{name.replace(' ', '-').lower()}",
        "name": name.replace(" ", ""),
        "version": "2024",
        "status": "active",
        "sourceCanonical": sourceValueSetUrl,
        "targetCanonical": targetValueSetUrl,
        "group": []
    }
    
    # Add group if there are map values
    add_group_to_valueset_concept_map(conceptMap, sourceSystemUri, targetSystemUri, map_values)

    return conceptMap

def add_group_to_concept_map(conceptMap, sourceUri, targetUri, map_values):
    if len(map_values) > 0:
        conceptMap["group"].append({
            "source": sourceUri,
            "target": targetUri,
            "element": [{"code": sourceCode, "display": sourceDisplay, "target": [{"code": targetCode, "display": targetDisplay, "equivalence": "equivalent"}]} for sourceCode, sourceDisplay, targetCode, targetDisplay in map_values]
        })

def add_group_to_valueset_concept_map(conceptMap, sourceSystemUri, targetSystemUri, map_values):
    if len(map_values) > 0:
        conceptMap["group"].append({
            "source": sourceSystemUri,
            "target": targetSystemUri,
            "element": [{"code": sourceCode, "display": sourceDisplay, "target": [{"code": targetCode, "display": targetDisplay, "equivalence": "equivalent"}]} for sourceCode, sourceDisplay, targetCode, targetDisplay in map_values]
        })

# Function to convert the Excel file to FHIR
def convert_to_fhir(file_path):
    # Load all sheets into dataframes
    antecedentes_df = pd.read_excel(file_path, sheet_name='Antecedentes Personales ')
    diagnosticos_df = pd.read_excel(file_path, sheet_name='Diagnósticos')
    vacunas_df = pd.read_excel(file_path, sheet_name='Vacunas')
    alergias_df = pd.read_excel(file_path, sheet_name='Alergias')
    medicacion_df = pd.read_excel(file_path, sheet_name='Medicación ')
    procedimientos_df = pd.read_excel(file_path, sheet_name='Procedimientos')
    
    # set the local uri to default or colmuns(2_ in antecedentes_df if it exists
    local_uri = antecedentes_df.columns[2] if antecedentes_df.columns[2] else "http://node-x.org/terminology/default"

    # Extract codes from each sheet
    antecedentes_concepts = extract_codes(antecedentes_df, 7, 8)
    antecedentes_racsel = extract_codes(antecedentes_df, 1, 2)
    antecedentes_cie10 = extract_codes(antecedentes_df, 5, 6)
    antecedentes_local = extract_codes(antecedentes_df, 3, 4)
    diagnosticos_concepts = extract_codes(diagnosticos_df, 7, 8)
    diagnosticos_racsel = extract_codes(diagnosticos_df, 1, 2)
    diagnosticos_cie10 = extract_codes(diagnosticos_df, 5, 6)
    diagnosticos_local = extract_codes(diagnosticos_df, 3, 4)
    vacunas_concepts = extract_codes(vacunas_df, 7, 8)
    vacunas_racsel = extract_codes(vacunas_df, 1, 2)
    vacunas_cie11 = extract_codes(vacunas_df, 5, 6)
    vacunas_local = extract_codes(vacunas_df, 3, 4)
    alergias_concepts = extract_codes(alergias_df, 7, 8)
    alergias_racsel = extract_codes(alergias_df, 1, 2)
    alergias_local = extract_codes(alergias_df, 3, 4)
    medicacion_concepts = extract_codes(medicacion_df, 7, 8)
    medicacion_racsel = extract_codes(medicacion_df, 1, 2)
    medicacion_local = extract_codes(medicacion_df, 3, 4)
    procedimientos_concepts = extract_codes(procedimientos_df, 7, 8)
    procedimientos_racsel = extract_codes(procedimientos_df, 1, 2)
    procedimientos_local = extract_codes(procedimientos_df, 3, 4)
    #prequal
    vacunas_prequal_concepts = extract_codes(vacunas_df, 9, 10)

    # Forward maps
    antecedentes_local_to_racsel = extract_maps(antecedentes_df, 3, 4, 1, 2)
    antecedentes_local_to_cie10 = extract_maps(antecedentes_df, 3, 4, 5, 6)
    antecedentes_local_to_snomed = extract_maps(antecedentes_df, 3, 4, 7, 8)
    diagnosticos_local_to_racsel = extract_maps(diagnosticos_df, 3, 4, 1, 2)
    diagnosticos_local_to_cie10 = extract_maps(diagnosticos_df, 3, 4, 5, 6)
    diagnosticos_local_to_snomed = extract_maps(diagnosticos_df, 3, 4, 7, 8)
    vacunas_local_to_racsel = extract_maps(vacunas_df, 3, 4, 1, 2)
    vacunas_local_to_cie11 = extract_maps(vacunas_df, 3, 4, 5, 6)
    vacunas_local_to_snomed = extract_maps(vacunas_df, 3, 4, 7, 8)
    alergias_local_to_racsel = extract_maps(alergias_df, 3, 4, 1, 2)
    alergias_local_to_snomed = extract_maps(alergias_df, 3, 4, 7, 8)
    medicacion_local_to_racsel = extract_maps(medicacion_df, 3, 4, 1, 2)
    medicacion_local_to_snomed = extract_maps(medicacion_df, 3, 4, 7, 8)
    procedimientos_local_to_racsel = extract_maps(procedimientos_df, 3, 4, 1, 2)
    procedimientos_local_to_snomed = extract_maps(procedimientos_df, 3, 4, 7, 8)
    antecedentes_cie10_to_snomed = extract_maps(antecedentes_df, 5, 6, 7, 8)
    diagnosticos_cie10_to_snomed = extract_maps(diagnosticos_df, 5, 6, 7, 8)
    vacunas_cie11_to_snomed = extract_maps(vacunas_df, 5, 6, 7, 8)
    #prequal
    vacunas_local_to_prequal = extract_maps(vacunas_df, 3, 4, 9, 10)
    vacunas_cie11_to_prequal = extract_maps(vacunas_df, 5, 6, 9, 10)
    vacunas_snomed_to_prequal = extract_maps(vacunas_df, 7, 8, 9, 10)


    # Reverse maps
    antecedentes_racsel_to_local = extract_maps(antecedentes_df, 1, 2, 3, 4)
    antecedentes_cie10_to_local = extract_maps(antecedentes_df, 5, 6, 3, 4)
    antecedentes_snomed_to_local = extract_maps(antecedentes_df, 7, 8, 3, 4)
    diagnosticos_racsel_to_local = extract_maps(diagnosticos_df, 1, 2, 3, 4)
    diagnosticos_cie10_to_local = extract_maps(diagnosticos_df, 5, 6, 3, 4)
    diagnosticos_snomed_to_local = extract_maps(diagnosticos_df, 7, 8, 3, 4)
    vacunas_racsel_to_local = extract_maps(vacunas_df, 1, 2, 3, 4)
    vacunas_cie11_to_local = extract_maps(vacunas_df, 5, 6, 3, 4)
    vacunas_snomed_to_local = extract_maps(vacunas_df, 7, 8, 3, 4)
    alergias_racsel_to_local = extract_maps(alergias_df, 1, 2, 3, 4)
    alergias_snomed_to_local = extract_maps(alergias_df, 7, 8, 3, 4)
    medicacion_racsel_to_local = extract_maps(medicacion_df, 1, 2, 3, 4)
    medicacion_snomed_to_local = extract_maps(medicacion_df, 7, 8, 3, 4)
    procedimientos_racsel_to_local = extract_maps(procedimientos_df, 1, 2, 3, 4)
    procedimientos_snomed_to_local = extract_maps(procedimientos_df, 7, 8, 3, 4)
    antecedentes_snomed_to_cie10 = extract_maps(antecedentes_df, 7, 8, 5, 6)
    diagnosticos_snomed_to_cie10 = extract_maps(diagnosticos_df, 7, 8, 5, 6)
    vacunas_snomed_to_cie11 = extract_maps(vacunas_df, 7, 8, 5, 6)

    #prequal
    vacunas_prequal_to_local = extract_maps(vacunas_df, 9, 10, 3, 4)
    vacunas_prequal_to_cie11 = extract_maps(vacunas_df, 9, 10, 5, 6)
    vacunas_prequal_to_snomed = extract_maps(vacunas_df, 9, 10, 7, 8)

    local_to_racsel = antecedentes_local_to_racsel + diagnosticos_local_to_racsel + vacunas_local_to_racsel + alergias_local_to_racsel + medicacion_local_to_racsel + procedimientos_local_to_racsel
    local_to_snomed = antecedentes_local_to_snomed + diagnosticos_local_to_snomed + vacunas_local_to_snomed + alergias_local_to_snomed + medicacion_local_to_snomed + procedimientos_local_to_snomed
    local_to_cie10 = antecedentes_local_to_cie10 + diagnosticos_local_to_cie10
    local_to_cie11 = vacunas_local_to_cie11
    cie10_to_snomed = antecedentes_cie10_to_snomed + diagnosticos_cie10_to_snomed
    cie11_to_snomed = vacunas_cie11_to_snomed
    cie11_to_local = vacunas_cie11_to_local
    racsel_to_local = antecedentes_racsel_to_local + diagnosticos_racsel_to_local + vacunas_racsel_to_local + alergias_racsel_to_local + medicacion_racsel_to_local + procedimientos_racsel_to_local
    cie10_to_local = antecedentes_cie10_to_local + diagnosticos_cie10_to_local
    snomed_to_local = antecedentes_snomed_to_local + diagnosticos_snomed_to_local + vacunas_snomed_to_local + alergias_snomed_to_local + medicacion_snomed_to_local + procedimientos_snomed_to_local
    snomed_to_cie10 = antecedentes_snomed_to_cie10 + diagnosticos_snomed_to_cie10
    snomed_to_cie11 = vacunas_snomed_to_cie11
    
    racselConnectathonUri = "http://racsel.org/connectathon"

    # Create ValueSet JSONs
    antecedentes_value_set_json = create_value_set_json("AntecedentesPersonalesValueSet", "antecedentes-personales-vs", antecedentes_concepts)
    antecentes_racsel_value_set_json = create_value_set_json("AntecedentesPersonalesRacselValueSet", "antecedentes-personales-racsel-vs", antecedentes_racsel, racselConnectathonUri)
    antecentes_local_value_set_json = create_value_set_json("AntecedentesPersonalesLocalValueSet", "antecedentes-personales-local-vs", antecedentes_local, local_uri)
    diagnosticos_value_set_json = create_value_set_json("DiagnosticosValueSet", "diagnosticos-vs", diagnosticos_concepts)
    diagnosticos_racsel_value_set_json = create_value_set_json("DiagnosticosRacselValueSet", "diagnosticos-racsel-vs", diagnosticos_racsel, racselConnectathonUri)
    diagnosticos_local_value_set_json = create_value_set_json("DiagnosticosLocalValueSet", "diagnosticos-local-vs", diagnosticos_local, local_uri)
    vacunas_value_set_json = create_value_set_json("VacunasValueSet", "vacunas-vs", vacunas_concepts)
    vacunas_racsel_value_set_json = create_value_set_json("VacunasRacselValueSet", "vacunas-racsel-vs", vacunas_racsel, racselConnectathonUri)
    vacunas_local_value_set_json = create_value_set_json("VacunasLocalValueSet", "vacunas-local-vs", vacunas_local, local_uri)
    alergias_value_set_json = create_value_set_json("AlergiasValueSet", "alergias-vs", alergias_concepts)
    alergias_racsel_value_set_json = create_value_set_json("AlergiasRacselValueSet", "alergias-racsel-vs", alergias_racsel, racselConnectathonUri)
    alergias_local_value_set_json = create_value_set_json("AlergiasLocalValueSet", "alergias-local-vs", alergias_local, local_uri)
    medicacion_value_set_json = create_value_set_json("MedicacionValueSet", "medicacion-vs", medicacion_concepts)
    medicacion_racsel_value_set_json = create_value_set_json("MedicacionRacselValueSet", "medicacion-racsel-vs", medicacion_racsel, racselConnectathonUri)
    medicacion_local_value_set_json = create_value_set_json("MedicacionLocalValueSet", "medicacion-local-vs", medicacion_local, local_uri)
    procedimientos_value_set_json = create_value_set_json("ProcedimientosValueSet", "procedimientos-vs", procedimientos_concepts)
    procedimientos_racsel_value_set_json = create_value_set_json("ProcedimientosRacselValueSet", "procedimientos-racsel-vs", procedimientos_racsel, racselConnectathonUri)
    procedimientos_local_value_set_json = create_value_set_json("ProcedimientosLocalValueSet", "procedimientos-local-vs", procedimientos_local, local_uri)
    racsel_value_set_json = create_value_set_json("RACSELValueSet", "racsel-vs", antecedentes_racsel + diagnosticos_racsel + vacunas_racsel + alergias_racsel + medicacion_racsel + procedimientos_racsel, racselConnectathonUri)
    cie10_value_set_json = create_value_set_json("CIE10ValueSet", "cie10-vs", antecedentes_cie10 + diagnosticos_cie10, cie10_uri)
    cie11_value_set_json = create_value_set_json("CIE11ValueSet", "cie11-vs", vacunas_cie11, cie11_uri)
    local_value_set_json = create_value_set_json("LocalValueSet", "local-vs", antecedentes_local + diagnosticos_local + vacunas_local + alergias_local + medicacion_local + procedimientos_local, local_uri)
    snomed_value_set_json = create_value_set_json("SNOMEDValueSet", "snomed-vs", antecedentes_concepts + diagnosticos_concepts + vacunas_concepts + alergias_concepts + medicacion_concepts + procedimientos_concepts, snomed_uri)  
    #prequal
    vacunas_prequal_value_set_json = create_value_set_json("PreQualValueSet", "prequal-vs", vacunas_prequal_concepts, prequal_uri)
    
    # Create CodeSystem JSONs - Unified approach
    conceptes_local_dfs = [antecedentes_local, diagnosticos_local, vacunas_local, alergias_local, medicacion_local, procedimientos_local]
    code_system_local_json = create_code_system_fragment(conceptes_local_dfs, local_uri, "LocalCodeSystem")
    
    concepts_dfs = [antecedentes_racsel, diagnosticos_racsel, vacunas_racsel, alergias_racsel, medicacion_racsel, procedimientos_racsel]
    code_system_json = create_code_system_fragment(concepts_dfs, racselConnectathonUri, "RACSELCodeSystem")
    concepts_cie10_dfs = [antecedentes_cie10, diagnosticos_cie10]
    code_system_cie10_json = create_code_system_fragment(concepts_cie10_dfs, cie10_uri, "icd-10")
    concepts_cie11_dfs = [vacunas_cie11]
    code_system_cie11_json = create_code_system_fragment(concepts_cie11_dfs, cie11_uri, "icd-11")
    
    #prequal
    concepts_prequal_dfs = [vacunas_prequal_concepts]
    code_system_prequal_json = create_code_system_fragment(concepts_prequal_dfs, prequal_uri, "prequal")

    # Create CodeSystem-based ConceptMaps - Unified approach
    local_to_racsel_map_json = create_concept_map(local_to_racsel, local_uri, racselConnectathonUri, "Local to RACSEL")
    local_to_snomed_map_json = create_concept_map(local_to_snomed, local_uri, snomed_uri, "Local to SNOMED")
    local_to_cie10_map_json = create_concept_map(local_to_cie10, local_uri, cie10_uri, "Local to CIE10")
    local_to_cie11_map_json = create_concept_map(local_to_cie11, local_uri, cie11_uri, "Local to CIE11")
    racsel_to_local_map_json = create_concept_map(racsel_to_local, racselConnectathonUri, local_uri, "RACSEL to Local")
    cie10_to_local_map_json = create_concept_map(cie10_to_local, cie10_uri, local_uri, "CIE10 to Local")
    cie11_to_local_map_json = create_concept_map(cie11_to_local, cie11_uri, local_uri, "CIE11 to Local")
    snomed_to_local_map_json = create_concept_map(snomed_to_local, snomed_uri, local_uri, "SNOMED to Local")
    
    cie10_to_snomed_map_json = create_concept_map(cie10_to_snomed, cie10_uri, snomed_uri, "CIE10 to SNOMED")
    cie11_to_snomed_map_json = create_concept_map(cie11_to_snomed, cie11_uri, snomed_uri, "CIE11 to SNOMED")
    snomed_to_cie10_map_json = create_concept_map(snomed_to_cie10, snomed_uri, cie10_uri, "SNOMED to CIE10")
    snomed_to_cie11_map_json = create_concept_map(snomed_to_cie11, snomed_uri, cie11_uri, "SNOMED to CIE11")

    #prequal
    vacunas_local_to_prequal_map_json = create_concept_map(vacunas_local_to_prequal, local_uri, prequal_uri, "Local to PreQual")
    vacunas_cie11_to_prequal_map_json = create_concept_map(vacunas_cie11_to_prequal, cie11_uri, prequal_uri, "CIE11 to PreQual")
    vacunas_snomed_to_prequal_map_json = create_concept_map(vacunas_snomed_to_prequal, snomed_uri, prequal_uri, "SNOMED to PreQual")
    vacunas_prequal_to_local_map_json = create_concept_map(vacunas_prequal_to_local, prequal_uri, local_uri, "PreQual to Local")
    vacunas_prequal_to_cie11_map_json = create_concept_map(vacunas_prequal_to_cie11, prequal_uri, cie11_uri, "Prequal to CIE11")
    vacunas_prequal_to_snomed_map_json = create_concept_map(vacunas_prequal_to_snomed, prequal_uri, snomed_uri, "PreQual to SNOMED")

    # Create ValueSet-based ConceptMaps
    
    # Domain-specific ValueSet to ValueSet mappings - Antecedentes
    vs_antecedentes_local_to_racsel_map = create_valueset_concept_map(
        antecedentes_local_to_racsel, 
        antecentes_local_value_set_json["url"], 
        antecentes_racsel_value_set_json["url"],
        local_uri,
        racselConnectathonUri,
        "VS Antecedentes Local to RACSEL"
    )
    vs_antecedentes_racsel_to_local_map = create_valueset_concept_map(
        antecedentes_racsel_to_local,
        antecentes_racsel_value_set_json["url"],
        antecentes_local_value_set_json["url"],
        racselConnectathonUri,
        local_uri,
        "VS Antecedentes RACSEL to Local"
    )
    vs_antecedentes_local_to_snomed_map = create_valueset_concept_map(
        antecedentes_local_to_snomed,
        antecentes_local_value_set_json["url"],
        antecedentes_value_set_json["url"],
        local_uri,
        snomed_uri,
        "VS Antecedentes Local to SNOMED"
    )
    vs_antecedentes_snomed_to_local_map = create_valueset_concept_map(
        antecedentes_snomed_to_local,
        antecedentes_value_set_json["url"],
        antecentes_local_value_set_json["url"],
        snomed_uri,
        local_uri,
        "VS Antecedentes SNOMED to Local"
    )
    # Create indirect RACSEL to SNOMED mappings via Local (for domains where direct mappings exist)
    vs_antecedentes_racsel_to_snomed_map = create_valueset_concept_map(
        # Create mapping by linking RACSEL->Local->SNOMED chains
        [(r[0], r[1], s[2], s[3]) for r in antecedentes_racsel_to_local for s in antecedentes_local_to_snomed if r[2] == s[0]],
        antecentes_racsel_value_set_json["url"],
        antecedentes_value_set_json["url"],
        racselConnectathonUri,
        snomed_uri,
        "VS Antecedentes RACSEL to SNOMED"
    )
    vs_antecedentes_snomed_to_racsel_map = create_valueset_concept_map(
        # Create reverse mapping by linking SNOMED->Local->RACSEL chains
        [(s[0], s[1], r[2], r[3]) for s in antecedentes_snomed_to_local for r in antecedentes_local_to_racsel if s[2] == r[0]],
        antecedentes_value_set_json["url"],
        antecentes_racsel_value_set_json["url"],
        snomed_uri,
        racselConnectathonUri,
        "VS Antecedentes SNOMED to RACSEL"
    )

    # Domain-specific ValueSet to ValueSet mappings - Diagnósticos
    vs_diagnosticos_local_to_racsel_map = create_valueset_concept_map(
        diagnosticos_local_to_racsel,
        diagnosticos_local_value_set_json["url"],
        diagnosticos_racsel_value_set_json["url"],
        local_uri,
        racselConnectathonUri,
        "VS Diagnosticos Local to RACSEL"
    )
    vs_diagnosticos_racsel_to_local_map = create_valueset_concept_map(
        diagnosticos_racsel_to_local,
        diagnosticos_racsel_value_set_json["url"],
        diagnosticos_local_value_set_json["url"],
        racselConnectathonUri,
        local_uri,
        "VS Diagnosticos RACSEL to Local"
    )
    vs_diagnosticos_local_to_snomed_map = create_valueset_concept_map(
        diagnosticos_local_to_snomed,
        diagnosticos_local_value_set_json["url"],
        diagnosticos_value_set_json["url"],
        local_uri,
        snomed_uri,
        "VS Diagnosticos Local to SNOMED"
    )
    vs_diagnosticos_snomed_to_local_map = create_valueset_concept_map(
        diagnosticos_snomed_to_local,
        diagnosticos_value_set_json["url"],
        diagnosticos_local_value_set_json["url"],
        snomed_uri,
        local_uri,
        "VS Diagnosticos SNOMED to Local"
    )
    vs_diagnosticos_local_to_cie10_map = create_valueset_concept_map(
        diagnosticos_local_to_cie10,
        diagnosticos_local_value_set_json["url"],
        cie10_value_set_json["url"],
        local_uri,
        cie10_uri,
        "VS Diagnosticos Local to CIE10"
    )
    vs_diagnosticos_cie10_to_local_map = create_valueset_concept_map(
        diagnosticos_cie10_to_local,
        cie10_value_set_json["url"],
        diagnosticos_local_value_set_json["url"],
        cie10_uri,
        local_uri,
        "VS Diagnosticos CIE10 to Local"
    )
    # RACSEL to SNOMED mappings for Diagnósticos
    vs_diagnosticos_racsel_to_snomed_map = create_valueset_concept_map(
        [(r[0], r[1], s[2], s[3]) for r in diagnosticos_racsel_to_local for s in diagnosticos_local_to_snomed if r[2] == s[0]],
        diagnosticos_racsel_value_set_json["url"],
        diagnosticos_value_set_json["url"],
        racselConnectathonUri,
        snomed_uri,
        "VS Diagnosticos RACSEL to SNOMED"
    )
    vs_diagnosticos_snomed_to_racsel_map = create_valueset_concept_map(
        [(s[0], s[1], r[2], r[3]) for s in diagnosticos_snomed_to_local for r in diagnosticos_local_to_racsel if s[2] == r[0]],
        diagnosticos_value_set_json["url"],
        diagnosticos_racsel_value_set_json["url"],
        snomed_uri,
        racselConnectathonUri,
        "VS Diagnosticos SNOMED to RACSEL"
    )

    # Domain-specific ValueSet to ValueSet mappings - Vacunas
    vs_vacunas_local_to_racsel_map = create_valueset_concept_map(
        vacunas_local_to_racsel,
        vacunas_local_value_set_json["url"],
        vacunas_racsel_value_set_json["url"],
        local_uri,
        racselConnectathonUri,
        "VS Vacunas Local to RACSEL"
    )
    vs_vacunas_racsel_to_local_map = create_valueset_concept_map(
        vacunas_racsel_to_local,
        vacunas_racsel_value_set_json["url"],
        vacunas_local_value_set_json["url"],
        racselConnectathonUri,
        local_uri,
        "VS Vacunas RACSEL to Local"
    )
    vs_vacunas_local_to_snomed_map = create_valueset_concept_map(
        vacunas_local_to_snomed,
        vacunas_local_value_set_json["url"],
        vacunas_value_set_json["url"],
        local_uri,
        snomed_uri,
        "VS Vacunas Local to SNOMED"
    )
    vs_vacunas_snomed_to_local_map = create_valueset_concept_map(
        vacunas_snomed_to_local,
        vacunas_value_set_json["url"],
        vacunas_local_value_set_json["url"],
        snomed_uri,
        local_uri,
        "VS Vacunas SNOMED to Local"
    )
    vs_vacunas_local_to_cie11_map = create_valueset_concept_map(
        vacunas_local_to_cie11,
        vacunas_local_value_set_json["url"],
        cie11_value_set_json["url"],
        local_uri,
        cie11_uri,
        "VS Vacunas Local to CIE11"
    )
    vs_vacunas_cie11_to_local_map = create_valueset_concept_map(
        vacunas_cie11_to_local,
        cie11_value_set_json["url"],
        vacunas_local_value_set_json["url"],
        cie11_uri,
        local_uri,
        "VS Vacunas CIE11 to Local"
    )
    # RACSEL to SNOMED mappings for Vacunas
    vs_vacunas_racsel_to_snomed_map = create_valueset_concept_map(
        [(r[0], r[1], s[2], s[3]) for r in vacunas_racsel_to_local for s in vacunas_local_to_snomed if r[2] == s[0]],
        vacunas_racsel_value_set_json["url"],
        vacunas_value_set_json["url"],
        racselConnectathonUri,
        snomed_uri,
        "VS Vacunas RACSEL to SNOMED"
    )
    vs_vacunas_snomed_to_racsel_map = create_valueset_concept_map(
        [(s[0], s[1], r[2], r[3]) for s in vacunas_snomed_to_local for r in vacunas_local_to_racsel if s[2] == r[0]],
        vacunas_value_set_json["url"],
        vacunas_racsel_value_set_json["url"],
        snomed_uri,
        racselConnectathonUri,
        "VS Vacunas SNOMED to RACSEL"
    )


    #prequal
    vs_vacunas_local_to_prequal_map = create_valueset_concept_map(
        vacunas_local_to_prequal,
        vacunas_local_value_set_json["url"],
        vacunas_prequal_value_set_json["url"],
        local_uri,
        prequal_uri,
        "VS Vacunas Local to PreQual"
    )

    vs_vacunas_cie11_to_prequal_map = create_valueset_concept_map(
        vacunas_cie11_to_prequal,
        cie11_value_set_json["url"],
        vacunas_prequal_value_set_json["url"],
        local_uri,
        prequal_uri,
        "VS Vacunas CIE11 to PreQual"
    )

    vs_vacunas_snomed_to_prequal_map = create_valueset_concept_map(
        vacunas_snomed_to_prequal,
        snomed_value_set_json["url"],
        vacunas_prequal_value_set_json["url"],
        local_uri,
        snomed_uri,
        "VS Vacunas SNOMED to PreQual"
    )
    
    #prequal
    vs_vacunas_prequal_to_local_map = create_valueset_concept_map(
        vacunas_prequal_to_local,
        vacunas_prequal_value_set_json["url"],
        vacunas_local_value_set_json["url"],
        prequal_uri,
        local_uri,
        "VS Vacunas PreQual to Local"
    )


    vs_vacunas_prequal_to_cie11_map =  create_valueset_concept_map(
        vacunas_prequal_to_cie11,
        vacunas_prequal_value_set_json["url"],
        cie11_value_set_json["url"],
        prequal_uri,
        cie11_uri,
        "VS Vacunas PreQual to CIE11"
    )

    vs_vacunas_prequal_to_snomed_map =  create_valueset_concept_map(
        vacunas_prequal_to_snomed,
        vacunas_prequal_value_set_json["url"],
        snomed_value_set_json["url"],
        prequal_uri,
        snomed_uri,
        "VS Vacunas PreQual to SNOMED"
    )






    # Domain-specific ValueSet to ValueSet mappings - Alergias
    vs_alergias_local_to_racsel_map = create_valueset_concept_map(
        alergias_local_to_racsel,
        alergias_local_value_set_json["url"],
        alergias_racsel_value_set_json["url"],
        local_uri,
        racselConnectathonUri,
        "VS Alergias Local to RACSEL"
    )
    vs_alergias_racsel_to_local_map = create_valueset_concept_map(
        alergias_racsel_to_local,
        alergias_racsel_value_set_json["url"],
        alergias_local_value_set_json["url"],
        racselConnectathonUri,
        local_uri,
        "VS Alergias RACSEL to Local"
    )
    vs_alergias_local_to_snomed_map = create_valueset_concept_map(
        alergias_local_to_snomed,
        alergias_local_value_set_json["url"],
        alergias_value_set_json["url"],
        local_uri,
        snomed_uri,
        "VS Alergias Local to SNOMED"
    )
    vs_alergias_snomed_to_local_map = create_valueset_concept_map(
        alergias_snomed_to_local,
        alergias_value_set_json["url"],
        alergias_local_value_set_json["url"],
        snomed_uri,
        local_uri,
        "VS Alergias SNOMED to Local"
    )
    
    # RACSEL to SNOMED mappings for Alergias
    vs_alergias_racsel_to_snomed_map = create_valueset_concept_map(
        [(r[0], r[1], s[2], s[3]) for r in alergias_racsel_to_local for s in alergias_local_to_snomed if r[2] == s[0]],
        alergias_racsel_value_set_json["url"],
        alergias_value_set_json["url"],
        racselConnectathonUri,
        snomed_uri,
        "VS Alergias RACSEL to SNOMED"
    )

    vs_alergias_snomed_to_racsel_map = create_valueset_concept_map(
        [(s[0], s[1], r[2], r[3]) for s in alergias_snomed_to_local for r in alergias_local_to_racsel if s[2] == r[0]],
        alergias_value_set_json["url"],
        alergias_racsel_value_set_json["url"],
        snomed_uri,
        racselConnectathonUri,
        "VS Alergias SNOMED to RACSEL"
    )

    # Domain-specific ValueSet to ValueSet mappings - Medicación
    vs_medicacion_local_to_racsel_map = create_valueset_concept_map(
        medicacion_local_to_racsel,
        medicacion_local_value_set_json["url"],
        medicacion_racsel_value_set_json["url"],
        local_uri,
        racselConnectathonUri,
        "VS Medicacion Local to RACSEL"
    )
    vs_medicacion_racsel_to_local_map = create_valueset_concept_map(
        medicacion_racsel_to_local,
        medicacion_racsel_value_set_json["url"],
        medicacion_local_value_set_json["url"],
        racselConnectathonUri,
        local_uri,
        "VS Medicacion RACSEL to Local"
    )
    vs_medicacion_local_to_snomed_map = create_valueset_concept_map(
        medicacion_local_to_snomed,
        medicacion_local_value_set_json["url"],
        medicacion_value_set_json["url"],
        local_uri,
        snomed_uri,
        "VS Medicacion Local to SNOMED"
    )
    vs_medicacion_snomed_to_local_map = create_valueset_concept_map(
        medicacion_snomed_to_local,
        medicacion_value_set_json["url"],
        medicacion_local_value_set_json["url"],
        snomed_uri,
        local_uri,
        "VS Medicacion SNOMED to Local"
    )
    # RACSEL to SNOMED mappings for Medicación
    vs_medicacion_racsel_to_snomed_map = create_valueset_concept_map(
        [(r[0], r[1], s[2], s[3]) for r in medicacion_racsel_to_local for s in medicacion_local_to_snomed if r[2] == s[0]],
        medicacion_racsel_value_set_json["url"],
        medicacion_value_set_json["url"],
        racselConnectathonUri,
        snomed_uri,
        "VS Medicacion RACSEL to SNOMED"
    )
    vs_medicacion_snomed_to_racsel_map = create_valueset_concept_map(
        [(s[0], s[1], r[2], r[3]) for s in medicacion_snomed_to_local for r in medicacion_local_to_racsel if s[2] == r[0]],
        medicacion_value_set_json["url"],
        medicacion_racsel_value_set_json["url"],
        snomed_uri,
        racselConnectathonUri,
        "VS Medicacion SNOMED to RACSEL"
    )

    # Domain-specific ValueSet to ValueSet mappings - Procedimientos
    vs_procedimientos_local_to_racsel_map = create_valueset_concept_map(
        procedimientos_local_to_racsel,
        procedimientos_local_value_set_json["url"],
        procedimientos_racsel_value_set_json["url"],
        local_uri,
        racselConnectathonUri,
        "VS Procedimientos Local to RACSEL"
    )
    vs_procedimientos_racsel_to_local_map = create_valueset_concept_map(
        procedimientos_racsel_to_local,
        procedimientos_racsel_value_set_json["url"],
        procedimientos_local_value_set_json["url"],
        racselConnectathonUri,
        local_uri,
        "VS Procedimientos RACSEL to Local"
    )
    vs_procedimientos_local_to_snomed_map = create_valueset_concept_map(
        procedimientos_local_to_snomed,
        procedimientos_local_value_set_json["url"],
        procedimientos_value_set_json["url"],
        local_uri,
        snomed_uri,
        "VS Procedimientos Local to SNOMED"
    )
    vs_procedimientos_snomed_to_local_map = create_valueset_concept_map(
        procedimientos_snomed_to_local,
        procedimientos_value_set_json["url"],
        procedimientos_local_value_set_json["url"],
        snomed_uri,
        local_uri,
        "VS Procedimientos SNOMED to Local"
    )
    # RACSEL to SNOMED mappings for Procedimientos
    vs_procedimientos_racsel_to_snomed_map = create_valueset_concept_map(
        [(r[0], r[1], s[2], s[3]) for r in procedimientos_racsel_to_local for s in procedimientos_local_to_snomed if r[2] == s[0]],
        procedimientos_racsel_value_set_json["url"],
        procedimientos_value_set_json["url"],
        racselConnectathonUri,
        snomed_uri,
        "VS Procedimientos RACSEL to SNOMED"
    )
    vs_procedimientos_snomed_to_racsel_map = create_valueset_concept_map(
        [(s[0], s[1], r[2], r[3]) for s in procedimientos_snomed_to_local for r in procedimientos_local_to_racsel if s[2] == r[0]],
        procedimientos_value_set_json["url"],
        procedimientos_racsel_value_set_json["url"],
        snomed_uri,
        racselConnectathonUri,
        "VS Procedimientos SNOMED to RACSEL"
    )

    # Global ValueSet to ValueSet mappings
    vs_local_to_racsel_global_map = create_valueset_concept_map(
        local_to_racsel,
        local_value_set_json["url"],
        racsel_value_set_json["url"],
        local_uri,
        racselConnectathonUri,
        "VS Local Global to RACSEL Global"
    )
    vs_racsel_to_local_global_map = create_valueset_concept_map(
        racsel_to_local,
        racsel_value_set_json["url"],
        local_value_set_json["url"],
        racselConnectathonUri,
        local_uri,
        "VS RACSEL Global to Local Global"
    )
    vs_local_to_snomed_global_map = create_valueset_concept_map(
        local_to_snomed,
        local_value_set_json["url"],
        snomed_value_set_json["url"],
        local_uri,
        snomed_uri,
        "VS Local Global to SNOMED Global"
    )
    vs_snomed_to_local_global_map = create_valueset_concept_map(
        snomed_to_local,
        snomed_value_set_json["url"],
        local_value_set_json["url"],
        snomed_uri,
        local_uri,
        "VS SNOMED Global to Local Global"
    )
    vs_cie10_to_snomed_global_map = create_valueset_concept_map(
        cie10_to_snomed,
        cie10_value_set_json["url"],
        snomed_value_set_json["url"],
        cie10_uri,
        snomed_uri,
        "VS CIE10 Global to SNOMED Global"
    )
    vs_snomed_to_cie10_global_map = create_valueset_concept_map(
        snomed_to_cie10,
        snomed_value_set_json["url"],
        cie10_value_set_json["url"],
        snomed_uri,
        cie10_uri,
        "VS SNOMED Global to CIE10 Global"
    )
    vs_cie11_to_snomed_global_map = create_valueset_concept_map(
        cie11_to_snomed,
        cie11_value_set_json["url"],
        snomed_value_set_json["url"],
        cie11_uri,
        snomed_uri,
        "VS CIE11 Global to SNOMED Global"
    )
    vs_snomed_to_cie11_global_map = create_valueset_concept_map(
        snomed_to_cie11,
        snomed_value_set_json["url"],
        cie11_value_set_json["url"],
        snomed_uri,
        cie11_uri,
        "VS SNOMED Global to CIE11 Global"
    )


    # prepare FHIR package

    # Create the package manifest (package.json)
    package_manifest = {
        "name": "racsel.connectathon",
        "version": "1.0.0",
        "description": "RACSEL Connectathon FHIR Package",
        "fhirVersion": "4.0.1",
        "dependencies": {},
        "author": "RACSEL",
        "url": "http://racsel.org",
        "resources": []
    }

    # Create the .index.json file
    index_file = {
        "index-version": 1,
        "files": []
    }

    # Resources list
    resources = [
        (antecedentes_value_set_json, "package/ValueSet/AntecedentesPersonalesValueSet.json"),
        (antecentes_racsel_value_set_json, "package/ValueSet/AntecedentesPersonalesRacselValueSet.json"),
        (antecentes_local_value_set_json, "package/ValueSet/AntecedentesPersonalesLocalValueSet.json"),
        (diagnosticos_value_set_json, "package/ValueSet/DiagnosticosValueSet.json"),
        (diagnosticos_racsel_value_set_json, "package/ValueSet/DiagnosticosRacselValueSet.json"),
        (diagnosticos_local_value_set_json, "package/ValueSet/DiagnosticosLocalValueSet.json"),
        (vacunas_value_set_json, "package/ValueSet/VacunasValueSet.json"),
        (vacunas_racsel_value_set_json, "package/ValueSet/VacunasRacselValueSet.json"),
        (vacunas_local_value_set_json, "package/ValueSet/VacunasLocalValueSet.json"),
        (alergias_value_set_json, "package/ValueSet/AlergiasValueSet.json"),
        (alergias_racsel_value_set_json, "package/ValueSet/AlergiasRacselValueSet.json"),
        (alergias_local_value_set_json, "package/ValueSet/AlergiasLocalValueSet.json"),
        (medicacion_value_set_json, "package/ValueSet/MedicacionValueSet.json"),
        (medicacion_racsel_value_set_json, "package/ValueSet/MedicacionRacselValueSet.json"),
        (medicacion_local_value_set_json, "package/ValueSet/MedicacionLocalValueSet.json"),
        (procedimientos_value_set_json, "package/ValueSet/ProcedimientosValueSet.json"),
        (procedimientos_racsel_value_set_json, "package/ValueSet/ProcedimientosRacselValueSet.json"),
        (procedimientos_local_value_set_json, "package/ValueSet/ProcedimientosLocalValueSet.json"),
        (racsel_value_set_json, "package/ValueSet/RACSELValueSet.json"),
        (local_value_set_json, "package/ValueSet/LocalValueSet.json"),
        (snomed_value_set_json, "package/ValueSet/SNOMEDValueSet.json"),
        (cie10_value_set_json, "package/ValueSet/CIE10ValueSet.json"),
        (cie11_value_set_json, "package/ValueSet/CIE11ValueSet.json"),
        (code_system_cie10_json, "package/CodeSystem/icd-10.json"),
        (code_system_cie11_json, "package/CodeSystem/icd-11.json"),
        (code_system_json, "package/CodeSystem/RACSELCodeSystem.json"),
        (code_system_local_json, "package/CodeSystem/LocalCodeSystem.json"),
        # CodeSystem-based ConceptMaps - Unified approach
            (local_to_racsel_map_json, "package/ConceptMap/Local-to-RACSEL.json"),
            (local_to_snomed_map_json, "package/ConceptMap/Local-to-SNOMED.json"),
            (local_to_cie10_map_json, "package/ConceptMap/Local-to-CIE10.json"),
            (local_to_cie11_map_json, "package/ConceptMap/Local-to-CIE11.json"),
            (racsel_to_local_map_json, "package/ConceptMap/RACSEL-to-Local.json"),
            (cie10_to_local_map_json, "package/ConceptMap/CIE10-to-Local.json"),
            (cie11_to_local_map_json, "package/ConceptMap/CIE11-to-Local.json"),
        (snomed_to_local_map_json, "package/ConceptMap/SNOMED-to-Local.json"),
        (cie10_to_snomed_map_json, "package/ConceptMap/CIE10-to-SNOMED.json"),
        (cie11_to_snomed_map_json, "package/ConceptMap/CIE11-to-SNOMED.json"),
        (snomed_to_cie10_map_json, "package/ConceptMap/SNOMED-to-CIE10.json"),
        (snomed_to_cie11_map_json, "package/ConceptMap/SNOMED-to-CIE11.json"),
        # ValueSet-based ConceptMaps - Global mappings
        (vs_local_to_racsel_global_map, "package/ConceptMap/VS-Local-Global-to-RACSEL-Global.json"),
        (vs_racsel_to_local_global_map, "package/ConceptMap/VS-RACSEL-Global-to-Local-Global.json"),
        (vs_local_to_snomed_global_map, "package/ConceptMap/VS-Local-Global-to-SNOMED-Global.json"),
        (vs_snomed_to_local_global_map, "package/ConceptMap/VS-SNOMED-Global-to-Local-Global.json"),
        (vs_cie10_to_snomed_global_map, "package/ConceptMap/VS-CIE10-Global-to-SNOMED-Global.json"),
        (vs_snomed_to_cie10_global_map, "package/ConceptMap/VS-SNOMED-Global-to-CIE10-Global.json"),
        (vs_cie11_to_snomed_global_map, "package/ConceptMap/VS-CIE11-Global-to-SNOMED-Global.json"),
        (vs_snomed_to_cie11_global_map, "package/ConceptMap/VS-SNOMED-Global-to-CIE11-Global.json"),
        # ValueSet-based ConceptMaps - Domain-specific Antecedentes
        (vs_antecedentes_local_to_racsel_map, "package/ConceptMap/VS-Antecedentes-Local-to-RACSEL.json"),
        (vs_antecedentes_racsel_to_local_map, "package/ConceptMap/VS-Antecedentes-RACSEL-to-Local.json"),
        (vs_antecedentes_local_to_snomed_map, "package/ConceptMap/VS-Antecedentes-Local-to-SNOMED.json"),
        (vs_antecedentes_snomed_to_local_map, "package/ConceptMap/VS-Antecedentes-SNOMED-to-Local.json"),
        (vs_antecedentes_racsel_to_snomed_map, "package/ConceptMap/VS-Antecedentes-RACSEL-to-SNOMED.json"),
        (vs_antecedentes_snomed_to_racsel_map, "package/ConceptMap/VS-Antecedentes-SNOMED-to-RACSEL.json"),
        # ValueSet-based ConceptMaps - Domain-specific Diagnósticos
        (vs_diagnosticos_local_to_racsel_map, "package/ConceptMap/VS-Diagnosticos-Local-to-RACSEL.json"),
        (vs_diagnosticos_racsel_to_local_map, "package/ConceptMap/VS-Diagnosticos-RACSEL-to-Local.json"),
        (vs_diagnosticos_local_to_snomed_map, "package/ConceptMap/VS-Diagnosticos-Local-to-SNOMED.json"),
        (vs_diagnosticos_snomed_to_local_map, "package/ConceptMap/VS-Diagnosticos-SNOMED-to-Local.json"),
        (vs_diagnosticos_local_to_cie10_map, "package/ConceptMap/VS-Diagnosticos-Local-to-CIE10.json"),
        (vs_diagnosticos_cie10_to_local_map, "package/ConceptMap/VS-Diagnosticos-CIE10-to-Local.json"),
        (vs_diagnosticos_racsel_to_snomed_map, "package/ConceptMap/VS-Diagnosticos-RACSEL-to-SNOMED.json"),
        (vs_diagnosticos_snomed_to_racsel_map, "package/ConceptMap/VS-Diagnosticos-SNOMED-to-RACSEL.json"),
        # ValueSet-based ConceptMaps - Domain-specific Vacunas
        (vs_vacunas_local_to_racsel_map, "package/ConceptMap/VS-Vacunas-Local-to-RACSEL.json"),
        (vs_vacunas_racsel_to_local_map, "package/ConceptMap/VS-Vacunas-RACSEL-to-Local.json"),
        (vs_vacunas_local_to_snomed_map, "package/ConceptMap/VS-Vacunas-Local-to-SNOMED.json"),
        (vs_vacunas_snomed_to_local_map, "package/ConceptMap/VS-Vacunas-SNOMED-to-Local.json"),
        (vs_vacunas_local_to_cie11_map, "package/ConceptMap/VS-Vacunas-Local-to-CIE11.json"),
        (vs_vacunas_cie11_to_local_map, "package/ConceptMap/VS-Vacunas-CIE11-to-Local.json"),
        (vs_vacunas_racsel_to_snomed_map, "package/ConceptMap/VS-Vacunas-RACSEL-to-SNOMED.json"),
        (vs_vacunas_snomed_to_racsel_map, "package/ConceptMap/VS-Vacunas-SNOMED-to-RACSEL.json"),

        #prequal
        (code_system_prequal_json, "package/CodeSystem/PreQualCodeSystem.json"),
        #prequal vs 
        (vacunas_prequal_value_set_json, "package/ValueSet/VacunasPreQualValueSet.json"),
        #prequal maps based on valueset
        (vs_vacunas_local_to_prequal_map, "package/ConceptMap/VS-Vacunas-Local-to-Prequal.json"),
        (vs_vacunas_cie11_to_prequal_map, "package/ConceptMap/VS-Vacunas-CIE11-to-Prequal.json"),
        (vs_vacunas_snomed_to_prequal_map, "package/ConceptMap/VS-Vacunas-SNOMED-to-Prequal.json"),
        (vs_vacunas_prequal_to_local_map, "package/ConceptMap/VS-Vacunas-Prequal-to-Local.json"),
        (vs_vacunas_prequal_to_cie11_map, "package/ConceptMap/VS-Vacunas-PreQual-to-CIE11.json"),
        (vs_vacunas_prequal_to_snomed_map, "package/ConceptMap/VS-Vacunas-PreQual-to-SNOMED.json"),

        # ValueSet-based ConceptMaps - Domain-specific Alergias
        (vs_alergias_local_to_racsel_map, "package/ConceptMap/VS-Alergias-Local-to-RACSEL.json"),
        (vs_alergias_racsel_to_local_map, "package/ConceptMap/VS-Alergias-RACSEL-to-Local.json"),
        (vs_alergias_local_to_snomed_map, "package/ConceptMap/VS-Alergias-Local-to-SNOMED.json"),
        (vs_alergias_snomed_to_local_map, "package/ConceptMap/VS-Alergias-SNOMED-to-Local.json"),
        (vs_alergias_racsel_to_snomed_map, "package/ConceptMap/VS-Alergias-RACSEL-to-SNOMED.json"),
        (vs_alergias_snomed_to_racsel_map, "package/ConceptMap/VS-Alergias-SNOMED-to-RACSEL.json"),
        # ValueSet-based ConceptMaps - Domain-specific Medicación
        (vs_medicacion_local_to_racsel_map, "package/ConceptMap/VS-Medicacion-Local-to-RACSEL.json"),
        (vs_medicacion_racsel_to_local_map, "package/ConceptMap/VS-Medicacion-RACSEL-to-Local.json"),
        (vs_medicacion_local_to_snomed_map, "package/ConceptMap/VS-Medicacion-Local-to-SNOMED.json"),
        (vs_medicacion_snomed_to_local_map, "package/ConceptMap/VS-Medicacion-SNOMED-to-Local.json"),
        (vs_medicacion_racsel_to_snomed_map, "package/ConceptMap/VS-Medicacion-RACSEL-to-SNOMED.json"),
        (vs_medicacion_snomed_to_racsel_map, "package/ConceptMap/VS-Medicacion-SNOMED-to-RACSEL.json"),
        # ValueSet-based ConceptMaps - Domain-specific Procedimientos
        (vs_procedimientos_local_to_racsel_map, "package/ConceptMap/VS-Procedimientos-Local-to-RACSEL.json"),
        (vs_procedimientos_racsel_to_local_map, "package/ConceptMap/VS-Procedimientos-RACSEL-to-Local.json"),
        (vs_procedimientos_local_to_snomed_map, "package/ConceptMap/VS-Procedimientos-Local-to-SNOMED.json"),
        (vs_procedimientos_snomed_to_local_map, "package/ConceptMap/VS-Procedimientos-SNOMED-to-Local.json"),
        (vs_procedimientos_racsel_to_snomed_map, "package/ConceptMap/VS-Procedimientos-RACSEL-to-SNOMED.json"),
        (vs_procedimientos_snomed_to_racsel_map, "package/ConceptMap/VS-Procedimientos-SNOMED-to-RACSEL.json")
    ]


    # Add resources to manifests
    for resource, filename in resources:
        loopReference = {
            "filename": filename[8:],
            "resourceType": resource["resourceType"],
            "id": resource["id"],
            "kind": resource["resourceType"].lower(),
            "url": resource["url"]
        }

        # if resource has version add it to the reference
        if "version" in resource:
            loopReference["version"] = resource["version"]

        index_file["files"].append(loopReference)
        package_manifest["resources"].append({"type": resource["resourceType"], "reference": f"{resource['resourceType']}/{resource['name']}"})

    # Create the tgz file
    output_tgz_path = "racsel_fhir_package.tgz"
    with tarfile.open(output_tgz_path, "w:gz") as tar:
        # Add the package manifest
        manifest_path = os.path.join(temp_dir, "package.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(package_manifest, f, ensure_ascii=False, indent=2)
        tar.add(manifest_path, arcname="package/package.json")
        os.remove(manifest_path)

        # Add the .index.json file
        index_path = os.path.join(temp_dir, ".index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_file, f, ensure_ascii=False, indent=2)
        tar.add(index_path, arcname="package/.index.json")
        os.remove(index_path)
        
        # Add each resource to the appropriate folder in the tar file
        for resource, filename in resources:
            json_path = os.path.join("/tmp", os.path.basename(filename))
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(resource, f, ensure_ascii=False, indent=2)
            tar.add(json_path, arcname=filename)
            os.remove(json_path)  # Clean up the temporary file

    print(f"FHIR package saved to {output_tgz_path}")

    print(f'Load in Snowstorm with curl --form file=@{output_tgz_path} --form resourceUrls="*" http://localhost/fhir-admin/load-package (or equivalent in windows)')

if __name__ == "__main__":
    main()




