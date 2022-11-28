from datetime import datetime
from pathlib import Path
import hashlib
import logging
import mimetypes
import shutil
import xml.etree.ElementTree as ET
import sys
import uuid


SOFTWARE_NAME = "E-ARK AIP Creator"
SOFTWARE_VERSION = "v0.2.0-dev"


def date_time_now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def update_root_mets(aip_path:Path):
    update_mets((aip_path / 'METS.xml'))


def get_checksum(file:Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def extract_namespaces(mets_path:Path) -> dict:
    # Extract namespaces from mets files
    # Store and register namespaces
    namespaces = {}
    for _, values, in ET.iterparse(mets_path, events=['start-ns']):
        key, value = str(values[0]), str(values[1])
        if key == 'mets':
            key = ''
        elif key == 'sip':
            key = 'aip'
            value = value.replace('SIP', 'AIP')
        namespaces[key] = value
        ET.register_namespace(key, value)
    return namespaces


def update_mets(mets_path:Path):

    id_updates = {}
    
    # Extract namespaces
    namespaces = extract_namespaces(mets_path)

    # Parse mets
    tree = ET.parse(mets_path)

    # Mets Element
    mets_element = tree.getroot()
    mets_element.set('OBJID', str(mets_path.parent.stem))

    # Update SIP schema location to AIP
    if "https://dilcis.eu/XML/METS/SIPExtensionMETS" in mets_element.get('{%s}schemaLocation' % namespaces['xsi']):
        mets_element.set('{%s}schemaLocation' % namespaces['xsi'], mets_element.get('{%s}schemaLocation' % namespaces['xsi']).replace("https://dilcis.eu/XML/METS/SIPExtensionMETS", "https://dilcis.eu/XML/METS/AIPExtensionMETS"))

    # Mets Header
    metsHdr_element = mets_element.find('{%s}metsHdr' % namespaces[''])
    # metsHdr_element.set('CREATEDATE', date_time_now())
    metsHdr_element.set('LASTMODDATE', date_time_now())
    metsHdr_element.set('RECORDSTATUS', "Revised")
    metsHdr_element.set('{%s}OAISPACKAGETYPE' % namespaces['csip'], "AIP")

    # Mets Header - MetsDocumentID
    # Remove
    metsDocumentId_element = metsHdr_element.find('{%s}metsDocumentID' % namespaces[''])
    if metsDocumentId_element is not None:
        metsHdr_element.remove(metsDocumentId_element)

    # Mets Header - Agent
    # Remove Software Agent and Individuals
    marked_for_remove = []
    for agent_element in metsHdr_element.findall('{%s}agent' % namespaces['']):
        agent_attribs = agent_element.attrib
        try:
            if agent_attribs['ROLE'] == 'CREATOR' and agent_attribs['TYPE'] == 'OTHER' and agent_attribs['OTHERTYPE'] == 'SOFTWARE':
                marked_for_remove.append(agent_element)
            elif agent_attribs['ROLE'] == 'CREATOR' and agent_attribs['TYPE'] == 'INDIVIDUAL':
                marked_for_remove.append(agent_element)
        except KeyError:
            pass
    for agent in marked_for_remove:
        metsHdr_element.remove(agent)

    # Add Software Agent
    new_agent = ET.SubElement(metsHdr_element, '{%s}agent' % namespaces[''], attrib={'ROLE': 'CREATOR', 'TYPE': 'OTHER', 'OTHERTYPE': 'SOFTWARE'})
    ET.SubElement(new_agent, '{%s}name' % namespaces['']).text = SOFTWARE_NAME
    ET.SubElement(new_agent, '{%s}note' % namespaces[''], attrib={'{%s}NOTETYPE' % namespaces['csip']: 'SOFTWARE VERSION'}).text = SOFTWARE_VERSION

    # Mets Header - DMD Section
    # Update and Store ID
    for dmdSec in mets_element.findall('{%s}dmdSec' % namespaces['']):
        id_updates[dmdSec.get('ID')] = new_uuid()
        dmdSec.set('ID', id_updates[dmdSec.get('ID')])
        dmdSec.set('CREATED', date_time_now())

    # Mets Header - AMD Section
    # Update and Store ID
    for amdSec in mets_element.findall('{%s}amdSec' % namespaces['']):
        id_updates[amdSec.get('ID')] = new_uuid()
        amdSec.set('ID', id_updates[amdSec.get('ID')])

    # File Section
    # Update ID - Don't Store
    fileSec_element = mets_element.find('{%s}fileSec' % namespaces[''])
    fileSec_element.set('ID', new_uuid())

    # File Section - File Groups
    # Remove Representation File Groups - (root mets)
    # Update and Store ID
    marked_for_remove = []
    for fileGrp_element in fileSec_element.findall('{%s}fileGrp' % namespaces['']):
        if fileGrp_element.get('USE').lower().startswith('representation'):
            marked_for_remove.append(fileGrp_element)
            continue
        else:
            id_updates[fileGrp_element.get('ID')] = new_uuid()
            fileGrp_element.set('ID', id_updates[fileGrp_element.get('ID')])
            # File Section - File Group - File
            # Update and Store ID
            for file_element in fileGrp_element.findall('{%s}file' % namespaces['']):
                id_updates[file_element.get('ID')] = new_uuid('ID')
                file_element.set('ID', id_updates[file_element.get('ID')])
    for fileGrp in marked_for_remove:
        fileSec_element.remove(fileGrp)

    # Struct Map
    # Update ID - Don't store
    structmap_element = mets_element.find('{%s}structMap' % namespaces[''])
    structmap_element.set('ID', new_uuid())

    # Struct Map - Div
    root_div_element = structmap_element.find('{%s}div' % namespaces[''])
    root_div_element.set('LABEL', mets_path.parent.stem)
    root_div_element.set('ID', new_uuid())

    # Struct Map - Div - Div
    # Remove representations - (root mets)
    # Update metadata DMDID
    # Update IDs
    marked_for_remove = []
    for div_element in root_div_element.findall('{%s}div' % namespaces['']):
        if div_element.get('LABEL').lower().startswith('representations'):
            marked_for_remove.append(div_element)
            continue
        if div_element.get('LABEL').lower().startswith('metadata'):
            if div_element.get('DMDID') in id_updates:
                div_element.set('DMDID', id_updates[div_element.get('DMDID')])
        div_element.set('ID', new_uuid())

        # Struct Map - Div - Div - FPTR
        # Update ID to fileGrp ID
        """
        fptr_element = div_element.find('{%s}fptr' % namespaces[''])
        if fptr_element is not None:
            if fptr_element.get('FILEID') in id_updates:
                fptr_element.set('FILEID', id_updates[fptr_element.get('FILEID')])
            else:
                fptr_element.set('FILEID', new_uuid())
        """
        for fptr_element in div_element.findall('{%s}fptr' % namespaces['']):
            if fptr_element.get('FILEID') in id_updates:
                fptr_element.set('FILEID', id_updates[fptr_element.get('FILEID')])
            else:
                fptr_element.set('FILEID', new_uuid())

        # Struct Map - Div - Div - MPTR
        # Update ID to file ID
        """
        mptr_element = div_element.find('{%s}mptr' % namespaces[''])
        if mptr_element is not None:
            if mptr_element.get('FILEID') in id_updates:
                mptr_element.set('FILEID', id_updates[mptr_element.get('FILEID')])
            else:
                fptr_element.set('FILEID', new_uuid())
        """
        for mptr_element in div_element.findall('{%s}mptr' % namespaces['']):
            if mptr_element.get('FILEID') in id_updates:
                mptr_element.set('FILEID', id_updates[mptr_element.get('FILEID')])
            else:
                mptr_element.set('FILEID', new_uuid())

    for div in marked_for_remove:
        root_div_element.remove(div)

    # Add File Groups and Struct Map Divs for new representations - (root mets only)
    representations_path = (mets_path.parent / 'representations')
    if representations_path.is_dir():
        for rep_path in representations_path.iterdir():
            rep_mets_path = (rep_path / 'METS.xml')
            if rep_path.stem.endswith('-preservation'):
                continue
            # File Group
            new_fileGrp_id = new_uuid()
            new_fileGrp_element = ET.SubElement(fileSec_element, '{%s}fileGrp' % namespaces[''], attrib={
                'ID': new_fileGrp_id,
                'USE': str(rep_path.relative_to(mets_path.parent))
            })
            new_file_id = new_uuid('ID')
            new_file_mimetype = str(mimetypes.guess_type(rep_mets_path)[0])
            # Fix potential depreciated mimetype
            if new_file_mimetype == "application/x-zip-compressed": 
                new_file_mimetype = "application/zip"
            new_file_element = ET.SubElement(new_fileGrp_element, '{%s}file' % namespaces[''], attrib={
                'ID': new_file_id,
                'MIMETYPE': new_file_mimetype,
                'SIZE': str(rep_mets_path.stat().st_size),
                'CREATED': date_time_now(),
                'CHECKSUM': get_checksum(rep_mets_path),
                'CHECKSUMTYPE': 'SHA-256'
            })
            ET.SubElement(new_file_element, '{%s}FLocat' % namespaces[''], attrib={
                '{%s}type' % namespaces['xlink']: 'simple',
                '{%s}href' % namespaces['xlink']: str(rep_mets_path.relative_to(mets_path.parent)),
                '{%s}LOCTYPE' % namespaces['']: 'URL',
            })
            # Struct Map
            new_div = ET.SubElement(root_div_element, '{%s}div' % namespaces[''], attrib={
                'ID': new_uuid(),
                'LABEL': str(rep_path.relative_to(rep_path.parents[1]))
            })
            ET.SubElement(new_div, '{%s}mptr' % namespaces[''], attrib={
                '{%s}type' % namespaces['xlink']: 'simple',
                '{%s}href' % namespaces['xlink']: str(rep_mets_path.relative_to(rep_path)),
                '{%s}title' % namespaces['xlink']: new_fileGrp_id,
                '{%s}LOCTYPE' % namespaces['']: 'URL',
            })

    ET.indent(tree, space='    ', level=0)
    tree.write(mets_path, encoding='utf-8', xml_declaration=True)


def update_rep_mets(aip_path:Path):
    # Update each non-preservation METS.xml
    for rep_path in (aip_path / 'representations').iterdir():
        # Ignore preservation reps
        if rep_path.stem.endswith('-preservation'):
            continue
        rep_mets_path = (rep_path / 'METS.xml')
        update_mets(rep_mets_path)
    pass


def transform_representations(aip_path:Path):
    # For each directory in representation, rename it rep0x and create rep0x-preservation
    rep_couter = 0
    for rep_path in (aip_path / "representations").iterdir():
        if rep_path.is_dir():
            rep_couter += 1
            # Rename rep name with zero padded counter
            new_rep_name = 'rep'+str(rep_couter).zfill(2)
            new_rep_path = (rep_path.parent / new_rep_name)
            rep_path.rename(new_rep_path)

            # Create preservation rep incl. data directory
            new_rep_preservation_name = new_rep_name + "-preservation"
            new_rep_preservation_path = (rep_path.parent / new_rep_preservation_name / "data")
            new_rep_preservation_path.mkdir(parents=True, exist_ok=False)


def copy_sip_to_aip(sip_path:Path, aip_path:Path):
    # Copy all directories and files from sip to aip
    for file_folder in sip_path.iterdir():
        if file_folder.is_dir():
            shutil.copytree(file_folder, (aip_path / file_folder.stem), copy_function=shutil.copy2)
        else:
            shutil.copy2(file_folder, (aip_path / file_folder.name))


def overwrite_and_create_directory(directory:Path):
    # Delete directory if it exists and (re)create it
    if directory.is_dir():
        logging.info("Overwriting '%s'" % directory)
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)


