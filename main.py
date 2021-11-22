import hashlib
import mimetypes
import os
import shutil
import sys
import uuid
import metsrw
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path


# logs_file_path = "./app.log"
# sys.stdout = open(logs_file_path, "w", buffering=1, encoding='utf-8')


def get_arg(index):
    try:
        sys.argv[index]
    except IndexError:
        return None
    else:
        return sys.argv[index]


def get_checksum(file):
    sha256_hash = hashlib.sha256()
    with open(file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


def validate_directories(sip_dir, output_dir):
    if sip_dir.exists():
        if sip_dir.is_dir():
            if output_dir.exists():
                if output_dir.is_dir():
                    sip_name = sip_dir.stem
                    try:
                        sip_uuid = str(sip_name[sip_name.index('uuid-') + len('uuid-'):])
                        uuid_obj = uuid.UUID(sip_uuid, version=4)
                    except ValueError:
                        print("Error: SIP doesn't contain valid uuid4")
                    else:
                        return True
                else:
                    print("Error: Output is not a directory")
            else:
                print("Error: Output directory doesn't exit")
        else:
            print("Error: Input is not a directory")
    else:
        print("Error: Input directory doesn't exit")
    return False


def overwrite_and_create_directory(directory):
    """
    Deletes directory if it exists and (re)creates directory
    :param Path directory: path that needs to be (re)created
    :return Boolean: if successful
    """
    if directory.is_dir():
        print("Overwriting '%s'" % directory)
        shutil.rmtree(directory)
    try:
        directory.mkdir(exist_ok=False)
    except FileExistsError as e:
        print(e)
        print('Error with AIP overwrite')


def validate_representations_sequence(representations_path):
    """
    Validate SIP representations naming and sequence structure
    :param Path representations_path: path to SIP representations folder to be vaildated
    :return Boolean: True if valid
    """
    expected_sequence_number = 1
    previous_folder_name = ''

    for rep in sorted(representations_path.iterdir()):
        rep = str(rep.stem)
        folder_name = rep.rstrip('0123456789')
        try:
            sequence_number = int(rep[len(folder_name):])
        except ValueError:
            print("ERROR in SIP representation. No sequence number.")
            return False

        if expected_sequence_number == 1:
            previous_folder_name = folder_name
        elif folder_name != previous_folder_name:
            print("ERROR in SIP representations naming sequence. Expected:", previous_folder_name, "Got:", folder_name)
            return False

        if expected_sequence_number == sequence_number:
            expected_sequence_number += 1
        else:
            print("ERROR in SIP rep number sequence. Expected:", expected_sequence_number, "Got:", sequence_number)
            return False
    return True


def new_uuid():
    return 'new-uuid-' + str(uuid.uuid4())


def update_all_mets_ids(mets_tree, id_updates, namespaces):
    """
    Updates all IDS in a mets file
    :param ElementTree mets_tree: tree for IDs to be updated on
    :param dict id_updates: contains tracked changes in ID's to maintain connections
    :param dict namespaces: contains namespaces ad their schema locations
    """
    root = mets_tree.getroot()
    try:
        if root.attrib['OBJID'] in id_updates:
            root.attrib['OBJID'] = id_updates[root.attrib['OBJID']]
        else:
            print("Warning: AIP uuid not updated")
    except ValueError:
        print("Warning: No OBJID in SIP METS.xml")

    dmdsec_elements = root.findall('{%s}dmdSec' % namespaces[''])
    for dmdsec in dmdsec_elements:
        new_id = new_uuid()
        id_updates[dmdsec.attrib['ID']] = new_id
        dmdsec.attrib['ID'] = new_id

    amdsec_elements = root.findall('{%s}amdSec' % namespaces[''])
    for amdsec in amdsec_elements:
        new_id = new_uuid()
        id_updates[amdsec.attrib['ID']] = new_id
        amdsec.attrib['ID'] = new_id

    filesec_element = root.find('{%s}fileSec' % namespaces[''])
    filesec_element.attrib['ID'] = new_uuid()
    for filegrp in filesec_element.findall('{%s}fileGrp' % namespaces['']):
        for sub_filegrp in filegrp.findall('{%s}fileGrp' % namespaces['']):
            sub_filegrp_id = new_uuid()
            id_updates[sub_filegrp.attrib['ID']] = sub_filegrp_id
            sub_filegrp.attrib['ID'] = sub_filegrp_id
            for file_element in sub_filegrp.findall('{%s}file' % namespaces['']):
                file_id = new_uuid()
                id_updates[file_element.attrib['ID']] = file_id
                file_element.attrib['ID'] = file_id
        else:
            filegrp_id = new_uuid()
            id_updates[filegrp.attrib['ID']] = filegrp_id
            filegrp.attrib['ID'] = filegrp_id
            for file_element in filegrp.findall('{%s}file' % namespaces['']):
                file_id = new_uuid()
                id_updates[file_element.attrib['ID']] = file_id
                file_element.attrib['ID'] = file_id

    structmap_element = root.find('{%s}structMap' % namespaces[''])
    structmap_element.attrib['ID'] = new_uuid()
    root_div_element = structmap_element.find('{%s}div' % namespaces[''])
    root_div_element.attrib['LABEL'] = root.attrib['OBJID']
    for div in root_div_element.findall('{%s}div' % namespaces['']):
        div.attrib['ID'] = new_uuid()
        if div.attrib['LABEL'].lower() == 'metadata':
            try:
                if div.attrib['DMDID'] in id_updates:
                    div.attrib['DMDID'] = id_updates[div.attrib['DMDID']]
                else:
                    div.attrib['DMDID'] = new_uuid()
            except KeyError:
                print("Warning: Expecting 'DMDID' in structmap metadata")

        for sub_div in div.findall('{%s}div' % namespaces['']):
            sub_div_id = new_uuid()
            # id_updates[sub_div.attrib['ID']] = sub_div_id
            sub_div.attrib['ID'] = sub_div_id
            for item in sub_div:
                if str(item.tag) == '{%s}fptr' % namespaces['']:
                    if item.attrib['FILEID'] in id_updates:
                        item.attrib['FILEID'] = id_updates[item.attrib['FILEID']]
                elif str(item.tag) == '{%s}mptr' % namespaces['']:
                    try:
                        if item.attrib['{%s}title' % namespaces['xlink']] in id_updates:
                            item.attrib['{%s}title' % namespaces['xlink']] = id_updates[
                                item.attrib['{%s}title' % namespaces['xlink']]]
                    except KeyError:
                        pass
                else:
                    print('Warning: Got unsupported pointer:', item.attrib['LABEL'], item.tag, "while updating mets ID")
        else:
            for item in div:
                if str(item.tag) == '{%s}fptr' % namespaces['']:
                    if item.attrib['FILEID'] in id_updates:
                        item.attrib['FILEID'] = id_updates[item.attrib['FILEID']]
                elif str(item.tag) == '{%s}mptr' % namespaces['']:
                    try:
                        if item.attrib['{%s}title' % namespaces['xlink']] in id_updates:
                            item.attrib['{%s}title' % namespaces['xlink']] = id_updates[
                                item.attrib['{%s}title' % namespaces['xlink']]]
                    except KeyError:
                        pass
                else:
                    print('Warning: Got unsupported pointer:', item.attrib['LABEL'], item.tag, "while updating mets ID")


def create_root_aip_mets(sip_mets, aip_root, id_updates):
    """
    The structure of the SIP and AIP are similar so it is possible to alter the SIP METS.xml to
    This method maintains namespaces with the original SIP mets and uses it as a template. The necessary adjustments are
    made to make it a conformant EARK AIP mets file.
    :param Path sip_mets: Path to SIP METS to use as template
    :param Path aip_root: Path to AIP root where METS will be written
    :param dict id_updates: Tracks ID changed to ensure connections remain
    :return:
    """
    # register namespaces to ET parser
    namespaces = {}
    for key, value in ET.iterparse(sip_mets, events=['start-ns']):
        ET.register_namespace(value[0], value[1])
        namespaces[value[0]] = value[1]

    tree = ET.parse(sip_mets)
    root = tree.getroot()
    created_now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f%z")

    # METS HEADER
    metshdr_elemet = root.find('{%s}metsHdr' % namespaces[''])
    metshdr_elemet.attrib['LASTMODDATE'] = created_now
    metshdr_elemet.attrib['RECORDSTATUS'] = 'Revised'
    try:
        metshdr_elemet.attrib['{%s}OAISPACKAGETYPE' % namespaces['csip']] = 'AIP'
    except KeyError:
        print("Warning: metsHdr doesn't containt OAISPACKAGETYPE")

    # FILE SECTION
    filesec_element = root.find('{%s}fileSec' % namespaces[''])

    new_filegrp = ET.Element('{%s}fileGrp' % namespaces[''])
    new_filegrp.attrib['ID'] = new_uuid()
    new_filegrp.attrib['USE'] = 'submission'

    new_file = ET.Element('{%s}file' % namespaces[''])
    new_file.attrib['ID'] = new_uuid()
    new_file.attrib['MIMETYPE'] = str(mimetypes.guess_type(sip_mets)[0])
    new_file.attrib['SIZE'] = str(sip_mets.stat().st_size)
    new_file.attrib['CREATED'] = created_now
    new_file.attrib['CHECKSUM'] = get_checksum(sip_mets)
    new_file.attrib['CHECKSUMTYPE'] = 'SHA-256'

    new_flocat = ET.Element('{%s}FLocat' % namespaces[''])
    new_flocat.attrib['{%s}type' % namespaces['xlink']] = 'simple'
    new_flocat.attrib['{%s}href' % namespaces['xlink']] = 'submission/METS.xml'
    new_flocat.attrib['LOCTYPE'] = 'URL'

    new_file.append(new_flocat)
    new_filegrp.append(new_file)
    filesec_element.append(new_filegrp)

    # EACH FILE GROUP
    for fileGrp in filesec_element.findall('{%s}fileGrp' % namespaces['']):
        if fileGrp.attrib['USE'].lower().startswith('representations'):
            rep_parts = Path(fileGrp.attrib['USE']).parts
            rep_name = rep_parts[1].rstrip('0123456789')
            rep_number = "{:02}.1".format(int(rep_parts[1][len(rep_name):]))
            preservation_rep_path = "{}/{}{}".format('representations', 'rep', rep_number)
            fileGrp.attrib['USE'] = preservation_rep_path

            preservation_mets = aip_root / preservation_rep_path / 'METS.xml'
            if preservation_mets.exists():
                files = [x for x in fileGrp.findall('{%s}file' % namespaces[''])]
                if len(files) == 1:
                    file = files[0]
                    flocat = file.find('{%s}FLocat' % namespaces[''])
                    if file.attrib['MIMETYPE'] == 'text/xml' and str(
                            flocat.attrib['{%s}href' % namespaces['xlink']]).endswith('METS.xml'):
                        file.attrib['MIMETYPE'] = str(mimetypes.guess_type(preservation_mets)[0])
                        file.attrib['SIZE'] = str(preservation_mets.stat().st_size)
                        file.attrib['CREATED'] = created_now
                        file.attrib['CHECKSUM'] = get_checksum(preservation_mets)
                        file.attrib['CHECKSUMTYPE'] = 'SHA-256'

                        flocat.attrib['{%s}href' % namespaces['xlink']] = preservation_rep_path + '/METS.xml'
                else:
                    print("More than one file in SIP representations fileGrp:", fileGrp.tag, fileGrp.attrib)
                    print("Not currently supported")
            else:
                print('ERROR: Expected Preservation METS.xml')

    # STRUCT MAP
    structmap_element = root.find('{%s}structMap' % namespaces[''])
    root_div_element = structmap_element.find('{%s}div' % namespaces[''])
    root_div_element.attrib['ID'] = new_uuid()
    for div in root_div_element.findall('{%s}div' % namespaces['']):
        if div.attrib['LABEL'].lower().startswith('representations'):
            rep_parts = Path(div.attrib['LABEL']).parts
            if len(rep_parts) == 1:
                for sub_div in div.findall('{%s}div' % namespaces['']):
                    if sub_div.attrib['LABEL'].lower().startswith('rep'):
                        rep = sub_div.attrib['LABEL']
                        rep_name = rep.rstrip('0123456789')
                        rep_number = "{:02}.1".format(int(rep[len(rep_name):]))
                        sub_div.attrib['LABEL'] = rep_name+rep_number
                        preservation_rep_path = "{}/{}{}".format('representations', 'rep', rep_number)
                        for pointer in sub_div:
                            if str(pointer.tag) == '{%s}mptr' % namespaces['']:
                                pointer.attrib['{%s}href' % namespaces['xlink']] = preservation_rep_path + '/METS.xml'
            elif len(rep_parts) == 2:
                rep_name = rep_parts[1].rstrip('0123456789')
                rep_number = "{:02}.1".format(int(rep_parts[1][len(rep_name):]))

                preservation_rep_path = "{}/{}{}".format('representations', rep_name, rep_number)
                div.attrib['LABEL'] = preservation_rep_path
                for pointer in div:
                    if str(pointer.tag) == '{%s}mptr' % namespaces['']:
                        pointer.attrib['{%s}href' % namespaces['xlink']] = preservation_rep_path + '/METS.xml'

    # UPDATE IDS
    update_all_mets_ids(tree, id_updates, namespaces)

    ET.indent(tree, space='    ', level=0)
    tree.write('%s/METS.xml' % aip_root, encoding='utf-8', xml_declaration=True)


def copy_sip_to_aip(sip_path, aip_path):
    """
    Copy the required items from the SIP into the necessary locations in the AIP
    :param Path sip_path:
    :param Path aip_path:
    :return:
    """
    # copy required items in to submissions and copy in to AIP root if required
    items_to_copy = {'representations': False, 'metadata': True, 'schemas': True, 'documentation': True,
                     'METS.xml': False}
    aip_submission_path = aip_path / "submission"
    expected_sip_reps_path = sip_path / 'representations'
    if expected_sip_reps_path.is_dir():
        if validate_representations_sequence(expected_sip_reps_path):
            aip_submission_path.mkdir()
            for item in items_to_copy.keys():
                item_path = sip_path / item
                destination_path = aip_submission_path / item
                if item_path.is_dir():
                    shutil.copytree(item_path, destination_path)
                    # if True, also copy item into aip root
                    if items_to_copy[item]:
                        shutil.copytree(item_path, aip_path / item)
                elif item_path.is_file():
                    # Will be METS.xml
                    shutil.copy2(item_path, destination_path)
                else:
                    print("%s not found" % item)
        else:
            print("Exiting.")
            sys.exit(1)
    else:
        print("Error: SIP representations directory not found")
        print("Exiting.")
        sys.exit(1)


def create_aip_representations(aip_path):
    """
    Create preservation directories to store archivematica transfer
    :param Path aip_path: path to AIP root
    """
    aip_submission_representations_path = aip_path / 'submission' / "representations"

    for rep in sorted(aip_submission_representations_path.iterdir()):
        rep = rep.stem
        rep_name = rep.rstrip('0123456789')
        rep_number = int(rep[len(rep_name):])

        # make preservation directory : rep1 -> rep01.1
        preservation_rep_path = aip_path / "representations" / "{}{:02}.1".format('rep', rep_number)
        (preservation_rep_path / "data").mkdir(parents=True)
        # create preservation rep METS.xml
        create_mets(preservation_rep_path)


def transform_sip_to_aip(sip_path, aip_path):
    if False:
        sip_name = sip_path.stem
        sip_uuid = sip_name[sip_name.index('uuid'):]
        package_name = sip_name[:sip_name.index('uuid')]
        aip_uuid = new_uuid()
        aip_name = package_name + aip_uuid
        aip_path = aip_path / aip_name
        id_updates = {sip_uuid: aip_uuid}
    else:
        sip_name = sip_path.stem
        aip_path = aip_path / sip_name
        id_updates = {}

    overwrite_and_create_directory(aip_path)

    copy_sip_to_aip(sip_path, aip_path)

    create_aip_representations(aip_path)

    sip_mets = Path(sip_path / 'METS.xml')

    create_root_aip_mets(sip_mets, aip_path, id_updates)

    # TODO:
    #  - Transfer archivematica AIP into preservation


def create_mets(path):
    """
    Creates METS.xml on directory and writes to directory root
    :param Path path: path to information package to create mets on
    """
    mets = metsrw.METSDocument()
    mets.append(create_fse(path, path))
    mets.write(str(path / "METS.xml"), pretty_print=True)
    print("METS written in: %s" % path)


def create_fse(current_path, aip_root_path):
    """
    Recursive call for creating metsrw.FSEntry tree to be written to METS
    :param Path current_path: keeps track of current directory
    :param Path aip_root_path: path to the AIP root
    :return FSEntry fse: completed tree of directory
    """
    base_directory = current_path.stem
    fse = metsrw.FSEntry(label=base_directory, type="Directory", file_uuid=str(uuid.uuid4()))
    relative_path = current_path.relative_to(aip_root_path)
    try:
        fse_use = relative_path.parts[0]
    except IndexError:
        fse_use = 'original'
    else:
        if len(relative_path.parts) > 1 and relative_path.parts[0] == 'representations':
            fse_use = '{}/{}'.format(relative_path.parts[0], relative_path.parts[1])

    if "METS.xml" in os.listdir(current_path):
        print("METS found: %s" % current_path)
        mets_path = str(current_path / 'METS.xml')
        file_fse = metsrw.FSEntry(use=fse_use, label="METS.xml",
                                  path=str(relative_path / "METS.xml"), type="Item",
                                  file_uuid=str(uuid.uuid4()), checksum=get_checksum(mets_path), checksumtype='SHA-256')
        fse.children.append(file_fse)
        return fse

    for item in os.listdir(current_path):
        item_path = current_path / item
        if item_path.is_dir():
            fse.children.append(create_fse(item_path, aip_root_path))
        elif item_path.is_file():
            file_fse = metsrw.FSEntry(use=fse_use, label=item, path=str(relative_path / item), type="Item",
                                      file_uuid=str(uuid.uuid4()), checksum=get_checksum(item_path),
                                      checksumtype='SHA-256')
            fse.children.append(file_fse)
        else:
            print("File Error - create_root_mets()")
    return fse


if __name__ == '__main__':
    if len(sys.argv) == 3:
        if validate_directories(Path(get_arg(1)), Path(get_arg(2))):
            transform_sip_to_aip(Path(get_arg(1)), Path(get_arg(2)))
        else:
            sys.exit(1)
    else:
        print("Error: Command should have the form:")
        print("python main.py <SIP Directory> <Output Directory>")
        sys.exit(1)
