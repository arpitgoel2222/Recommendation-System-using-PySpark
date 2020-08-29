from pyspark import SparkContext
import json
import sys
import time
from queue import *
import pyspark
import itertools
from itertools import combinations
import collections

s = pyspark.SparkConf().setAppName('HW4')
sc = SparkContext(conf = s)
sc.setLogLevel("Error")

threshold = int(sys.argv[1])
input_file = sys.argv[2]
output1 = sys.argv[3]
output2 = sys.argv[4]

def remove_component(remainder_graph, component):
	for v in component[0]:
		del remainder_graph[v]

	for node in remainder_graph.keys():
		adj_list = remainder_graph[node]
		for vertex in component[0]:
			if(vertex in adj_list):
				adj_list.remove(node[1])
		remainder_graph[node] = adj_list		

	return remainder_graph		

def compute_connected_components(adjacent_vertices):
    connected_components= []
    remainder_graph = adjacent_vertices

    while(checkempty(remainder_graph) == False):
        vertices= []
        for key, value in remainder_graph.items():
            vertices.append(key)
        vertices = list(set(vertices))
        root = vertices[0]
        visited=[]
        edges= []
        queue = Queue(maxsize = len(vertices))
        queue.put(root)
        visited.append(root)
        while(queue.empty()!= True):
            node = queue.get()
            children = adjacent_vertices[node]
            for i in children:
                if(i not in visited):
                    queue.put(i)
                    visited.append(i)
                pair = sorted((node,i))
                if(pair not in edges):
                    edges.append(pair)
        comp_g = (visited, edges)
        connected_components.append(comp_g)
        remainder_graph= remove_component(remainder_graph, comp_g)
    return connected_components
            
def build_adjacency_matrix(connected_components):
    result = {}
    for c in connected_components:
        for edge in c[1]:
            if(edge[0] in result.keys()):
                result[edge[0]].append(edge[1])
            else:
                result[edge[0]]= [edge[1]]
            if(edge[1] in result.keys()):
                result[edge[1]].append(edge[0])
            else:
                result[edge[1]]= [edge[0]]
    return result

def remove_edge(adjacency_matrix, edge_to_remove):
    if(edge_to_remove[0] in adjacency_matrix.keys()):
        l = adjacency_matrix[edge_to_remove[0]]
        if(edge_to_remove[1] in l):
            l.remove(edge_to_remove[1])

    if(edge_to_remove[1] in adjacency_matrix.keys()):
        l = adjacency_matrix[edge_to_remove[1]]
        if(edge_to_remove[0] in l):
            l.remove(edge_to_remove[0])
    return adjacency_matrix


def checkempty(av):
    if len(av) !=0:
        for x in av.keys():
            alist = av[x]
            if len(alist)==0:
                pass
            else:
                return False
        return True

        
def getallbusinesses(x):
    res= []
    #Get all the combinations of the edges possible in the graph
    pairs = itertools.combinations(x[1], 2)
    for i in pairs:
        i = sorted(i)
        #Make a tuple along with the edge(which is the user id) and business id
        res.append(((i[0], i[1]), [x[0]]))
    return res


def calculate_betweenness(root, edges_list, vertices):
    q = Queue(maxsize = vertices)
    q.put(root)
    visited, levels, parents, weights = [], {}, {}, {}
    weights[root] = 1
    visited.append(root)
    levels[root] = 0
    
    while not q.empty():
        node = q.get()
        child = edges_list[node]
        for i in child:
            if (i in visited):
                if (i != root):
                    parents[i].append(node)
                    if (levels[i] - 1 == levels[node]):
                        weights[i] += weights[node]
            else:
                q.put(i)
                levels[i] = levels[node] + 1
                parents[i], weights[i] = [node], weights[node]
                visited.append(i)

    ov = list()
    rev_order = []
    count = -1
    for i in visited:
        count = count + 1
        ov.append((i, count))
    nVs = {}
    reverse_order = sorted(ov, key=(lambda x: x[1]), reverse=True)

    for i in reverse_order:
        nVs[i[0]] = 1
        rev_order.append(i[0])

    bVs = {}
    for j in range(len(rev_order)):
        if (rev_order[j] != root):
            t_w = 0
            for i in parents[rev_order[j]]:
                if (levels[i] == levels[rev_order[j]] - 1):
                    t_w += weights[i]
            for i in parents[rev_order[j]]:
                if (levels[i] == levels[rev_order[j]] - 1):
                    src, dest = rev_order[j], i
                    if src >= dest:
                        p = (dest,src)
                        pair = tuple(p)
                    else:
                        p = (src,dest)
                        pair = tuple(p)
                    if (pair in bVs.keys()):
                        bVs[pair] += float(nVs[src] * weights[dest] / t_w)
                    else:
                        bVs[pair] = float(nVs[src] * weights[dest] / t_w)
                    nVs[dest] += float(nVs[src] * weights[dest] / t_w)

    bList = list()
    for k, v in bVs.items():
        bList.append([k, v])
    return bList

    
    
