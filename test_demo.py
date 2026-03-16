"""
test_demo.py — Diagnostic integration script bypassing the browser.

Usage:
    python test_demo.py

Requires the server to be running at localhost:8000.
"""

import json
import requests

API_URL = "http://localhost:8000/analyse"
SAMPLE_FILE = "data/sample_novacast.txt"


def main():
    print(f"Sending '{SAMPLE_FILE}' to {API_URL} …\n")

    with open(SAMPLE_FILE, "rb") as fh:
        response = requests.post(
            API_URL,
            files={"files": (SAMPLE_FILE.split("/")[-1], fh, "text/plain")},
            timeout=120,
        )

    print(f"HTTP {response.status_code}\n")

    if response.ok:
        print(json.dumps(response.json(), indent=2))
    else:
        print("Error response:")
        print(response.text)


if __name__ == "__main__":
    main()
