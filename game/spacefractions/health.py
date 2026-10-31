"""Health check endpoint used by k8s probes (SF-OPS). Not part of the desktop UI."""

import json


def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    print(json.dumps(health()))
