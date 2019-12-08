#!/bin/python
from os import walk
import os
import random

INPUT_PATH = "./bliss/"
OUTPUT_PATH = "./bliss-permut/"
PERMUTATIONS_NUMBER = 12

(dirpath, tasks, filenames) = next(walk(INPUT_PATH))

for task in tasks : 
	(dirpath, dirnames, filenames) = next(walk("%s%s" % (INPUT_PATH, task)))
	dirtask = "%s%s/" % (OUTPUT_PATH, task)
	if not os.path.exists(dirtask):
		os.makedirs(dirtask)

	for i in range(1, PERMUTATIONS_NUMBER):
		for filename in filenames :
			with open("%s/%s" % (dirpath, filename)) as f:
				content = []
				lines = f.readlines()
				#print(lines)
				header = lines.pop(0)
				content.append(header)
				#print(header)
				(vertices, edges) = (int(header.split(' ')[2]), int(header.split(' ')[3]))
				print(str(vertices) + " vertices found")
				indexes = [id_node for id_node in range(1, vertices+1)]
				print(indexes)
				random.shuffle(indexes)
				for line in lines : 
					tokens = line.split(' ')
					print(tokens)
					tokens[1] = str(indexes[int(tokens[1])-1])
					tokens[2] = str(indexes[int(tokens[2])-1])
					content.append(' '.join(tokens))
				out_file = open("%s%s-%s" % (dirtask, filename, str(i)), "w+") 
				out_file.write('\n'.join(content)) 
				out_file.close() 