def update_metadata(aip_path:Path, sip_name:str):
    # Update referencese to SIP name with new AIP name
    # TODO Update different types of metadata

    # Descriptive DC.xml
    dc_metadata_path = (aip_path / 'metadata' / 'descriptive' / 'DC.xml')
    if dc_metadata_path.is_file():
        dc_tree = ET.parse(dc_metadata_path)
        dc_root = dc_tree.getroot()
        for child in dc_root:
            if sip_name in str(child.text):
                child.text = child.text.replace(sip_name, aip_path.stem)
    
        dc_tree.write(dc_metadata_path, encoding='utf-8', xml_declaration=True)


def new_uuid(prefix:str="uuid") -> str:
    return prefix + "-" + str(uuid.uuid4())


def transform_sip_to_aip(sip_path:Path, output_path:Path) -> str:

    sip_name = sip_path.stem
    aip_name = new_uuid()

    # For Testing
    # aip_name = sip_name

    aip_path = (output_path / aip_name)

    # Update metadata to reflect new directory name
    update_metadata(aip_path, sip_name)

    # (Re-)create output directory
    overwrite_and_create_directory(aip_path)
    
    # Copy SIP contents to AIP directory
    copy_sip_to_aip(sip_path, aip_path)

    # Transform the AIP representations directory to AIP specification
    transform_representations(aip_path)

    update_rep_mets(aip_path)

    update_root_mets(aip_path)

    return aip_name


