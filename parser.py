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

import sys, os, traceback, argparse
import time
import socket
import re
import urllib
import urllib2
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
from collections import defaultdict
from multiprocessing import Process, Manager, Value

global stage_start_time, BWB_dict, eclis

def parse_references(eclis, BWB_dict, total, succes, fail, refs, args, regex, lawGroup):
    # Start function timer
    stage_start_time = time.time()
    
    # Prints first sign of life (useful to check if all processes are working)
    print("Parsing references...".format())
    
    # Compile the supplied regex for finding references
    ReferenceRegEx = re.compile(regex)
    
    # Check whether there are any ECLIs in the shared todolist (eclis)
    while len(eclis) > 0:
        # Init error counter
        errorScore = 0
        
        # Take and remove an ecli from the top of the shared todolist
        e = eclis.pop()
        
        # Fetch the file for the ecli popped before
        ecliFile = get_ecli_file(e.text)
        
        # If the get_ecli_file function return None a time out has occurred
        if ecliFile is None:    # Time out has occurred
            
            # Put the ECLI back into the todolist
            eclis.append(e)
            
        # Extract the document from the file and make it plaintext
        ecliDocument = get_plain_text(get_document(e.text, ecliFile))
        
        # Check whether there is a document
        if ecliDocument is not None:
            # Init the cleanLaw as None, cleanLaw is used to inherit the law from the previous reference
            cleanLaw = None
            
            # Fetch the list with matches of the regex in the plaintext document
            refList = find_references(ecliDocument, regex)

            # Do things with the found references
            for ref in refList:
                
                # Add one to the total counter
                total.value += 1
                
                # Fetch the match which indicates the law
                law = ref[lawGroup]
                
                # Check whether there is a match in the law group
                if law is not None:             # A law was found
                    
                    # Clean extra whitespace of the begin and the end of the law match and make it all lowercase
                    cleanLaw = law.strip().lower()
                    
                    # Check whether the law is in our dictionary
                    if cleanLaw in BWB_dict:        # Law is in the dictionary
                        
                        # Fetches all the BWBs associated with the law and remove duplicates
                        BWB = list(set(BWB_dict.get(cleanLaw)))
                        
                        # Increase the succes counter!
                        succes.value += 1
                    else:                           # Law is not in the dictionary
                        
                        # Set an empty BWB as there is a Law reference but we don't know what it is suppossed to be
                        BWB = ""
                        
                        # Increase the counters
                        fail.value += 1
                        errorScore += 1                        
                elif cleanLaw is not None:      # No law was found but we have a previous law we can use, so we will use the current values
                    # Increase counter
                    succes.value += 1
                    
                # Create an tuple with the information that was found
                tuple = {"ReferenceString":ref[0], "RawBWB":BWB}
                
                # Check whether the ECLI is already a key in the global dictionary refs
                if e.text in refs:          # ECLI is in dictionary
                    
                    # Fetch the current dictionary entry
                    result = refs[e.text]
                    
                    # Append the current result to the list
                    result.append(tuple)
                else:                      # ECLI is not in dictionary
                    
                    # Create a list with the result
                    result = [tuple]
                
                # Put the dictionary entry back (unknown keys are created)
                refs[e.text] = result
            
            # When the XML output option is do this
            if args.xmlOutput:          # XML output is ON
                
                # Define the namespace for the XML document, needed for selecting the right node to place the results in
                nameSpace = {'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'ecli':'https://e-justice.europa.eu/ecli',
                'eu':'http://publications.europa.eu/celex/', 'dcterms':'http://purl.org/dc/terms/',
                'bwb':'bwb-dl', 'cvdr':'http://decentrale.regelgeving.overheid.nl/cvdr/', 'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
                'preserve':'http://www.rechtspraak.nl/schema/rechtspraak-1.0'}
                
                # Find the RDF node in the XML with an about tag (this is always the second Description block of the RDF)
                root = ecliFile.find("./rdf:RDF/rdf:Description[@rdf:about]", namespaces=nameSpace)
                
                # Check whether we could find the correct block to place the results
                if root is not None:        # The block was found
                    
                    # For each reference we found in this document do:
                    for tuple in refs[e.text]:
                    
                        # Create an new node in the first namespace
                        parentRefNode = ET.SubElement(root, "ns1:references")
                        
                        # Give it a tag indicating we are pointing at a BWB
                        parentRefNode.set("ns2:label", "Wetsverwijzing")
                        
