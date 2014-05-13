import glob
import os
import xml.etree.ElementTree as ET

def read_ecli_files():
    filelocation = os.path.normpath('ECLIs/*.xml')
    return glob.glob(filelocation)
    
def find_ref(file):
    nameSpace = {'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#', 'ecli': 'https://e-justice.europa.eu/ecli',
                 'eu': 'http://publications.europa.eu/celex/', 'dcterms': 'http://purl.org/dc/terms/',
                 'bwb': 'bwb-dl', 'cvdr': 'http://decentrale.regelgeving.overheid.nl/cvdr/',
                 'rdfs': 'http://www.w3.org/2000/01/rdf-schema#',
                 'preserve': 'http://www.rechtspraak.nl/schema/rechtspraak-1.0'}
     
    parser = ET.XMLParser(encoding="utf-8")
    xml = ET.parse(file, parser=parser)
    refs = xml.findall("./rdf:RDF/rdf:Description/dcterms:references[@resourceIdentifier]", namespaces=nameSpace)
    
    return refs

def eval_refs(refs):
    global positive, negative
    
    for ref in refs:
        url = ref.get("resourceIdentifier", "No URL!")
        string = ref.findtext("{http://purl.org/dc/terms/}string", "No ref string!")
        para = ref.findtext("{http://purl.org/dc/terms/}sentence", "No para block!")
        print("+---------------------------------------------------+\n\nURL:\t{}\nRef:\t{}\n\nContext:\t{}\n".format(url, string, para))
        
        answer = raw_input('Is this classification correct: [Y/N] ')
        
        while answer not in ['y', 'Y', 'n', 'N']:
            print("Invalid input!")
            answer = raw_input('Is this classification correct: [Y/N] ')
        
        if answer.lower() == "y":
            positive += 1
        elif answer.lower() == "n":
            negative += 1

positive = 0
negative = 0

fileList = read_ecli_files()

for file in fileList:
    print("+---------------------------------------------------+\n|\tFile:\t{}".format(file))
    refs = find_ref(file)

    print("|\tRefs: \t{}".format(len(refs)))

    eval_refs(refs)

    total = positive + negative

    print "P: {} ({:.2%}) \nN: {} ({:.2%})".format(positive, float(positive)/total, negative, float(negative)/total)