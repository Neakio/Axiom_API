# ------------------------------ PACKAGES ------------------------------
# Standard imports
import requests


# ------------------------------ MAIN ------------------------------
response = requests.get("http://checkip.amazonaws.com/", timeout=30)
public_ip = response.text.strip()

tags_metadata = [
    {
        "name": "scans",
        "description": "Operations for scans.",
        "externalDocs": {
            "description": "Scans external docs",
            "url": f"http://{public_ip}:8000/docs/scans",
        },
    },
    {
        "name": "docs",
        "description": "API documentation",
    },
]

description = f"""


## Scans
_(see <a href="http://{public_ip}:8000/docs/scans" target="_self">here</a> for endpoint usage)_


You can **perform scans** using different tool. There is three different methods :
* Scan a **single domain**.
* Scan **multiple domains** within a file.
"""