# TODO!!                # Add a tag with the a string of the found BWBs, should be an URI
                        parentRefNode.set("resourceIdentifier", " ".join(tuple.get("RawBWB")))
                        
                        # Set the text of the node to the text of the reference
                        parentRefNode.text = tuple.get("ReferenceString")
               
                    # Create the proper file location using python os libary to make it OS independent
                    file = os.path.normpath('ECLIs/'+re.sub(":", "-", e.text)+'.txt')
                    
                    # Check whether the XML needs to be nicely formatted
                    if args.prettyPrint:    # XML needs to be nicely formatted

                        # Turn the current document in a String
                        rawXML = ET.tostring(ecliFile.getroot(), method='xml')
                        
                        # Remove all the extra white spaces from the string and create a miniDOM object
                        domXML = parseString(re.sub("\s*\n\s*", "", rawXML))
                        
                        # Use toPrettyXML to properly format the file (and encode it in UTF-8 as it is the standard for XML)
                        outputXML = domXML.toprettyxml(indent="\t").encode('utf-8')
                        
                        # Write the XML to the file
                        with open(file, "w") as myfile:
                            myfile.write(outputXML)
                            
                    else:                   # XML doesn't need to be nicely formatted
                        
                        # Write the XML to a file without any extra indents or newlines
                        ecliFile.write(file, encoding='utf8', method='xml') 
                else:                   # The block was not found, occurs when the location of the block is wrong
                    print "No Meta data found (shouldn't happen ever!)"
    
    # Print completion message
    print("Completed parsing references in {:.2f} seconds".format((time.time() - stage_start_time)))
    
def find_references(document, regex):
    
    # Compile the regex
    ReferenceRegEx = re.compile(regex)
    
    # Return ALL matches to the regex
    return ReferenceRegEx.findall(document)

def get_eclis(parameters={'subject':'http://psi.rechtspraak.nl/rechtsgebied#bestuursrecht_vreemdelingenrecht', 'max':'100', 'return':'DOC'}):
    
    # Start function timer
    stage_start_time = time.time()
    
    # Print welcome message
    print("Loading ECLI data...".format())
    
    # URL encode the parameters
    encoded_parameters = urllib.urlencode(parameters)
    
    # Create an URL feed to the proper URL
    feed = urllib2.urlopen("http://data.rechtspraak.nl/uitspraken/zoeken?"+encoded_parameters)
    
    # Define Namespace for the XML file
    nameSpace = {'xmlns':'http://www.w3.org/2005/Atom'}
    
    # Find all Entries in the results XML
    eclis = ET.parse(feed).findall("./xmlns:entry/xmlns:id", namespaces=nameSpace)
    
    # Print Completion message
    print("Completed loading ECLI data in {:.2f} seconds".format((time.time() - stage_start_time)))

    # Return the list of entry found above
    return eclis

def get_ecli_file(ecli):
    
    # URL encode the parameters
    encoded_parameters = urllib.urlencode({'id':ecli})
    
    # Try to open the file for the ECLI
    try:
        feed = urllib2.urlopen("http://data.rechtspraak.nl/uitspraken/content?"+encoded_parameters, timeout = 3)
    
    # Catch Time out's
    except (urllib2.HTTPError, urllib2.URLError, socket.timeout) as err:
        
        # Print an error message
        print("{} timed out, retrying in 3 seconds!".format(ecli))
        
        # Sleep for 3 seconds to give the server time to restore
        time.sleep(3)
        
        # Pass the exception (proper error handling)
        pass
        
        # Return None to have the ECLI re-added to the todolist
        return None
    else:   # When no exception has occurred
        
        # Create an ElementTree from the feed
        element = ET.parse(feed)
        
        # Return the tree
        return element
        
