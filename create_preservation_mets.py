import mimetypes
import xml.etree.ElementTree as ET
import logging
import sys
from pathlib import Path

from sip_to_eark_aip import extract_namespaces, get_checksum, new_uuid, date_time_now


def update_root_mets(rep_path:Path):
    root_path = rep_path.parents[1]
    root_mets = (root_path / 'METS.xml')
<<<<<<< Updated upstream

    if not root_mets.exists() or not root_mets.is_file():
        fatal_error("Root METS.xml file not found")

=======
    if not root_mets.exists() or not root_mets.is_file():
        fatal_error("Root METS.xml file not found")
>>>>>>> Stashed changes
    namespaces = extract_namespaces(root_mets)
    tree = ET.parse(root_mets)
    mets_element = tree.getroot()

    # File Section
    fileSec_element = mets_element.find('{%s}fileSec' % namespaces[''])

    # Remove any file group with the same USE attribute - for re-running script
    marked_for_remove = []
    for fileGrp_element in fileSec_element.findall('{%s}fileGrp' % namespaces['']):
        if fileGrp_element.get('USE') == (rep_path.relative_to(root_path)):
            marked_for_remove.append(fileGrp_element)
    for fileGrp in marked_for_remove:
        fileSec_element.remove(fileGrp)

    rep_mets_path = (rep_path / 'METS.xml')

    # New File Group
    fileGrp_id = new_uuid()
    fileGrp_element = ET.SubElement(fileSec_element, '{%s}fileGrp' % namespaces[''], attrib={
        'ID': fileGrp_id,
        'USE': str(rep_path.relative_to(root_path))
    })
    file_id = new_uuid('ID')
    # Fix potential depreciated mimetype
<<<<<<< Updated upstream
=======
    file_mimetype = str(mimetypes.guess_type(rep_mets_path)[0])
>>>>>>> Stashed changes
    if file_mimetype == "application/x-zip-compressed": 
        file_mimetype = "application/zip"
    file_element = ET.SubElement(fileGrp_element, '{%s}file' % namespaces[''], attrib={
        'ID': file_id,
        'MIMETYPE': file_mimetype,
        'SIZE': str(rep_mets_path.stat().st_size),
        'CREATED': date_time_now(),
        'CHECKSUM': get_checksum(rep_mets_path),
        'CHECKSUMTYPE': 'SHA-256'
    })
    ET.SubElement(file_element, '{%s}FLocat' % namespaces[''], attrib={
        '{%s}type' % namespaces['xlink']: 'simple',
        '{%s}href' % namespaces['xlink']: str(rep_mets_path.relative_to(root_path)),
        '{%s}LOCTYPE' % namespaces['']: 'URL',
    })

    # Struct Map
    structmap_element = mets_element.find('{%s}structMap' % namespaces[''])
    structmap_element.set('ID', new_uuid())

    root_div_element = structmap_element.find('{%s}div' % namespaces[''])
    # New Div
    div_element = ET.SubElement(root_div_element, '{%s}div' % namespaces[''], attrib={
        'ID': new_uuid(),
        'LABEL': str(rep_path.relative_to(root_path))
    })
    ET.SubElement(div_element, '{%s}mptr' % namespaces[''], attrib={
        '{%s}type' % namespaces['xlink']: 'simple',
        '{%s}href' % namespaces['xlink']: str(rep_mets_path.relative_to(root_path)),
        '{%s}title' % namespaces['xlink']: fileGrp_id,
        '{%s}LOCTYPE' % namespaces['']: 'URL',
    })
<<<<<<< Updated upstream

=======
>>>>>>> Stashed changes
    ET.indent(tree, space='    ', level=0)
    tree.write(root_mets, encoding='utf-8', xml_declaration=True)

