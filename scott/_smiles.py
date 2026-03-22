"""SMILES to MOL block conversion. Requires rdkit or pybel."""


def to_mol_block(smiles):
	try:
		import pybel
		mol = pybel.readstring("smi", smiles)
		mol.make3D()
		return mol.write("sdf")
	except ModuleNotFoundError:
		pass

	try:
		from rdkit import Chem
		mol = Chem.MolFromSmiles(smiles)
		mol = Chem.AddHs(mol)
		return Chem.MolToMolBlock(mol)
	except Exception:
		pass

	raise ImportError(
		"SMILES parsing requires rdkit or pybel. "
		"Install with: pip install scott[rdkit]"
	)