def fatal_error(error:str):
    logging.error(error)
    # TODO Revert changes?
    sys.exit('Fatal Error: '+ error)


def validate_input_directories(sip_path:Path, output_path:Path) -> tuple[Path, Path]:

    # SIP must exists
    if not sip_path.exists():
        fatal_error(str(sip_path) + " not found")

    # SIP must be a directory
    if not sip_path.is_dir():
        fatal_error(str(sip_path) + " is not a directory")
    
    # SIP must contain representations directory
    representations_path = (sip_path / 'representations')
    if not representations_path.is_dir():
        fatal_error("SIP doesn't contain representations directory")

    # SIP representations directory must contatin rep directories
    rep_paths = representations_path.iterdir()
    if not rep_paths:
        fatal_error("No rep directories found in representations")
        
    # SIP reps must contain METS.xml files
    for rep_path in rep_paths:
        mets_path = (rep_path / 'METS.xml')
        if not mets_path.is_file():
            fatal_error("One or more SIP representations don't contain METS.xml")

    # Ouput destination should be a directory if it exists
    if output_path.exists() and not output_path.is_dir():
        fatal_error("Output destination must be a directory")
    
    return sip_path, output_path

def main(argv) -> str:
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.DEBUG, filemode='a', filename='logs/sip_to_eark_aip.log', format='%(asctime)s %(levelname)s: %(funcName)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if len(argv) != 2:
        logging.error("Incorrect script call format")
        sys.exit("Command should have the form:\npython aip_to_eark_aip.py <SIP Directory> <Output Directory>")
    
    sip_path, output_path = validate_input_directories(Path(argv[0]), Path(argv[1]))

    aip_name = transform_sip_to_aip(sip_path, output_path)

    return aip_name


if __name__ == '__main__':
    print(main(sys.argv[1:]))