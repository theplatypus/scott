import os
import shutil

import pytest

from harness import run_cfi_rigid_py, run_cfi_rigid_rs


@pytest.mark.canonization
def test_cfi_rigid_legacy():
	max_n = int(os.getenv("SCOTT_TEST_CFI_N", "16"))
	assert run_cfi_rigid_py("py", max_n=max_n)


@pytest.mark.canonization
def test_cfi_rigid_nx():
	try:
		import networkx  # noqa: F401
	except Exception:
		pytest.skip("networkx not available")
	max_n = int(os.getenv("SCOTT_TEST_CFI_N", "16"))
	assert run_cfi_rigid_py("nx", max_n=max_n)


@pytest.mark.canonization
def test_cfi_rigid_rs():
	if shutil.which("cargo") is None:
		pytest.skip("cargo not available")
	max_n = int(os.getenv("SCOTT_TEST_CFI_N", "16"))
	assert run_cfi_rigid_rs(max_n=max_n, release=False)
