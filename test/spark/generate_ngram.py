import os
import zlib

import scott as sct

sc = spark.sparkContext

WINDOW_SIZE = 5

FRAGMENT_SIZE = 1

OUTPUT_FOLDER = "./W_" + str(WINDOW_SIZE) + "F_" + str(FRAGMENT_SIZE)

def safe_enumeration(mol):
	try:
		if mol is None:
			return ""
		else :
			return sct.fragmentation.enum_ngrams(mol, 
				window_size = WINDOW_SIZE, 
				fragment_size = FRAGMENT_SIZE)
	except Exception as e:
		print("Unable to get a enum_ngrams : " + str(e))
		return ""

for dirname, dirnames, filenames in os.walk('./data/batch/xml/gz/'):
	for filename in filenames:
		path = os.path.join(dirname, filename)
		print("PROCESSING " + filename)
		try:
			compounds = sct.parse.from_pubchem_xml(file_path = path, ignore_hydrogens = True)
			compoundsRDD = sc.parallelize(compounds)
			print("parsed")
			print(str(len(compounds)) + " compounds parsed from " + filename)
			ngrams = compoundsRDD \
					.map(safe_enumeration) \
					.map(lambda ngrams : str(ngrams))
			print(ngrams)
			ngrams.saveAsTextFile(OUTPUT_FOLDER + "/NGRAMS/" + filename)
		except Exception as e:
			print(e)

