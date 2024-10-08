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

temp_dir = tempfile.gettempdir()

def main():
    parser = argparse.ArgumentParser(description="Process a source file with optional splitcs flag.")
    parser.add_argument("source_file", help="The source file to process")
    parser.add_argument("-splitcs", action="store_true", help="Splits local codesystem into separate resources by domain")

    args = parser.parse_args()

    print(f"Source file: {args.source_file}")
    print(f"Split Local Code Systems: {'Enabled' if args.splitcs else 'Disabled'}")

    convert_to_fhir(args.source_file, args.splitcs)


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

def add_group_to_concept_map(conceptMap, sourceUri, targetUri, map_values):
    if len(map_values) > 0:
        conceptMap["group"].append({
            "source": sourceUri,
            "target": targetUri,
            "element": [{"code": sourceCode, "display": sourceDisplay, "target": [{"code": targetCode, "display": targetDisplay, "equivalence": "equivalent"}]} for sourceCode, sourceDisplay, targetCode, targetDisplay in map_values]
        })

# Function to convert the Excel file to FHIR
def convert_to_fhir(file_path, splitcs=False):
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
    antecentes_local_value_set_json = create_value_set_json("AntecedentesPersonalesLocalValueSet", "antecedentes-personales-local-vs", antecedentes_local, local_uri + '/antecedentes' if splitcs else local_uri)
    diagnosticos_value_set_json = create_value_set_json("DiagnosticosValueSet", "diagnosticos-vs", diagnosticos_concepts)
    diagnosticos_racsel_value_set_json = create_value_set_json("DiagnosticosRacselValueSet", "diagnosticos-racsel-vs", diagnosticos_racsel, racselConnectathonUri)
    diagnosticos_local_value_set_json = create_value_set_json("DiagnosticosLocalValueSet", "diagnosticos-local-vs", diagnosticos_local, local_uri + '/diagnosticos' if splitcs else local_uri)
    vacunas_value_set_json = create_value_set_json("VacunasValueSet", "vacunas-vs", vacunas_concepts)
    vacunas_racsel_value_set_json = create_value_set_json("VacunasRacselValueSet", "vacunas-racsel-vs", vacunas_racsel, racselConnectathonUri)
    vacunas_local_value_set_json = create_value_set_json("VacunasLocalValueSet", "vacunas-local-vs", vacunas_local, local_uri + '/vacunas' if splitcs else local_uri)
    alergias_value_set_json = create_value_set_json("AlergiasValueSet", "alergias-vs", alergias_concepts)
    alergias_racsel_value_set_json = create_value_set_json("AlergiasRacselValueSet", "alergias-racsel-vs", alergias_racsel, racselConnectathonUri)
    alergias_local_value_set_json = create_value_set_json("AlergiasLocalValueSet", "alergias-local-vs", alergias_local, local_uri + '/alergias' if splitcs else local_uri)
    medicacion_value_set_json = create_value_set_json("MedicacionValueSet", "medicacion-vs", medicacion_concepts)
    medicacion_racsel_value_set_json = create_value_set_json("MedicacionRacselValueSet", "medicacion-racsel-vs", medicacion_racsel, racselConnectathonUri)
    medicacion_local_value_set_json = create_value_set_json("MedicacionLocalValueSet", "medicacion-local-vs", medicacion_local, local_uri + '/medicacion' if splitcs else local_uri)
    procedimientos_value_set_json = create_value_set_json("ProcedimientosValueSet", "procedimientos-vs", procedimientos_concepts)
    procedimientos_racsel_value_set_json = create_value_set_json("ProcedimientosRacselValueSet", "procedimientos-racsel-vs", procedimientos_racsel, racselConnectathonUri)
    procedimientos_local_value_set_json = create_value_set_json("ProcedimientosLocalValueSet", "procedimientos-local-vs", procedimientos_local, local_uri + '/procedimientos' if splitcs else local_uri)
    racsel_value_set_json = create_value_set_json("RACSELValueSet", "racsel-vs", antecedentes_racsel + diagnosticos_racsel + vacunas_racsel + alergias_racsel + medicacion_racsel + procedimientos_racsel, racselConnectathonUri)
    cie10_value_set_json = create_value_set_json("CIE10ValueSet", "cie10-vs", antecedentes_cie10 + diagnosticos_cie10, cie10_uri)
    cie11_value_set_json = create_value_set_json("CIE11ValueSet", "cie11-vs", vacunas_cie11, cie11_uri)
    local_value_set_json = create_value_set_json("LocalValueSet", "local-vs", antecedentes_local + diagnosticos_local + vacunas_local + alergias_local + medicacion_local + procedimientos_local, local_uri)
    snomed_value_set_json = create_value_set_json("SNOMEDValueSet", "snomed-vs", antecedentes_concepts + diagnosticos_concepts + vacunas_concepts + alergias_concepts + medicacion_concepts + procedimientos_concepts, snomed_uri)  

    # Create CodeSystem JSONs
    if (splitcs):
        conceptes_local_dfs_antecedentes = [antecedentes_local]
        code_system_local_json_antecedentes = create_code_system_fragment(conceptes_local_dfs_antecedentes, local_uri + "/antecedentes", "LocalAntecedentesCodeSystem")
        conceptes_local_dfs_diagnosticos = [diagnosticos_local]
        code_system_local_json_diagnosticos = create_code_system_fragment(conceptes_local_dfs_diagnosticos, local_uri + "/diagnosticos", "LocalDiagnosticosCodeSystem")
        conceptes_local_dfs_vacunas = [vacunas_local]
        code_system_local_json_vacunas = create_code_system_fragment(conceptes_local_dfs_vacunas, local_uri + "/vacunas", "LocalVacunasCodeSystem")
        conceptes_local_dfs_alergias = [alergias_local]
        code_system_local_json_alergias = create_code_system_fragment(conceptes_local_dfs_alergias, local_uri + "/alergias", "LocalAlergiasCodeSystem")
        conceptes_local_dfs_medicacion = [medicacion_local]
        code_system_local_json_medicacion = create_code_system_fragment(conceptes_local_dfs_medicacion, local_uri + "/medicacion", "LocalMedicacionCodeSystem")
        conceptes_local_dfs_procedimientos = [procedimientos_local]
        code_system_local_json_procedimientos = create_code_system_fragment(conceptes_local_dfs_procedimientos, local_uri + "/procedimientos", "LocalProcedimientosCodeSystem")
    else:
        conceptes_local_dfs = [antecedentes_local, diagnosticos_local, vacunas_local, alergias_local, medicacion_local, procedimientos_local]
        code_system_local_json = create_code_system_fragment(conceptes_local_dfs, local_uri, "LocalCodeSystem")
        
    concepts_dfs = [antecedentes_racsel, diagnosticos_racsel, vacunas_racsel, alergias_racsel, medicacion_racsel, procedimientos_racsel]
    code_system_json = create_code_system_fragment(concepts_dfs, racselConnectathonUri, "RACSELCodeSystem")
    concepts_cie10_dfs = [antecedentes_cie10, diagnosticos_cie10]
    code_system_cie10_json = create_code_system_fragment(concepts_cie10_dfs, cie10_uri, "icd-10")
    concepts_cie11_dfs = [vacunas_cie11]
    code_system_cie11_json = create_code_system_fragment(concepts_cie11_dfs, cie11_uri, "icd-11")

    # Create Conceptmap JSONs
    if (splitcs == False):
        local_to_racsel_map_json = create_concept_map(local_to_racsel, local_uri, racselConnectathonUri, "Local to RACSEL")
        local_to_snomed_map_json = create_concept_map(local_to_snomed, local_uri, snomed_uri, "Local to SNOMED")
        local_to_cie10_map_json = create_concept_map(local_to_cie10, local_uri, cie10_uri, "Local to CIE10")
        local_to_cie11_map_json = create_concept_map(local_to_cie11, local_uri, cie11_uri, "Local to CIE11")
        racsel_to_local_map_json = create_concept_map(racsel_to_local, racselConnectathonUri, local_uri, "RACSEL to Local")
        cie10_to_local_map_json = create_concept_map(cie10_to_local, cie10_uri, local_uri, "CIE10 to Local")
        cie11_to_local_map_json = create_concept_map(cie11_to_local, cie11_uri, local_uri, "CIE11 to Local")
        snomed_to_local_map_json = create_concept_map(snomed_to_local, snomed_uri, local_uri, "SNOMED to Local")
    else:
        local_antecedentes_to_racsel_map_json = create_concept_map(antecedentes_local_to_racsel, local_uri + '/antecedentes', racselConnectathonUri, "Local Antecedentes to RACSEL")
        local_diagnosticos_to_racsel_map_json = create_concept_map(diagnosticos_local_to_racsel, local_uri + '/diagnosticos', racselConnectathonUri, "Local Diagnosticos to RACSEL")
        local_vacunas_to_racsel_map_json = create_concept_map(vacunas_local_to_racsel, local_uri + '/vacunas', racselConnectathonUri, "Local Vacunas to RACSEL")
        local_alergias_to_racsel_map_json = create_concept_map(alergias_local_to_racsel, local_uri + '/alergias', racselConnectathonUri, "Local Alergias to RACSEL")
        local_medicacion_to_racsel_map_json = create_concept_map(medicacion_local_to_racsel, local_uri + '/medicacion', racselConnectathonUri, "Local Medicacion to RACSEL")
        local_procedimientos_to_racsel_map_json = create_concept_map(procedimientos_local_to_racsel, local_uri + '/procedimientos', racselConnectathonUri, "Local Procedimientos to RACSEL")

        local_antecedentes_to_snomed_map_json = create_concept_map(antecedentes_local_to_snomed, local_uri + '/antecedentes', snomed_uri, "Local Antecedentes to SNOMED")
        local_diagnosticos_to_snomed_map_json = create_concept_map(diagnosticos_local_to_snomed, local_uri + '/diagnosticos', snomed_uri, "Local Diagnosticos to SNOMED")
        local_vacunas_to_snomed_map_json = create_concept_map(vacunas_local_to_snomed, local_uri + '/vacunas', snomed_uri, "Local Vacunas to SNOMED")
        local_alergias_to_snomed_map_json = create_concept_map(alergias_local_to_snomed, local_uri + '/alergias', snomed_uri, "Local Alergias to SNOMED")
        local_medicacion_to_snomed_map_json = create_concept_map(medicacion_local_to_snomed, local_uri + '/medicacion', snomed_uri, "Local Medicacion to SNOMED")
        local_procedimientos_to_snomed_map_json = create_concept_map(procedimientos_local_to_snomed, local_uri + '/procedimientos', snomed_uri, "Local Procedimientos to SNOMED")

        local_antecedentes_to_cie10_map_json = create_concept_map(antecedentes_local_to_cie10, local_uri + '/antecedentes', cie10_uri, "Local Antecedentes to CIE10")
        local_diagnosticos_to_cie10_map_json = create_concept_map(diagnosticos_local_to_cie10, local_uri + '/diagnosticos', cie10_uri, "Local Diagnosticos to CIE10")

        local_to_cie11_map_json = create_concept_map(local_to_cie11, local_uri + '/vacunas', cie11_uri, "Local to CIE11")

        racsel_to_local_antecedentes_map_json = create_concept_map(antecedentes_racsel_to_local, racselConnectathonUri, local_uri  + '/antecedentes', "RACSEL to Local Antecedentes")
        racsel_to_local_diagnosticos_map_json = create_concept_map(diagnosticos_racsel_to_local, racselConnectathonUri, local_uri + '/diagnosticos', "RACSEL to Local Diagnosticos")
        racsel_to_local_vacunas_map_json = create_concept_map(vacunas_racsel_to_local, racselConnectathonUri, local_uri + '/vacunas', "RACSEL to Local Vacunas")
        racsel_to_local_alergias_map_json = create_concept_map(alergias_racsel_to_local, racselConnectathonUri, local_uri + '/alergias', "RACSEL to Local Alergias")
        racsel_to_local_medicacion_map_json = create_concept_map(medicacion_racsel_to_local, racselConnectathonUri, local_uri + '/medicacion', "RACSEL to Local Medicacion")
        racsel_to_local_procedimientos_map_json = create_concept_map(procedimientos_racsel_to_local, racselConnectathonUri, local_uri + '/procedimientos', "RACSEL to Local Procedimientos")
        
        cie10_to_local_antecedentes_map_json = create_concept_map(antecedentes_cie10_to_local, cie10_uri, local_uri + '/antecedentes', "CIE10 to Local Antecedentes")
        cie10_to_local_diagnosticos_map_json = create_concept_map(diagnosticos_cie10_to_local, cie10_uri, local_uri + '/diagnosticos', "CIE10 to Local Diagnosticos")

        cie11_to_local_map_json = create_concept_map(cie11_to_local, cie11_uri, local_uri + '/vacunas', "CIE11 to Local")
        
        snomed_to_local_antecedentes_map_json = create_concept_map(antecedentes_snomed_to_local, snomed_uri, local_uri + '/antecedentes', "SNOMED to Local Antecedentes")
        snomed_to_local_diagnosticos_map_json = create_concept_map(diagnosticos_snomed_to_local, snomed_uri, local_uri + '/diagnosticos', "SNOMED to Local Diagnosticos")
        snomed_to_local_vacunas_map_json = create_concept_map(vacunas_snomed_to_local, snomed_uri, local_uri + '/vacunas', "SNOMED to Local Vacunas")
        snomed_to_local_alergias_map_json = create_concept_map(alergias_snomed_to_local, snomed_uri, local_uri + '/alergias', "SNOMED to Local Alergias")
        snomed_to_local_medicacion_map_json = create_concept_map(medicacion_snomed_to_local, snomed_uri, local_uri + '/medicacion', "SNOMED to Local Medicacion")
        snomed_to_local_procedimientos_map_json = create_concept_map(procedimientos_snomed_to_local, snomed_uri, local_uri + '/procedimientos', "SNOMED to Local Procedimientos")
    
    cie10_to_snomed_map_json = create_concept_map(cie10_to_snomed, cie10_uri, snomed_uri, "CIE10 to SNOMED")
    cie11_to_snomed_map_json = create_concept_map(cie11_to_snomed, cie11_uri, snomed_uri, "CIE11 to SNOMED")
    snomed_to_cie10_map_json = create_concept_map(snomed_to_cie10, snomed_uri, cie10_uri, "SNOMED to CIE10")
    snomed_to_cie11_map_json = create_concept_map(snomed_to_cie11, snomed_uri, cie11_uri, "SNOMED to CIE11")


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
        (cie10_to_snomed_map_json, "package/ConceptMap/CIE10-to-SNOMED.json"),
        (cie11_to_snomed_map_json, "package/ConceptMap/CIE11-to-SNOMED.json"),
        (snomed_to_cie10_map_json, "package/ConceptMap/SNOMED-to-CIE10.json"),
        (snomed_to_cie11_map_json, "package/ConceptMap/SNOMED-to-CIE11.json")
    ]
    
    if (splitcs):
        # Adding split local code systems
        resources.extend([
            (code_system_local_json_antecedentes, "package/CodeSystem/LocalAntecedentesCodeSystem.json"),
            (code_system_local_json_diagnosticos, "package/CodeSystem/LocalDiagnosticosCodeSystem.json"),
            (code_system_local_json_vacunas, "package/CodeSystem/LocalVacunasCodeSystem.json"),
            (code_system_local_json_alergias, "package/CodeSystem/LocalAlergiasCodeSystem.json"),
            (code_system_local_json_medicacion, "package/CodeSystem/LocalMedicacionCodeSystem.json"),
            (code_system_local_json_procedimientos, "package/CodeSystem/LocalProcedimientosCodeSystem.json")
        ])

        # Adding split local maps
        resources.extend([
            (local_antecedentes_to_racsel_map_json, "package/ConceptMap/Local-Antecedentes-to-RACSEL.json"),
            (local_diagnosticos_to_racsel_map_json, "package/ConceptMap/Local-Diagnosticos-to-RACSEL.json"),
            (local_vacunas_to_racsel_map_json, "package/ConceptMap/Local-Vacunas-to-RACSEL.json"),
            (local_alergias_to_racsel_map_json, "package/ConceptMap/Local-Alergias-to-RACSEL.json"),
            (local_medicacion_to_racsel_map_json, "package/ConceptMap/Local-Medicacion-to-RACSEL.json"),
            (local_procedimientos_to_racsel_map_json, "package/ConceptMap/Local-Procedimientos-to-RACSEL.json"),
            (local_antecedentes_to_snomed_map_json, "package/ConceptMap/Local-Antecedentes-to-SNOMED.json"),
            (local_diagnosticos_to_snomed_map_json, "package/ConceptMap/Local-Diagnosticos-to-SNOMED.json"),
            (local_vacunas_to_snomed_map_json, "package/ConceptMap/Local-Vacunas-to-SNOMED.json"),
            (local_alergias_to_snomed_map_json, "package/ConceptMap/Local-Alergias-to-SNOMED.json"),
            (local_medicacion_to_snomed_map_json, "package/ConceptMap/Local-Medicacion-to-SNOMED.json"),
            (local_procedimientos_to_snomed_map_json, "package/ConceptMap/Local-Procedimientos-to-SNOMED.json"),
            (local_antecedentes_to_cie10_map_json, "package/ConceptMap/Local-Antecedentes-to-CIE10.json"),
            (local_diagnosticos_to_cie10_map_json, "package/ConceptMap/Local-Diagnosticos-to-CIE10.json"),
            (local_to_cie11_map_json, "package/ConceptMap/Local-to-CIE11.json"),
            (racsel_to_local_antecedentes_map_json, "package/ConceptMap/RACSEL-to-Local-Antecedentes.json"),
            (racsel_to_local_diagnosticos_map_json, "package/ConceptMap/RACSEL-to-Local-Diagnosticos.json"),
            (racsel_to_local_vacunas_map_json, "package/ConceptMap/RACSEL-to-Local-Vacunas.json"),
            (racsel_to_local_alergias_map_json, "package/ConceptMap/RACSEL-to-Local-Alergias.json"),
            (racsel_to_local_medicacion_map_json, "package/ConceptMap/RACSEL-to-Local-Medicacion.json"),
            (racsel_to_local_procedimientos_map_json, "package/ConceptMap/RACSEL-to-Local-Procedimientos.json"),
            (cie10_to_local_antecedentes_map_json, "package/ConceptMap/CIE10-to-Local-Antecedentes.json"),
            (cie10_to_local_diagnosticos_map_json, "package/ConceptMap/CIE10-to-Local-Diagnosticos.json"),
            (cie11_to_local_map_json, "package/ConceptMap/CIE11-to-Local.json"),
            (snomed_to_local_antecedentes_map_json, "package/ConceptMap/SNOMED-to-Local-Antecedentes.json"),
            (snomed_to_local_diagnosticos_map_json, "package/ConceptMap/SNOMED-to-Local-Diagnosticos.json"),
            (snomed_to_local_vacunas_map_json, "package/ConceptMap/SNOMED-to-Local-Vacunas.json"),
            (snomed_to_local_alergias_map_json, "package/ConceptMap/SNOMED-to-Local-Alergias.json"),
            (snomed_to_local_medicacion_map_json, "package/ConceptMap/SNOMED-to-Local-Medicacion.json"),
            (snomed_to_local_procedimientos_map_json, "package/ConceptMap/SNOMED-to-Local-Procedimientos.json")
        ])

    else:
        # Adding local code system
        resources.append((code_system_local_json, "package/CodeSystem/LocalCodeSystem.json"))

        # Adding local to racsel maps
        resources.extend([
            (local_to_racsel_map_json, "package/ConceptMap/Local-to-RACSEL.json"),
            (local_to_snomed_map_json, "package/ConceptMap/Local-to-SNOMED.json"),
            (local_to_cie10_map_json, "package/ConceptMap/Local-to-CIE10.json"),
            (local_to_cie11_map_json, "package/ConceptMap/Local-to-CIE11.json"),
            (racsel_to_local_map_json, "package/ConceptMap/RACSEL-to-Local.json"),
            (cie10_to_local_map_json, "package/ConceptMap/CIE10-to-Local.json"),
            (cie11_to_local_map_json, "package/ConceptMap/CIE11-to-Local.json"),
            (snomed_to_local_map_json, "package/ConceptMap/SNOMED-to-Local.json")
        ])

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




