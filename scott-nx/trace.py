import json
import os


def _enabled() -> bool:
	return os.getenv("SCOTT_TRACE") == "1"


def emit(event: str, **fields) -> None:
	if not _enabled():
		return
	parts = [event]
	for key, value in fields.items():
		parts.append(f"{key}={json.dumps(value, sort_keys=True, separators=(',', ':'))}")
	print("TRACE " + " ".join(parts))