def get_document(ecli, element):

    # Define the name space
    nameSpace = {'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'ecli':'https://e-justice.europa.eu/ecli',
            'eu':'http://publications.europa.eu/celex/', 'dcterms':'http://purl.org/dc/terms/',
            'bwb':'bwb-dl', 'cvdr':'http://decentrale.regelgeving.overheid.nl/cvdr/', 'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
            'preserve':'http://www.rechtspraak.nl/schema/rechtspraak-1.0'}
    
    # Return the element holding the document
    return element.find("./preserve:uitspraak", namespaces=nameSpace)
    
def get_plain_text(xml, encoding='UTF-8'):
    
    # Check whether input is None
    if xml is not None:         # Input is not None
        
        # Returns a plain text version of the Element given (also removes extra whitespaces)
        return ET.tostring(xml, encoding, method='text').strip()
    else:                       # Input is None
        
        # Return None (same as input)
        return None

def get_bwb_info(file = 'BWBIdList.xml'):
    
    # Returns an ElementTree for the specified local file holding the information about BWB ID's
    return ET.parse(file)
    
def get_bwb_name_dict(XML=get_bwb_info()):
    
    # Start function timer
    stage_start_time = time.time()
    
    # Print Welcome message
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
            
            # Parse OfficieleTitel
            titelNode = regeling.find("./bwb:OfficieleTitel", namespaces=nameSpace)
            
            # Add OfficieleTitel to the dictonary if it exists
            if titelNode is not None:
                dict[get_plain_text(titelNode).lower()].append(BWBId)
            
            #Parse CiteertitelLijst
            titelLijst = regeling.findall("./bwb:CiteertitelLijst/bwb:Citeertitel", namespaces=nameSpace)
            
            # If there are 1 or more Citeertitel's iterate through them
            if len(titelLijst) != 0:
                for titel in titelLijst:
                
                    # Select the titel node
                    titelNode = titel.find("./bwb:titel", namespaces=nameSpace)
                    
                    # Add Citeertitel to the dictionary if it exists
                    if titelNode is not None:
                        dict[get_plain_text(titelNode).lower()].append(BWBId)
                        
                        # Clean the citeertitel and also append it to the dictionary
                        cleanedTitel = re.sub("[\d]", "", get_plain_text(titelNode).lower()).strip()
                        dict[get_plain_text(cleanedTitel).lower()].append(BWBId)
                        
                        
            #Parse NietOfficieleTitelLijst
            titelLijst = regeling.findall("./bwb:NietOfficieleTitelLijst/bwb:NietOfficieleTitel", namespaces=nameSpace)
            
            # If there are 1 or more NietOfficieleTitel's iterate through them
            if len(titelLijst) != 0:
                for titel in titelLijst:
                    
                    # Add NietOfficieleTitel to the dictionary
                    dict[get_plain_text(titel).lower()].append(BWBId)
            
            #Parse AfkortingLijst
            titelLijst = regeling.findall("./bwb:AfkortingLijst/bwb:Afkorting", namespaces=nameSpace)
            
            # If there are 1 or more Afkorting's iterate through them
            if len(titelLijst) != 0:
                for titel in titelLijst:
                    dict[get_plain_text(titel).lower()].append(BWBId)
                    
    # Print completion message
    print("Completed loading BWB data in {:.2f} seconds".format((time.time() - stage_start_time)))
    
    # Return the created dictionary
    return dict

