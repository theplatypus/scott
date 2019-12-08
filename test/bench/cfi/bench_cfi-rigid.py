import tracemalloc
tracemalloc.start()

import scott as st 
from os import walk
import pandas as pd
import time 

import concurrent
from joblib import Parallel, delayed
import multiprocessing
num_cores = multiprocessing.cpu_count()


SIZE_MIN = 250
SIZE_MAX = 275
DIR_PATH = "./data/isotest/cfi-rigid-t2-dot/"

(dirpath, dirnames, filenames) = next(walk(DIR_PATH))
results = []
checker = {}

for filename in filenames :
	if ".dot" in filename :
		tokens = filename.split("-")
		problem_size = tokens[3]
		if int(problem_size) <= SIZE_MAX and int(problem_size) >= SIZE_MIN :
			print("Working on %s..." % (filename))
			task_id = "%s-%s" % (problem_size, tokens[4])
			graph_id = tokens[5]
			g = st.parse.from_dot(file_path="%s%s" % (dirpath, filename))[0]
			start = time.time()
			res = str(st.canonize.to_cgraph(g, candidate_rule="$label > $degree > graph.n_degree(id_node, 1) > graph.n_degree(id_node, 2)"))
			elapsed = time.time() - start
			valid = False
			if task_id in checker :
				valid = bool(checker[task_id] == res)
			else :
				checker[task_id] = res
				valid = True
			#r.set('%s_%s' % (task_id, graph_id), "\t".join([str(problem_size), str(len(g.V)), str(len(g.E)), task_id, graph_id, str(elapsed), str(valid), str(len(res)), res]))
			print("\t".join([str(problem_size), str(len(g.V)), str(len(g.E)), task_id, graph_id, str(elapsed), str(valid), str(len(res)), res]))
			results.append([str(problem_size), str(len(g.V)), str(len(g.E)),task_id, graph_id, str(elapsed), str(valid), str(len(res)), res])



df = pd.DataFrame(results, columns = ['problem_size', 'nodes', 'edges', 'task_id', 'graph', 'time', 'valid', 'res_size', 'canonization'])

df.to_csv("results_cfi_0-275.csv") 


g = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot")[0]
h = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot")[0]

c = st.canonize.to_cgraph(g, candidate_rule="$degree > $label")
c2 = st.canonize.to_cgraph(h, candidate_rule="$degree > $label")

str(c) == str(c2)



d1 = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-r2-dot/216-432-01-A.dot")[0]
d2 = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-r2-dot/216-432-02-A.dot")[0]
d3 = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-r2-dot/216-432-03-B.dot")[0]
d4 = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-r2-dot/216-432-04-B.dot")[0]
d5 = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-r2-dot/216-432-05-C.dot")[0]
d6 = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-r2-dot/216-432-06-C.dot")[0]
d7 = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-r2-dot/216-432-07-D.dot")[0]
d8 = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-r2-dot/216-432-08-D.dot")[0]

c1 = st.canonize.to_cgraph(d1, candidate_rule="$degree > $label")
c2 = st.canonize.to_cgraph(d2, candidate_rule="$degree > $label")
c3 = st.canonize.to_cgraph(d3, candidate_rule="$degree > $label")
c4 = st.canonize.to_cgraph(d4, candidate_rule="$degree > $label")
c5 = st.canonize.to_cgraph(d5, candidate_rule="$degree > $label")
c6 = st.canonize.to_cgraph(d6, candidate_rule="$degree > $label")
c7 = st.canonize.to_cgraph(d7, candidate_rule="$degree > $label")
c8 = st.canonize.to_cgraph(d8, candidate_rule="$degree > $label")
