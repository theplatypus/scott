class CGraph :
	"""
		Compressed Graph
		================

		A Graph under the Neuwick form, expressed as a 1D string
	"""
	
	def check_graph(value: str) -> bool :
		"""
			TODO
		"""
		return True
	
	def __init__(self, value:str):
		#assert check_graph(value)
		self.value = value
	
	def __str__(self):
		return self.__repr__()
	
	def __repr__(self):
		return self.value
	
	def is_equal(self, other) -> bool :
		a = str(self)
		b = str(other)
		for i in range(0, len(a)):
			if (a[i] != b[i]):
				print("Mismatch at char %i : expected '%s', got '%s'" % (i, a[i], b[i]))
				return False
		return True
