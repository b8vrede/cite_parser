import glob
import os
import argparse
import random
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

def fetch_random_refs(fileList, n):
    allRefs = []
    for file in fileList:
        allRefs.extend(find_ref(file))
    
    if allRefs is not None and n > 0 and n < len(allRefs):
        allRefs = random.sample(allRefs, n)
    
    return allRefs
    
def eval_refs(refs):
    global truepositive, falsepositive, truenegative, falsenegative
    counter = 0
    for ref in refs:
        counter += 1
        
        url = ref.get("resourceIdentifier", "No URL atribute (shouldn't be possible!)")
        string = ref.findtext("{http://purl.org/dc/terms/}string", "No ref string!")
        para = ref.findtext("{http://purl.org/dc/terms/}sentence", "No para block!")
    
        print("\n+---------------------------------------------------+\n\nProgress:\t{:.2%}\nURL:\t{}\nRef:\t{}\n\nContext:\t{}\n".format((float(counter)/len(refs)), url, string, para))
        
        if url == "No BWB found":
            print("The answer is Yes when it is correct that we didn't resolve this reference!")
        answer = raw_input('Is this classification correct: [Y/N] ')
        
        while answer not in ['y', 'Y', 'n', 'N']:
            print("Invalid input!")
            answer = raw_input('Is this classification correct: [Y/N] ')
        
        if url == "No BWB found":
            if answer.lower() == "y":
                truenegative += 1
            elif answer.lower() == "n":
                falsenegative += 1

        else:
            if answer.lower() == "y":
                truepositive += 1
            elif answer.lower() == "n":
                falsepositive += 1
# Main function
if __name__ == '__main__':
    truepositive = 0
    falsepositive = 0
    truenegative = 0
    falsenegative = 0
    
    # Parse the arguments
    parser = argparse.ArgumentParser(description='Tool for evaluation')
    parser.add_argument("-r", "--random",
                        action="store", type=int, metavar="X", dest="random", default=None,
                        help="Creates a random sample of size X from all avaible references")    
    parser.add_argument("-s", "--seed",
                        action="store", type=int, metavar="X", dest="seed", default=None,
                        help="Sets the seed of the random generator to X")                              
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
        
    fileList = read_ecli_files()
    
    
        
    if args.random > 0:
        refs = fetch_random_refs(fileList, args.random)
        print("+---------------------------------------------------+\n|\tFile:\t- (Random from {} file(s))".format(len(fileList)))
        print("|\tRefs: \t{}".format(len(refs)))
        eval_refs(refs)
    else:
        for file in fileList:
            print("+---------------------------------------------------+\n|\tFile:\t{}".format(file))
            refs = find_ref(file)

            print("|\tRefs: \t{}".format(len(refs)))

            eval_refs(refs)
    
    if (truepositive+falsepositive) == 0:
        precision = 0
    else:
        precision = float(truepositive)/float(truepositive+falsepositive)
        
    if (truepositive+falsenegative) == 0:    
        recall = 0
    else:
        recall = float(truepositive)/float(truepositive+falsenegative)

     
    print "RESULTS:\nTP: {}\t|FP: {}\n-------------------\nFN: {}\t| TN: {}".format(truepositive, falsepositive, falsenegative, truenegative)
    print "Precision:\t{0:.4f}\nRecall:\t{0:.4f}".format(precision, recall)