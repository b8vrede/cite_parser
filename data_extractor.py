import glob
import os
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict
import re
import sys

# Fetches a list of all ECLI files in the ECLIs folder
def read_ecli_files():
    filelocation = os.path.normpath('ECLIs/*.xml')
    return glob.glob(filelocation)

# Extracts data from the ECLI files
def parse_refs():
    
    # Fetch a list with XML files in the ECLIs folder
    files = read_ecli_files()
    
    # Initialize dictionary's
    article_counter = defaultdict(int)
    BWB_counter = defaultdict(int)
    ref_order = defaultdict(list)
    files_proccessed = 0
    
    # Compile pattern for BWB extraction
    p = re.compile("(BWB[^/]+)")
    
    
    # Loop through files
    print "Parsing files:"
    for file in files:
        # Print current status (and count number of files proccessed)
        files_proccessed += 1
        sys.stdout.write("{} out of {} done\r".format(files_proccessed, len(files)))
        sys.stdout.flush()
         
        # Initialize local list and dictonary
        file_ref_order = []
        counter = defaultdict(int)
        
        # Define namespace for xml extraction
        nameSpace = {'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'ecli': 'https://e-justice.europa.eu/ecli',
                 'eu': 'http://publications.europa.eu/celex/', 'dcterms': 'http://purl.org/dc/terms/',
                 'bwb': 'bwb-dl', 'cvdr': 'http://decentrale.regelgeving.overheid.nl/cvdr/',
                 'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                 'preserve': 'http://www.rechtspraak.nl/schema/rechtspraak-1.0'}
        
        # Set XML encoding
        parser = ET.XMLParser(encoding="utf-8")
        
        # Parse the current XML file
        xml = ET.parse(file, parser=parser)
        
        # Find the ECLI of the file and create its URI
        ecli = xml.find("./rdf:RDF/rdf:Description/dcterms:identifier", namespaces=nameSpace).text
        ECLI_URI = "http://rechtspraak.nl/ecli?id=" + ecli
        
        # Find all ref's (that are added by the parser)
        refs = xml.findall("./rdf:RDF/rdf:Description/dcterms:references[@metaLexResourceIdentifier]", namespaces=nameSpace)
        
        # Do stuff for each ref
        for ref in refs:
            
            # Get the BWB URI from the "metaLexResourceIdentifier" attribute
            BWB_URI = ref.get("metaLexResourceIdentifier")
            
            # Increase counters
            counter[BWB_URI] += 1
            article_counter[BWB_URI] += 1
            
            # Try to extract the BWB from the URI
            m = p.search(BWB_URI)
            
            # If there is a BWB do:
            if m is not None:
                
                # Fetch the BWB
                cleanBWB = m.group()
                
                # Append it to the local ref order list
                file_ref_order.append(cleanBWB)
                
                # Increase the count for the found BWB
                BWB_counter[cleanBWB] += 1
        
        # For each BWB_URI we found do:
        for BWB_URI in counter.keys():
            
            # Depending on parameters output edges with or without occurrence count
            if args.counts:
                args.outputFile.write("<{}> <{}> {}\n".format(ECLI_URI, BWB_URI, counter[BWB_URI]))
            else:
                args.outputFile.write("<{}> <{}>\n".format(ECLI_URI, BWB_URI))
        
        # If we found refs, add the order list to the global dictonary
        if len(file_ref_order) >= 1:
            ref_order[ecli] = file_ref_order
    
    # Depending on parameters output a file with ECLI   [order of BWBs]
    if args.ordered:
        file = os.path.normpath('output\Order_list.csv')
        with open(file, "w") as myfile:
            for ecli in ref_order.keys():  
                myfile.write("{}\t{}\n".format(ecli, ref_order[ecli]))
    
    # Depending on parameters output 2 files:
    # 1. BWB followed by the number of occurrences
    # 2. BWB URIs followed by the number of occurrences
    if args.counts:  
        file = os.path.normpath('output/BWBList.csv')
        outputBWB = []
        p = re.compile("(BWB[^/]+)")
        with open(file, "w") as myfile:
            myfile.write("{}\t{}\n".format("BWB", "Count"))
            for BWB in BWB_counter.keys():
                myfile.write("{}\t{}\n".format(BWB, BWB_counter[BWB]))
        
        file = os.path.normpath('output/BWBArticleList.csv')
        outputBWB = []
        with open(file, "w") as myfile:
            myfile.write("{}\t{}\n".format("BWB URI", "Count"))
            for BWB in article_counter.keys():
                myfile.write("{}\t{}\n".format(BWB, article_counter[BWB]))
        
        
        
# Main function
if __name__ == '__main__':
    # Parse the arguments
    parser = argparse.ArgumentParser(description='Tool for extracting RDF tuples from XML')
    parser.add_argument('outputFile', type=argparse.FileType('w'))
    parser.add_argument("-c", "--counts",
                        action="store_true", dest="counts", default=False,
                        help="Add counters to the extracted edges and creates BWBList.csv with counts per BWB and BWBArticleList.csv with counts per URI")
    parser.add_argument("-o", "--ordered",
                        action="store_true", dest="ordered", default=False,
                        help="Creates a csv file with the refs in order of occurrence")
    args = parser.parse_args()
    
    # Call main function
    parse_refs()