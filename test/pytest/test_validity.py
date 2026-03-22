import shutil

import pytest

from harness import run_validity_py, run_validity_rs


@pytest.mark.unit
def test_validity_legacy():
	assert run_validity_py("py")



@pytest.mark.unit
def test_validity_rs():
	if shutil.which("cargo") is None:
		pytest.skip("cargo not available")
	assert run_validity_rs(release=False)
