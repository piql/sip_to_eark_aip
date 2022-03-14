from datetime import datetime
import hashlib
import logging
import mimetypes
import sys
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET


def validate_directories(dir: Path):
    if dir.exists():
        if dir.is_dir():
            # We want to make sure we are not in the SIP root
            if (dir / 'submission').is_dir() or (dir / 'schemas').is_dir():
                logging.error('Directory appears as root. Require representation directory')
            return True
        else:
            logging.error("Error: Input is not a directory")
    else:
        logging.error("Error: Input directory doesn't exist")
    return False

def get_namespaces(mets_file):
    # register namespaces to ET parser
    namespaces = {value[0]: value[1] for key, value in ET.iterparse(mets_file, events=['start-ns'])}
    for key in namespaces:
        ET.register_namespace(key, namespaces[key])
    return namespaces


def new_uuid():
    return 'uuid-' + str(uuid.uuid4())
    
def new_id():
    return 'ID-' + str(uuid.uuid4())

def get_checksum(file):
    sha256_hash = hashlib.sha256()
    with open(file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

def update_rep_mets(directory):
    expected_mets_path = directory / "METS.xml"
    if expected_mets_path.exists() and expected_mets_path.is_file():
        namespaces = get_namespaces(expected_mets_path)
        tree = ET.parse(expected_mets_path)
        root = tree.getroot()
        created_now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f%z")

        header_element = root.find('{%s}metsHdr' % namespaces[''])
        header_element.attrib['LASTMODDATE'] = created_now

        filesec_element = root.find('{%s}fileSec' % namespaces[''])
        filegrp_elements = filesec_element.findall('{%s}fileGrp' % namespaces[''])

        if len(filegrp_elements) != 1:
            logging.error("Error: Explicitly one filegrp element expected")
            sys.exit(2)
        file_elements = filegrp_elements[0].findall('{%s}file' % namespaces[''])
        if len(file_elements) != 1:
            logging.error("Error: Explicitly one file element expected")
            sys.exit(2)

        if not (directory / 'data').is_dir():
            logging.error("Error: data directory not found.")
            sys.exit(2)

        files_in_data = [Path(f) for f in (directory / 'data').iterdir()]

        if len(files_in_data) > 2:
            logging.error("Error: Too many files found in data dir")
            sys.exit(2)

        text_file = ''
        zip_file = ''
        for f in files_in_data:
            if f.suffix == ".txt" and text_file == '':
                text_file = f
            elif f.suffix == ".zip" and zip_file == '':
                zip_file = f
            else:
                logging.error("Error: Unexpected file in data dir")
                sys.exit(2)
        
        if zip_file == '':
            logging.error("Error: No zip found")
            sys.exit(2)
        
        new_file = ET.Element('{%s}file' % namespaces[''],
                            attrib={'ID': new_id(), 'MIMETYPE': str(mimetypes.guess_type(str(zip_file))[0]),
                                    'SIZE': str(zip_file.stat().st_size), 'CREATED': created_now,
                                    'CHECKSUM': get_checksum(zip_file), 'CHECKSUMTYPE': 'SHA-256'})
        new_flocat = ET.Element('{%s}FLocat' % namespaces[''],
                                attrib={'{%s}type' % namespaces['xlink']: 'simple',
                                        '{%s}href' % namespaces['xlink']: 'data/' + zip_file.name,
                                        'LOCTYPE': 'URL'})
        new_file.append(new_flocat)
        filegrp_elements[0].remove(file_elements[0])
        filegrp_elements[0].append(new_file)
        
        ET.indent(tree, space='    ', level=0)
        tree.write(directory / 'METS.xml', encoding='utf-8', xml_declaration=True)
        logging.info("METS written in: " + str(directory))

        if text_file != '':
            text_file.unlink()
        
    else:
        logging.error("Error: METS.xml not found in directory: " + expected_mets_path)
        sys.exit(2)

def update_root_mets(directory):
    expected_mets_path = directory / "METS.xml"
    if expected_mets_path.exists() and expected_mets_path.is_file():
        namespaces = get_namespaces(expected_mets_path)
        tree = ET.parse(expected_mets_path)
        root = tree.getroot()
        fileSec_element = root.find('{%s}fileSec' % namespaces[''])
        for fileGrp_element in fileSec_element.findall('{%s}fileGrp' % namespaces['']):
            fileGrp_use = fileGrp_element.get('USE')
            if fileGrp_use.lower().startswith('representations'):
                use_parts = fileGrp_use.split('/')
                if len(use_parts) == 1:
                    pass
                elif len(use_parts) == 2:
                    file_element = fileGrp_element.find('{%s}file' % namespaces[''])
                    flocat_element = file_element.find('{%s}FLocat' % namespaces[''])
                    href = flocat_element.get('{%s}href' % namespaces['xlink'])
                    file_path = directory / href
                    file_element.set('SIZE', str(file_path.stat().st_size))
                    file_element.set('CREATED', datetime.fromtimestamp(file_path.stat().st_ctime).strftime("%Y-%m-%dT%H:%M:%S%z"))
                    file_element.set('CHECKSUM', get_checksum(file_path))
                    file_element.set('CHECKSUMTYPE', 'SHA-256')
            elif fileGrp_use.lower() == 'submission':
                fileGrp_element.set('USE', str(Path(fileGrp_element.find('{%s}file' % namespaces['']).find('{%s}FLocat' % namespaces['']).get('{%s}href' % namespaces['xlink'])).parent))

        ET.indent(tree, space='    ', level=0)
        tree.write(directory / 'METS.xml', encoding='utf-8', xml_declaration=True)
        logging.info("METS written in: " + str(directory))


if __name__ == '__main__':
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.DEBUG, filemode='a', filename='logs/update_rep_mets.log', format='%(asctime)s %(levelname)s: %(message)s')
    if len(sys.argv) == 2:
        rep_dir = Path(sys.argv[1])
        if validate_directories(rep_dir):
            logging.info('Updating rep mets: ' + str(rep_dir))
            update_rep_mets(rep_dir)
            logging.info('Updating root mets: ' + str(rep_dir.parents[1]))
            update_root_mets(rep_dir.parents[1])
        else:
            logging.error('Directory Invalid: ' + str(rep_dir))
            sys.exit(1)
    else:
        logging.error("Incorrect script call format")
        print("Error: Command should have the form:")
        print("python main.py <Directory>")
        sys.exit(1)
