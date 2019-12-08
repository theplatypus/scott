
import sys

def to_mol_block(smiles: str) -> str:
	
	try:
		import pybel
		mol = pybel.readstring("smi", smiles)
		mol.make3D()
		return mol.write('sdf')
	except ModuleNotFoundError as error:
		try:
			from rdkit import Chem
			mol = Chem.MolFromSmiles(smiles)
			mol = Chem.AddHs(mol)
			return Chem.MolToMolBlock(mol)
		except expression as identifier:
			print(error)
			print("try to install rdkit/pybel from packages, or use anaconda (see Readme.MD)")
			return ""
