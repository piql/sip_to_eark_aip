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


def overwrite_and_create(directory):
    """
    Deletes directory if it exists and (re)creates directory
    :param str directory: path that needs to be (re)created
    """
    if os.path.isdir(directory):
        print("Overwriting '%s'" % directory)
        shutil.rmtree(directory)
    os.makedirs(directory)


def copy_sip_to_aip(sip_path, aip_path):
    # copy required items in to submissions and copy in to AIP root if required
    items_to_copy = {'representations': False, 'metadata': True, 'schemas': True, 'documentation': True,
                     'METS.xml': False}
    aip_submission_path = os.path.join(aip_path, "submission")
    if os.path.isdir(os.path.join(sip_path, 'representations')):
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
                #update_mets(destination_path)
            else:
                print("%s not found" % item)
    else:
        print("Error: Representations directory not found")
        sys.exit(1)


def update_representations(aip_path):
    # update representations and create preservation directories
    output_submission_representations_path = os.path.join(aip_path, 'submission', "representations")
    for rep in os.listdir(output_submission_representations_path):
        if rep.startswith("rep") and rep[len("rep"):].isdigit():

            # make preservation directory : rep1 -> rep01.1
            preservation_rep_path = os.path.join(aip_path, "representations", "rep{0:0=2d}.1".format(int(rep[len("rep"):])))
            os.makedirs(os.path.join(preservation_rep_path, "data"))
            # create preservation rep METS.xml
            create_mets(preservation_rep_path)

            # update mets
            rep_mets_file_path = os.path.join(output_submission_representations_path, rep, "METS.xml")
            if os.path.isfile(rep_mets_file_path):
                update_mets(rep_mets_file_path)
            else:
                print("%s METS.xml missing." % rep)
            """
            # rename sip rep directories : rep1 -> rep01
            os.rename(os.path.join(output_submission_representations_path, rep),
                      os.path.join(output_submission_representations_path, "rep{0:0=2d}".format(int(rep[len("rep"):]))))
            """
        else:
            print("Invalid file/folder in representations: %s" % rep)

        # TODO: change rep name in METS.xml to rep0x


def transform(sip_path, aip_path):
    aip_name = os.path.basename(os.path.normpath(sip_path))
    aip_path = os.path.join(aip_path, aip_name)

    overwrite_and_create(aip_path)

    copy_sip_to_aip(sip_path, aip_path)

    update_representations(aip_path)

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


def update_mets(mets_file):
    # register namespaces to ET parser
    for key, value in ET.iterparse(mets_file, events=['start-ns']):
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

    fse_use = current_path[len(aip_root_path+'/'):].split('\\')[0]
    if fse_use == "":
        fse_use = 'original'
    print("***")
    print("CURRENT PATH: %s" % current_path)
    print("AIP ROOT PATH: %s" % aip_root_path)
    print("AIP ROOT SUBFOLDER: %s" % fse_use)
    print("***")

    if "METS.xml" in os.listdir(current_path):
        print("METS found: %s" % current_path)
        file_fse = metsrw.FSEntry(use=fse_use, label="METS.xml", path=os.path.join(current_path[len(aip_root_path):], "METS.xml"), type="Item",
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
            # TODO: Validate folder structure?
            transform(sip_directory, output_directory)
        else:
            sys.exit(1)
    else:
        print("Error: Command should have the form:")
        print("python main.py <SIP Directory> <Output Directory>:")
        sys.exit(1)
