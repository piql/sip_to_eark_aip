from datetime import datetime
import hashlib
import mimetypes
import sys
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET

def get_arg(index):
    try:
        sys.argv[index]
    except IndexError:
        return None
    else:
        return sys.argv[index]


def validate_directories(dir):
    if dir.exists():
        if dir.is_dir():
            return True
        else:
            print("Error: Input is not a directory")
    else:
        print("Error: Input directory doesn't exist")
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
            print("Error: Explicitly one filegrp element expected")
            sys.exit(1)
        file_elements = filegrp_elements[0].findall('{%s}file' % namespaces[''])
        if len(file_elements) != 1:
            print("Error: Explicitly one file element expected")
            sys.exit(1)

        if not (directory / 'data').is_dir():
            print("Error: data directory not found.")
            sys.exit(1)

        files_in_data = [Path(f) for f in (directory / 'data').iterdir()]

        if len(files_in_data) > 2:
            print("Error: Too many files found in data dir")
            sys.exit(1)

        text_file = ''
        zip_file = ''
        for f in files_in_data:
            if f.suffix == ".txt" and text_file == '':
                text_file = f
            elif f.suffix == ".zip" and zip_file == '':
                zip_file = f
            else:
                print("Error: Unexpected file in data dir")
                sys.exit(1)
        
        if zip_file == '':
            print("Error: No zip found")
            sys.exit(1)
        
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
        print("METS written in:", directory)

        if text_file != '':
            text_file.unlink()
        
    else:
        print("Error: METS.xml not found in directory:", expected_mets_path)
        sys.exit(1)

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
        ET.indent(tree, space='    ', level=0)
        tree.write(directory / 'METS.xml', encoding='utf-8', xml_declaration=True)
        print("METS written in:", directory)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        rep_dir = Path(sys.argv[1])
        if validate_directories(rep_dir):
            update_rep_mets(rep_dir)
            update_root_mets(rep_dir.parents[1])
        else:
            sys.exit(1)
    else:
        print("Error: Command should have the form:")
        print("python main.py <Directory>")
        sys.exit(1)
