# Penwern SIP to E-Ark AIP Generator

The aim of this project is to generate E-Ark conformant AIPs from SIPs.

The AIPs generated using these scripts should comply with the AIP specification laid out by [DILCIS](https://dilcis.eu/) and validate successfully  using the [CommonsIP Validator](https://github.com/keeps/commons-ip).

## Requirements

Python 3.9+

Python packages:
- metsrw

## Instructions

The first script, sip_to_eark_aip, takes the format `python sip_to_eark_aip.py <sip directory> <output directory>`.
The SIP will go through a minor validation check.
Once completed, the new AIP name will be returned. 

The second script, *create_preservation_mets.py*, should be run after you have placed your Archivematica AIPs in their respective repxx-preservation directories.
It takes the format `python create_preservation_mets.py <repxx-preservation directory>`.
This will generate preservation METS.xml.
