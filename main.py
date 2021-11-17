import os
import shutil
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
import metsrw


# logs_file_path = "./app.log"
# sys.stdout = open(logs_file_path, "w", buffering=1, encoding='utf-8')


def get_arg(index):
    try:
        sys.argv[index]
    except IndexError:
        return None
    else:
        return sys.argv[index]


def validate_directories(sip_dir, output_dir):
    if os.path.exists(sip_dir):
        if os.path.isdir(sip_dir):
            if os.path.exists(output_dir):
                if os.path.isdir(output_dir):
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
    :param str directory: path that needs to be (re)created
    """
    if os.path.isdir(directory):
        print("Overwriting '%s'" % directory)
        shutil.rmtree(directory)
    os.makedirs(directory)


def validate_representations_sequence(representations_path):
    # check sequence
    expected_sequence_number = 1
    previous_folder_name = '///'

    for rep in sorted(os.listdir(representations_path)):
        folder_name = rep.rstrip('0123456789')
        try:
            sequence_number = int(rep[len(folder_name):])
        except ValueError:
            print("ERROR in SIP representation. No sequence number.")
            return False

        if previous_folder_name == '///':
            previous_folder_name = folder_name
        elif folder_name != previous_folder_name:
            print("ERROR in SIP representations naming sequence. Expected:", previous_folder_name, "Got:", folder_name)
            return False

        if expected_sequence_number != sequence_number:
            print("ERROR in SIP representations number sequence. Expected:", expected_sequence_number, "Got:", sequence_number)
            return False
        else:
            expected_sequence_number += 1

    return True


def copy_sip_to_aip(sip_path, aip_path):
    # copy required items in to submissions and copy in to AIP root if required
    items_to_copy = {'representations': False, 'metadata': True, 'schemas': True, 'documentation': True,
                     'METS.xml': False}
    aip_submission_path = os.path.join(aip_path, "submission")
    expected_sip_reps_path = os.path.join(sip_path, 'representations')
    if os.path.isdir(expected_sip_reps_path):
        if validate_representations_sequence(expected_sip_reps_path):
            os.makedirs(aip_submission_path)
            for item in items_to_copy.keys():
                item_path = os.path.join(sip_path, item)
                destination_path = os.path.join(aip_submission_path, item)
                if os.path.isdir(item_path):
                    shutil.copytree(item_path, destination_path)
                    # if True also copy item into root
                    if items_to_copy[item]:
                        shutil.copytree(item_path, os.path.join(aip_path, item))
                elif os.path.isfile(item_path):
                    # Will be METS.xml
                    shutil.copy2(item_path, destination_path)
                    # update_mets(destination_path)
                else:
                    print("%s not found" % item)
        else:
            print("Exiting.")
            sys.exit(1)
    else:
        print("Error: root representations directory not found")
        print("Exiting.")
        sys.exit(1)


def update_sip_representations(aip_path):
    # update representations and create preservation directories
    output_submission_representations_path = os.path.join(aip_path, 'submission', "representations")

    print("Valid Rep Sequence:", validate_representations_sequence(output_submission_representations_path))

    if validate_representations_sequence(output_submission_representations_path):
        for rep in sorted(os.listdir(output_submission_representations_path)):
            rep_name = rep.rstrip('0123456789')
            rep_number = int(rep[len(rep_name):])

            # make preservation directory : rep1 -> rep01.1
            preservation_rep_path = os.path.join(aip_path, "representations", "{}{:02}.1".format(rep_name, rep_number))
            os.makedirs(os.path.join(preservation_rep_path, "data"))
            # create preservation rep METS.xml
            create_mets(preservation_rep_path)

            # update mets
            # rep_mets_file_path = os.path.join(output_submission_representations_path, rep, "METS.xml")
            # if os.path.isfile(rep_mets_file_path):
            #     update_mets(rep_mets_file_path)
            # else:
            #     print("%s METS.xml missing." % rep)

        # TODO: change rep name in METS.xml to rep0x


def transform(sip_path, aip_path):
    aip_name = os.path.basename(os.path.normpath(sip_path))
    aip_path = os.path.join(aip_path, aip_name)

    overwrite_and_create_directory(aip_path)

    copy_sip_to_aip(sip_path, aip_path)

    update_sip_representations(aip_path)

    # create root METS.xml
    create_mets(aip_path)

    # TODO:
    #  - Transfer archivematica AIP into preservation
    #  - Create root METS.xml for each preservation representations folder  - Update
    #  - Create root METS.xml for AIP root                                  - Update


def create_mets(path):
    print("METS.xml written in: %s" % path)
    mets = metsrw.METSDocument()
    mets.append(create_fse(path, path))
    mets.write(os.path.join(path, "METS.xml"), pretty_print=True)


# NOT USED
def update_mets(mets_file):
    # register namespaces to ET parser
    for key, value in ET.iterparse(mets_file, events=['start-ns']):
        # print("Key: ", value[0])
        # print("Value: ", value[1])
        # print()
        ET.register_namespace(value[0], value[1])

    tree = ET.parse(mets_file)
    root = tree.getroot()

    try:
        if root.attrib['TYPE']:
            root.attrib['TYPE'] = "AIP"
    except KeyError:
        print("ERROR: mets element: TYPE attribute missing")

    mets_header = root.find('{http://www.loc.gov/METS/}metsHdr')
    if mets_header is not None:
        mets_header.set('RECORDSTATUS', 'Revised')
        mets_header.set('LASTMODDATE', str(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
        mets_header.set('{https://dilcis.eu/XML/METS/CSIPExtensionMETS}OAISPACKAGETYPE', "AIP")

    tree.write(mets_file)


def create_fse(current_path, aip_root_path):
    """
    Recursive call
    :param aip_root_path:
    :param str current_path:
    :return FSEntry fse:
    """
    base_directory = os.path.basename(current_path)
    fse = metsrw.FSEntry(label=base_directory, type="Directory", file_uuid=str(uuid.uuid4()))

    current_path_list = current_path[len(aip_root_path + '/'):].split('\\')
    fse_use = current_path_list[0]
    if fse_use == '':
        fse_use = 'original'
    elif len(current_path_list)>1 and fse_use == 'representations':
        fse_use += '/{}'.format(current_path_list[1])

    if "METS.xml" in os.listdir(current_path):
        print("METS found: %s" % current_path)
        file_fse = metsrw.FSEntry(use=fse_use, label="METS.xml",
                                  path=os.path.join(current_path[len(aip_root_path):], "METS.xml"), type="Item",
                                  file_uuid=str(uuid.uuid4()))
        fse.children.append(file_fse)
        return fse

    for item in os.listdir(current_path):
        item_path = os.path.join(current_path, item)
        if os.path.isdir(item_path):
            fse.children.append(create_fse(item_path, aip_root_path))
            pass
        elif os.path.isfile(item_path):
            file_fse = metsrw.FSEntry(use=base_directory, label=item, path=current_path, type="Item",
                                      file_uuid=str(uuid.uuid4()))
            fse.children.append(file_fse)
        else:
            print("File Error - create_root_mets()")
    return fse


if __name__ == '__main__':
    numArgs = len(sys.argv)

    if numArgs == 3:
        sip_directory = get_arg(1)
        output_directory = get_arg(2)
        if validate_directories(sip_directory, output_directory):
            # TODO: Validate SIP folder structure?
            transform(sip_directory, output_directory)
        else:
            sys.exit(1)
    else:
        print("Error: Command should have the form:")
        print("python main.py <SIP Directory> <Output Directory>")
        sys.exit(1)
