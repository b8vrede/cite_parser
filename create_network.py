import rdflib
import re
import numpy as np
import matplotlib.pyplot as plt
from networkx import *
import argparse

def select_highest(central_list):  
    top_list = []
    if len(central_list) > 0:
        sorted_central_list = sorted(central_list, reverse=True, key=central_list.get)
        for node in sorted_central_list:
            m = law_regex.match(node.encode('ascii','ignore'))
            if m is not None:
                most_similar = node
                top_list.append(node)
                print "{}. Best match {}\n\tScore: {:.15f}".format(len(top_list), node, central_list[node])
                if len(top_list) >= 10:
                    break
    else:
        most_similar = ""
    
    return top_list

def build_network():
    # Read edge file
    G = nx.read_weighted_edgelist(args.caselaw) # , create_using=nx.DiGraph() <-- Used for creating directional graphs

    # Fetch sorted degree list
    node_and_degree = G.degree()
    degree_sorted = sorted(node_and_degree.items(), key=lambda node: node[1])

    print "GLOBAL Nodes: {} Edges: {}".format(len(G.nodes()), len(G.edges()))

    # (current_node, degree) = degree_sorted[1000]
    current_node = u"<http://doc.metalex.eu:8080/page/id/BWBR0007333/artikel/12>"

    # Select the surrounding nodes and edges
    local_graph = ego_graph(G, current_node, radius = 2, center = True, undirected = True)

    print "LOCAL  Nodes: {} Edges: {}".format(len(local_graph.nodes()), len(local_graph.edges()))

    # Fetch all the nodes and init a empty list for the case law nodes
    local_nodes = local_graph.nodes()
    case_law_nodes = []

    # Iter through all the nodes and append the case law nodes to their list
    for node in local_nodes:
        m = case_law_regex.match(node.encode('ascii','ignore'))
        if m is not None:
            case_law_nodes.append(node)

    # Create closeness centrality list and find the best matching law
    central_list = closeness_centrality(local_graph)
    top_list = select_highest(central_list)

    if len(top_list) >= 1:
        most_close = top_list[1]
    else:
        most_close = "";

    central_list = betweenness_centrality(local_graph, endpoints=False)
    top_list = select_highest(central_list)

    if len(top_list) >= 1:
        most_between = top_list[1]
    else:
        most_between = "";
            
    # Drawing code
    print "Preparing for drawing..."
    initpos = nx.shell_layout(local_graph)
    pos = nx.spring_layout(local_graph, fixed=case_law_nodes, pos=initpos, iterations=500)
    print "Look I have drawn some circles and lines...\n(Close window to continue.)"
    nx.draw_networkx_nodes(local_graph, pos, node_color='b', node_size=50, with_labels=True, label="Law Node")
    nx.draw_networkx_nodes(local_graph,pos,nodelist=case_law_nodes,node_size=50,node_color='r', label="Case Law Node")
    nx.draw_networkx_nodes(local_graph,pos,nodelist=[current_node],node_size=200,node_color='g', label="Current Law Node")
    nx.draw_networkx_nodes(local_graph,pos,nodelist=[most_close],node_size=210,node_color='y', label="Closest Law Node (closeness)")
    nx.draw_networkx_nodes(local_graph,pos,nodelist=[most_between],node_size=200,node_color='c', label="Closest Law Node (betweenness)")
    nx.draw_networkx_edges(local_graph, pos, edgelist=local_graph.edges(), arrows=True, label="Cites")
    plt.axis('off')
    plt.legend()
    plt.savefig('ego_graph.png')
    plt.show()

parser = argparse.ArgumentParser(description='Tool for building network based on edges')
parser.add_argument("-c", "--case",
                        action="store", metavar="X", dest="caselaw", default="caselaw.edges",
                        help="File X containing edges for case law")
parser.add_argument("-l", "--law",
                        action="store", metavar="X", dest="legislation",
                        help="File X containing edges for legislation")
args = parser.parse_args()

# Compile the regex for finding out which type of document the node is
case_law_regex = re.compile('<http://rechtspraak.nl')
law_regex = re.compile('<http://doc.metalex.eu')

build_network()