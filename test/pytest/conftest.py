import os
import sys

TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TEST_DIR)
for path in (TEST_DIR, REPO_ROOT):
	if path not in sys.path:
		sys.path.insert(0, path)