def create_preservation_mets(rep_path:Path):

    # Use non-preservation rep mets as a template
    np_rep_mets_path = (rep_path.parent / rep_path.stem.replace('-preservation', '') / 'METS.xml')
    
    preservation_file_path = [Path(f) for f in (rep_path / 'data').iterdir()][0]
    
    # Extract namespaces from non-preservation rep mets
    namespaces = extract_namespaces(np_rep_mets_path)

    # Parse mets
    tree = ET.parse(np_rep_mets_path) 

    # Mets Element
    mets_element = tree.getroot()
    mets_element.set('OBJID', str(rep_path.stem))

    # Mets Header
    metsHdr_element = mets_element.find('{%s}metsHdr' % namespaces[''])
    metsHdr_element.set('CREATEDATE', date_time_now())
    metsHdr_element.set('LASTMODDATE', date_time_now())
    metsHdr_element.set('RECORDSTATUS', 'NEW')

    # Remove all amdSecs
    for amdSec_element in mets_element.findall('{%s}amdSec' % namespaces['']):
        mets_element.remove(amdSec_element)
        
    # Remove all dmdSecs
    for dmdSec_element in mets_element.findall('{%s}dmdSec' % namespaces['']):
        mets_element.remove(dmdSec_element)

    # File Section - should only be one
    fileSec_element = mets_element.find('{%s}fileSec' % namespaces[''])
    fileSec_element.set('ID', new_uuid())

    # Remove all File Groups
    for fileGrp_element in fileSec_element.findall('{%s}fileGrp' % namespaces['']):
        fileSec_element.remove(fileGrp_element)

    # Create new FileGroup and File Elements
    fileGrp_element = ET.SubElement(fileSec_element, '{%s}fileGrp' % namespaces[''], attrib={
        'ID': new_uuid(),
        'USE': 'data'
    })
    file_id = new_uuid('ID')
    # Fix potential depreciated mimetype
    file_mimetype = str(mimetypes.guess_type(preservation_file_path)[0])
    if file_mimetype == "application/x-zip-compressed": 
        file_mimetype = "application/zip"
    file_element = ET.SubElement(fileGrp_element, '{%s}file' % namespaces[''], attrib={
        'ID': file_id,
        'MIMETYPE': file_mimetype,
        'SIZE': str(preservation_file_path.stat().st_size),
        'CREATED': date_time_now(),
        'CHECKSUM': get_checksum(preservation_file_path),
        'CHECKSUMTYPE': 'SHA-256'
    })
    ET.SubElement(file_element, '{%s}FLocat' % namespaces[''], attrib={
        '{%s}type' % namespaces['xlink']: 'simple',
        '{%s}href' % namespaces['xlink']: str(preservation_file_path.relative_to(rep_path)),
        '{%s}LOCTYPE' % namespaces['']: 'URL',
    })

    # Struct Map
    structmap_element = mets_element.find('{%s}structMap' % namespaces[''])
    structmap_element.set('ID', new_uuid())

    root_div_element = structmap_element.find('{%s}div' % namespaces[''])
    root_div_element.set('LABEL', rep_path.stem)
    root_div_element.set('ID', new_uuid())

    # Remove all sub divs
    for sub_div_element in root_div_element.findall('{%s}div' % namespaces['']):
        root_div_element.remove(sub_div_element)

    # Add data sub div
    sub_div_element = ET.SubElement(root_div_element, '{%s}div' % namespaces[''], attrib={
        'LABEL': 'data',
        'ID': new_uuid()
    })
    ET.SubElement(sub_div_element, '{%s}fptr' % namespaces[''], attrib={
        'FILEID': file_id
    })

    ET.indent(tree, space='    ', level=0)
    tree.write((rep_path / 'METS.xml'), encoding='utf-8', xml_declaration=True)


def fatal_error(error:str):
    logging.error(error)
    # TODO Revert changes?
    sys.exit('Fatal Error: '+ error)


def validate_input_directory(rep_path:Path):
    # Rep must exists
    if not rep_path.exists():
        fatal_error(str(rep_path) + " not found")

    # Rep must be a directory
    if not rep_path.is_dir():
        fatal_error(str(rep_path) + " is not a directory")
    
    # Rep must contain data directory
    data_path = (rep_path / 'data')
    if not data_path.is_dir():
        fatal_error("Rep doesn't contain data directory")

    # Ensure data directory contains a single file with .zip extension
    preservation_files = [Path(f) for f in data_path.iterdir()]
    if len(preservation_files) != 1:
        fatal_error('Preservation representaion data directory should contain a single zip file')
    if [Path(f) for f in (rep_path / 'data').iterdir()][0].suffix != '.zip':
        fatal_error('Preservation file should be a zip')
    
    return rep_path


def main(argv):
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.DEBUG, filemode='a', filename='logs/sip_to_eark_aip.log', format='%(asctime)s %(levelname)s: %(funcName)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

    if len(argv) != 1:
        logging.error("Incorrect script call format")
        sys.exit("Command should have the form:\npython create_preservation_mets.py <Rep Directory>")
    
    rep_path = validate_input_directory(Path(argv[0]))
<<<<<<< Updated upstream
    create_preservation_mets(rep_path)

=======
    logging.info(rep_path)
    create_preservation_mets(rep_path)
>>>>>>> Stashed changes
    update_root_mets(rep_path)


if __name__ == '__main__':
    main(sys.argv[1:])