# Main function
if __name__ == '__main__':
    
    # Start global timer
    start_time = time.time()
    
    # Parse the arguments
    parser = argparse.ArgumentParser(description='Downloads ECLIs and adds references to them')
    parser.add_argument("-x", "--xmlOutput", "--xml",
                      action="store_true", dest="xmlOutput", default=False,
                      help="Outputs references in XML file")
    parser.add_argument("--pretty",
                      action="store_true", dest="prettyPrint", default=False,
                      help="Prints formatted XML (takes longer)")
    parser.add_argument("-m", "--multi",
                      action="store", type=int, metavar="X", dest="processes", default="1",
                      help="Creates X processes in order to speed up the parsing")
    args = parser.parse_args()
    
    
    # Regex for references (PLEASE INDICATE THE LAW GROUP BELOW START COUNTING FROM 0)
    regex = ('((?:[Aa]rtikel|[Aa]rt\\.) ([0-9][0-9a-z:.]*),?'                #Matches Artikel and captures the number (and letter) combination for the article
            '((?: (?:lid|aanhef en lid|aanhef en onder|onder)?(?:[0-9a-z ]|tot en met)+,?'  # matches "lid .. (tot en met ...)"
            '|,? (?:[a-z]| en )+ lid,?)*)'                                  # matches a word followed by "lid" e.g. "eerste lid"
            '(,? onderdeel [a-z],?)?'                                       # captures "onderdeel ..."
            '(,? sub [0-9],?)?'                                             # captures "sub ..."
            '(?:(?: van (?:de|het|)(?: wet)?|,?)? *'                        # matches e.g. "van de wet "
            '((?:(?:[A-Z0-9][a-zA-Z0-9]*|de|wet|bestuursrecht) *)+))? *'    # matches the Title
            '(?:\(([^\)]+?)\))?)')                                           # matches anything between () after the title
    
    # Indicates which match group in the regex holds the law title
    regexLawGroup = 5
    
    # Parameters for ECLI selection
    parameters = {'subject':'http://psi.rechtspraak.nl/rechtsgebied#bestuursrecht_vreemdelingenrecht', 'max':'1', 'return':'DOC', 'sort':'DESC'}
    
    # Create the dictionary for the law (key: law, value: list of related BWB's)
    BWB_dict = get_bwb_name_dict()

    # Fetch the list of ECLI's corresponding to the parameters
    eclis = get_eclis(parameters)
    
    # If the list of ECLI's is not empty, prepare for parsing
    if len(eclis) > 0:
        
        # Creating shared variables for the counters
        succes = Value('i',0)
        total = Value('i',0)
        fail = Value('i',0)
        
        # Create managers for the variables in used multi processing 
        manager = Manager()
        ecliManager = manager.list(eclis)
        BWBManager = manager.dict(BWB_dict)
        refs = manager.dict(defaultdict(list))
        
        # Check whether the user asked for more than one process
        if args.processes > 1:      # More than one process (multi-processing)
        
            # Print multi process welcome messages
            print("Parsing with {} processes....".format(args.processes))
            
            # Create job list
            jobs = []
            
            # Create the jobs
            for i in range(args.processes):
                
                # Make a process calling the parse_references
                p = Process(target=parse_references, args=(ecliManager, BWBManager, total, succes, fail, refs, args, regex, regexLawGroup))
                
                # Add the job to the list
                jobs.append(p)
                
                # Start the process
                p.start()
                
                # Print start message
                print("{} Started".format(p.name))
            
            # Holding loop, keeps the main process alive while the child processes are working
            while len(ecliManager) > 0:
            
                # Only print progress message when a ECLI is processed
                if(len(ecliManager) != len(eclis)):
                    print("{} ECLI's remaining".format(len(ecliManager)))
                
                # Sleep for 2 seconds to prevent output spamming and unnecessary CPU usage 
                time.sleep(2)
            
            # When all ECLI are out of the todo list check whether all processes are done
            while len(jobs) > 0:
                
                # Check all processes in the job list
                for p in jobs:
                
                    if p.is_alive():        # If a process is still alive it is busy so leave it in the list
                        print("Waiting for {} to return...".format(p.name))
                    else:                   # If a procces is not alive remove it from the list
                        jobs.remove(p)
                        
                # Sleep for 1 seconds to prevent output spamming and unnecessary CPU usage
                time.sleep(1)
        else :
            
            # Print single process welcom message
            print("Parsing with single process....")
            
            # Call the parse_references function
            parse_references(ecliManager, BWBManager, total, succes, fail, refs, args, regex, regexLawGroup)

        # Print completion message
        print("{} out of {} ({:.2%}) were successful,\n{} out of {} ({:.2%}) came back without a match,\nin a total time of {:.2f} seconds".format(succes.value, total.value, (float(succes.value)/float(total.value)), fail.value, total.value, (float(fail.value)/float(total.value)),(time.time() - start_time)))
