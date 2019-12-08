#from setuptools import setup, find_packages
from distutils.core import setup
from Cython.Build import cythonize
from distutils.extension import Extension

extensions = [
	Extension("scott", ["scott/structs/node.py", "scott/structs/edge.py", "scott/structs/tree.py", 
	"scott/structs/graph.py", "scott/structs/cgraph.py", "scott/canonize.py",
	"scott/compression.py", "scott/parse.py", "scott/export.py", "scott/fragmentation.py"],
		include_dirs=[],
		libraries=[],
		library_dirs=[])
]

setup(
	name='scott',
	version='1.0',
	description='Structure Canonization w/ Ordered Tree Translation',
	#packages=find_packages(),
	ext_modules = cythonize(extensions)
)