def getvertices(node, edges):
    av = []
    #This function get all the vertices adjacent to each other
    #Iterate each edge and check if one of tbe vertice is same,get the other one
    for edge in edges:
        if edge[0] == node:
            av.append(edge[1])
        elif edge[1] == node:
            av.append(edge[0])
    return list(set(av))

#Get the data and grup it by business id and user id
data= sc.textFile(input_file).map(lambda x : x.split(',')).filter(lambda x: x[0]!= "user_id").map(lambda x: (x[1], [x[0]])).reduceByKey(lambda x,y: x+y)

#Get all the combinations of business id of a user id anf group it together
#Filter it on the basis of threshold and get the first set
users = data.flatMap(lambda x: getallbusinesses(x)).reduceByKey(lambda x,y: x+y).filter(lambda x: len(x[1]) >= threshold).map(lambda x: x[0])

#Get the number of nodes/users present in the graph
nodes = users.flatMap(lambda x: [(x[0]),(x[1])]).distinct()
no_of_nodes = len(nodes.collect())

#Get all the edges present in the graph
edges = users.map(lambda x: (x[0], x[1]))
edge_list = edges.collect()


#Get vertices adjacent to each other
vert = nodes.map(lambda x: (x, getvertices(x, edge_list))).collectAsMap()
print(len(vert))
#Task1
#calculate betweenness in the graph using the vertices
#Divide the betweenness by 2 as it is a directed graph and sort it accordingly after getting the pair of tuple
btw = nodes.flatMap(lambda x: calculate_betweenness(x, vert, no_of_nodes)).reduceByKey(lambda x,y: (x+y)).map(lambda x: (x[0], float(x[1]/2))).sortByKey().map(lambda x: (x[1],x[0])).sortByKey(ascending=False).map(lambda x: (x[1],x[0]))

#Dump it
with open(output1,"w") as f:
    for pair in btw.collect():
        f.write(str(pair[0]) + ", " + str(pair[1]) + "\n")
        

#Task2
#Take the edge with highest betweenness and remove it according to girvan newman
edge_to_remove = btw.take(1)[0][0]
    
no_of_edges = len(edge_list)
    
adjacency_matrix = vert.copy()

connected_components = compute_connected_components(adjacency_matrix)

modularity= 0

for c in connected_components:
    count = 0
    for i in c[0]:
        for j in c[0]:
            count = 0;
            adj_list = vert[str(i)]
            if(j in adj_list):
                count=1

            ki = len(vert[i])
            kj = len(vert[j])

            modularity += count - ((ki*kj)/(2*no_of_edges))

modularity= modularity/(2*no_of_edges)
    
adjacency_matrix= vert.copy()
    
highest_modularity = -1
communities=[]
count=0
    
while(1):
    adjacency_matrix = remove_edge(adjacency_matrix, edge_to_remove)
        
    connected_components = compute_connected_components(adjacency_matrix)
        
    for c in connected_components:
        counter = 0
        for i in c[0]:
            for j in c[0]:
                counter = 0;
                adj_list = vert[str(i)]
                if(j in adj_list):
                    counter=1

                ki = len(vert[i])
                kj = len(vert[j])
    
                modularity += counter - ((ki*kj)/(2*no_of_edges))

    modularity= modularity/(2*no_of_edges)

    adjacency_matrix= build_adjacency_matrix(connected_components)

    temp=[]
        
    for i in adjacency_matrix.keys():
        temp.append(i)
        
    temp = list(set(temp))
        
    vert_rdd = sc.parallelize(temp)
        
    betweenness_temp = vert_rdd.flatMap(lambda x: calculate_betweenness(x, adjacency_matrix, no_of_nodes))\
    .reduceByKey(lambda x,y: (x+y)).map(lambda x: (x[0], float(x[1]/2))).sortByKey().map(lambda x: (x[1],x[0])).sortByKey(ascending=False).map(lambda x: (x[1],x[0]))
        
    edge_to_remove = betweenness_temp.take(1)[0][0]
    
    if(modularity >= highest_modularity):
        highest_modularity = modularity;communities = connected_components

    count += 1
    if(count == 50):
        break

sorted_communities= []
print(len(communities))
for community in communities :
    item = sorted(community[0])
    sorted_communities.append((item,len(item)))

sorted_communities.sort()
sorted_communities.sort(key = lambda x:x[1])

f = open(output2, 'w')
i = 0
for community in sorted_communities:
    if(i == 0):
        i = 1
    else:
        f.write("\n")
    s = str(community[0]).replace("[","").replace("]","")
    f.write(s)
    

