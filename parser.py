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
import socket
import re
import urllib
import urllib2
import xml.etree.ElementTree as ET
from collections import defaultdict
from multiprocessing import Process, Manager, Value

global stage_start_time, BWB_dict, eclis

def parse_references(eclis, BWB_dict, total, succes, fail, failedRefs):    
    stage_start_time = time.time()
    print("Parsing references...".format())
    LawRegEx = re.compile('(?:[Aa]rtikel|[Aa]rt\\.) [0-9][0-9a-z:.]*(?:,? (?:lid|aanhef en lid|aanhef en onder|onder)? [0-9a-z]+,?|,? [a-z]+ lid,?)?(?:,? onderdeel [a-z],?)?(?:,? sub [0-9],?)?(?:(?: van (?:de|het)(?: wet)?|,?)? ((?:[A-Z][a-zA-Z]* ?|op de ?|wet ?|bestuursrecht ?)+))?(?: *\\(.*?\\))?')
    
    while len(eclis) > 0:
        printText = 0
        e = eclis.pop()
    # for e in eclis:
        Ecli = get_plain_text(get_document(e.text))
        if Ecli is not None:

            refList = find_references(Ecli)
            if refList is None:
                eclis.append(e)
            for ref in refList:
                total.value += 1
                law = LawRegEx.match(ref).group(1)
                # print LawRegEx.match(ref).group()
                if law is not None:
                    law = law.strip().lower()
                    if law in BWB_dict:
                        # print("{} --> {}".format(law, BWB_dict.get(law)))
                        succes.value += 1 
                    else:
                        # print("{} --> No Match".format(law))
                        fail.value += 1
                        printText += 1
                        if law in failedRefs:
                            failedRefs[law] += 1
                        else:
                            failedRefs[law] = 1
                            
                else:
                    printText += 1
            if printText > 15:
                file = os.path.normpath('candidates/candidate_'+re.sub(":", "-", e.text)+'.txt')
                ET.ElementTree(get_document(e.text)).write(file, encoding='UTF-8', method='text')
                with open(file, "a") as myfile:
                    myfile.write('REFERENCES\n')
                    for ref in refList:
                        myfile.write(ref+'\n')
    print("Completed parsing references in {:.2f} seconds".format((time.time() - stage_start_time)))
    
def find_references(document):
    references = {}
    ReferenceRegEx = re.compile('((?:[Aa]rtikel|[Aa]rt\\.) [0-9][0-9a-z:.]*(?:,? (?:lid|aanhef en lid|aanhef en onder|onder)? [0-9a-z]+,?|,? [a-z]+ lid,?)?(?:,? onderdeel [a-z],?)?(?:,? sub [0-9],?)?(?:(?: van (?:de|het)(?: wet)?|,?)? (?:[A-Z][a-zA-Z]* ?|op de ?|wet ?|bestuursrecht ?)+)?(?: *\\(.*?\\))?)')
    
    return ReferenceRegEx.findall(document)

def get_eclis(parameters={'subject':'http://psi.rechtspraak.nl/rechtsgebied#bestuursrecht_vreemdelingenrecht', 'max':'100', 'return':'DOC'}):
    stage_start_time = time.time()
    print("Loading ECLI data...".format())
    encoded_parameters = urllib.urlencode(parameters)
    feed = urllib2.urlopen("http://data.rechtspraak.nl/uitspraken/zoeken?"+encoded_parameters)
    nameSpace = {'xmlns':'http://www.w3.org/2005/Atom'}
    eclis = ET.parse(feed).findall("./xmlns:entry/xmlns:id", namespaces=nameSpace)
    print("Completed loading ECLI data in {:.2f} seconds".format((time.time() - stage_start_time)))
    stage_start_time = time.time()
    
    return eclis
    
def get_document(ecli):
    encoded_parameters = urllib.urlencode({'id':ecli})
    try:
        feed = urllib2.urlopen("http://data.rechtspraak.nl/uitspraken/content?"+encoded_parameters, timeout = 3)
    except (urllib2.HTTPError, urllib2.URLError, socket.timeout) as err:
        print("{} timed out, retrying in 3 seconds!".format(ecli))
        time.sleep(3)
        pass
        return None
    else:
        nameSpace = {'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'ecli':'https://e-justice.europa.eu/ecli',
            'eu':'http://publications.europa.eu/celex/', 'dcterms':'http://purl.org/dc/terms/',
            'bwb':'bwb-dl', 'cvdr':'http://decentrale.regelgeving.overheid.nl/cvdr/', 'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
            'preserve':'http://www.rechtspraak.nl/schema/rechtspraak-1.0'}
        element = ET.parse(feed).find("./preserve:uitspraak", namespaces=nameSpace)
        return element
    
def get_plain_text(xml, encoding='UTF-8'):
    if xml is not None:
        return ET.tostring(xml, encoding, method='text').strip()
    else:
        return None

def get_bwb_info(file = 'BWBIdList.xml'):
    return ET.parse(file)
    
def get_bwb_name_dict(XML=get_bwb_info()):
    stage_start_time = time.time()
    print "Loading BWB data..."
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
    print("Completed loading BWB data in {:.2f} seconds".format((time.time() - stage_start_time)))
    stage_start_time = time.time()
    return dict

if __name__ == '__main__':    
    start_time = time.time()
    parameters = {'subject':'http://psi.rechtspraak.nl/rechtsgebied#bestuursrecht_vreemdelingenrecht', 'max':'200', 'return':'DOC', 'sort':'DESC'}

    processes = 4
    
    BWB_dict = get_bwb_name_dict()

    eclis = get_eclis(parameters)
    
    if len(eclis) > 0:
        print("Preparing Workers....")
        succes = Value('i',0)
        total = Value('i',0)
        fail = Value('i',0)
        
        manager = Manager()
        ecliManager = manager.list(eclis)

        BWBManager = manager.dict(BWB_dict)
        failedRefs = manager.dict()
        printList = manager.list()
        
        jobs = []
        for i in range(processes):
            p = Process(target=parse_references, args=(ecliManager, BWBManager, total, succes, fail, failedRefs))
            jobs.append(p)
            p.start()
            print("{} Started".format(p.name))
		
        while len(ecliManager) > 0:
            if(len(ecliManager) != len(eclis)):
                print("{} ECLI's remaining".format(len(ecliManager)))
            time.sleep(2)
        
        LivingAgents = processes
        while LivingAgents != 0:
            for p in jobs:
                if p.is_alive():
                    print("Waiting for {} to return...".format(p.name))
                else:
                    LivingAgents -= 1
                    jobs.remove(p)
            time.sleep(1)
            
        print("{} out of {} ({:.2%}) were successful,\n{} out of {} ({:.2%}) came back without a match,\nin a total time of {:.2f} seconds".format(succes.value, total.value, (float(succes.value)/float(total.value)), fail.value, total.value, (float(fail.value)/float(total.value)),(time.time() - start_time), failedRefs))
