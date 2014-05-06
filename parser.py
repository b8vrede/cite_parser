#!/usr/bin/env python
"""
SYNOPSIS

   parser [-h,--help] [-v,--verbose] [--version]

DESCRIPTION

    TODO This describes how to use this script. This docstring
    will be printed by the script if there is an error or
    if the user requests help (-h or --help).

EXAMPLES

    TODO: Show some examples of how to use this script.

AUTHOR

    Bart Vredebregt <bart.vredebregt@gmail.com>

LICENSE

    This script is in the public domain, free from copyrights or restrictions.

VERSION

    0.0.1
"""

import sys, os, traceback, optparse
import time
import re
import urllib
import urllib2
import xml.etree.ElementTree as ET
from collections import defaultdict

global options, args, BWB_dict

def main ():
    start_time = time.time()
    stage_start_time = time.time()
    parameters = {'subject':'http://psi.rechtspraak.nl/rechtsgebied#bestuursrecht_vreemdelingenrecht', 'max':'10', 'return':'DOC', 'sort':'DESC'}
    
    print "Loading BWB data..."
    BWB_dict = get_bwb_name_dict()
    print("Completed loading BWB data in {:.2f} seconds".format((time.time() - stage_start_time)))
    stage_start_time = time.time()
    
    print("Loading ECLI data...".format((stage_start_time - start_time)))
    eclis = get_eclis(parameters)
    print("Completed loading ECLI data in {:.2f} seconds".format((time.time() - stage_start_time)))
    stage_start_time = time.time()
    
    print("Parsing references...".format((time.time() - stage_start_time)))
    LawRegEx = re.compile('(?:[Aa]rtikel|[Aa]rt\\.) [0-9][0-9a-z:.]*(?:,? (?:lid|aanhef en lid|aanhef en onder|onder)? [0-9a-z]+,?|,? [a-z]+ lid,?)?(?:,? onderdeel [a-z],?)?(?:,? sub [0-9],?)?(?:(?: van (?:de|het)(?: wet)?|,?)? ((?:[A-Z][a-zA-Z]* ?|op de ?|wet ?|bestuursrecht ?)+))?(?: *\\(.*?\\))?')
    succes = 0
    total = 0
    fail = 0
    for e in eclis:
        refList = find_references(get_plain_text(get_document(e.text)))
        for ref in refList:
            total += 1
            law = LawRegEx.match(ref).group(1)
            # print LawRegEx.match(ref).group()
            if law is not None:
                law = law.strip().lower()
                if law in BWB_dict:
                    # print("{} --> {}".format(law, BWB_dict.get(law)))
                    succes += 1 
                else:
                    # print("{} --> No Match".format(law))
                    fail += 1
    print("Completed parsing references in {:.2f} seconds".format((time.time() - stage_start_time)))
    print("{} out of {} ({:.2%}) were successful,\n{} out of {} ({:.2%}) came back without a match,\nin a total time of {:.2f} seconds".format(succes, total, (float(succes)/float(total)), fail, total, (float(fail)/float(total)),(time.time() - start_time)))

def find_references(document):
    references = {}
    ReferenceRegEx = re.compile('((?:[Aa]rtikel|[Aa]rt\\.) [0-9][0-9a-z:.]*(?:,? (?:lid|aanhef en lid|aanhef en onder|onder)? [0-9a-z]+,?|,? [a-z]+ lid,?)?(?:,? onderdeel [a-z],?)?(?:,? sub [0-9],?)?(?:(?: van (?:de|het)(?: wet)?|,?)? (?:[A-Z][a-zA-Z]* ?|op de ?|wet ?|bestuursrecht ?)+)?(?: *\\(.*?\\))?)')
    
    return ReferenceRegEx.findall(document)

def get_eclis(parameters={'subject':'http://psi.rechtspraak.nl/rechtsgebied#bestuursrecht_vreemdelingenrecht', 'max':'100', 'return':'DOC'}):
    encoded_parameters = urllib.urlencode(parameters)
    feed = urllib2.urlopen("http://data.rechtspraak.nl/uitspraken/zoeken?"+encoded_parameters)
    nameSpace = {'xmlns':'http://www.w3.org/2005/Atom'}
    return ET.parse(feed).findall("./xmlns:entry/xmlns:id", namespaces=nameSpace)
    
def get_document(ecli):
    encoded_parameters = urllib.urlencode({'id':ecli})
    feed = urllib2.urlopen("http://data.rechtspraak.nl/uitspraken/content?"+encoded_parameters)
    nameSpace = {'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'ecli':'https://e-justice.europa.eu/ecli',
        'eu':'http://publications.europa.eu/celex/', 'dcterms':'http://purl.org/dc/terms/',
        'bwb':'bwb-dl', 'cvdr':'http://decentrale.regelgeving.overheid.nl/cvdr/', 'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
        'preserve':'http://www.rechtspraak.nl/schema/rechtspraak-1.0'}
    element = ET.parse(feed).find("./preserve:uitspraak", namespaces=nameSpace)
    return element
    
def get_plain_text(xml, encoding='UTF-8'):
    return ET.tostring(xml, encoding, method='text').strip()

def get_bwb_info(file = 'BWBIdList.xml'):
    return ET.parse(file)
    
def get_bwb_name_dict(XML=get_bwb_info()):
    # Create an list dictonary
    dict = defaultdict(list)
    
    # Define the namespace for the document
    nameSpace = {'bwb':'http://schemas.overheid.nl/bwbidservice'}
    
    # Find all regelingen
    regelingen = XML.findall("./bwb:RegelingInfoLijst/bwb:RegelingInfo", namespaces=nameSpace)
    
    for regeling in regelingen:
        BWBId = get_plain_text(regeling.find("./bwb:BWBId", namespaces=nameSpace))
        # Add BWBId to the dictonary
        dict[BWBId].append(BWBId)
        if BWBId is not None:
            #Parse OfficieleTitel
            titelNode = regeling.find("./bwb:OfficieleTitel", namespaces=nameSpace)
            if titelNode is not None:
                # Add OfficieleTitel to the dictonary if it exists
                dict[get_plain_text(titelNode).lower()].append(BWBId)
            
            #Parse CiteertitelLijst
            titelLijst = regeling.findall("./bwb:CiteertitelLijst/bwb:Citeertitel", namespaces=nameSpace)
            if len(titelLijst) != 0:
                # If there are 1 or more Citeertitel's iterate through them
                for titel in titelLijst:
                    # Select the titel node
                    titelNode = titel.find("./bwb:titel", namespaces=nameSpace)
                    if titelNode is not None:
                        # Add Citeertitel to the dictonary if it exists
                        cleanedTitel = re.sub("[\d]", "", get_plain_text(titelNode).lower()).strip()
                        dict[cleanedTitel].append(BWBId)
                        dict[get_plain_text(titelNode).lower()].append(BWBId)
                        
            #Parse NietOfficieleTitelLijst
            titelLijst = regeling.findall("./bwb:NietOfficieleTitelLijst/bwb:NietOfficieleTitel", namespaces=nameSpace)
            if len(titelLijst) != 0:
                # If there are 1 or more NietOfficieleTitel's iterate through them
                for titel in titelLijst:
                    dict[get_plain_text(titel).lower()].append(BWBId)
            
            #Parse AfkortingLijst
            titelLijst = regeling.findall("./bwb:AfkortingLijst/bwb:Afkorting", namespaces=nameSpace)
            if len(titelLijst) != 0:
                # If there are 1 or more Afkorting's iterate through them
                for titel in titelLijst:
                    dict[get_plain_text(titel).lower()].append(BWBId)
    return dict
        

main()