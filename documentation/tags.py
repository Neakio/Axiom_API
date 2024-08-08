# ------------------------------ PACKAGES ------------------------------
# General packages
import requests


# ------------------------------ MAIN ------------------------------
response = requests.get("http://checkip.amazonaws.com/")
public_ip = response.text.strip()

tags_metadata = [
    {
        "name": "users",
        "description": "Operations with users. The **login** logic is also here.",
        "externalDocs": {
            "description": "Users external docs",
            "url": f"http://{public_ip}:8000/docs/users",
        },
    },
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

## Users
_(see <a href="http://{public_ip}:8000/docs/users" target="_self">here</a> for endpoint usage)_


The admin will be able to :
* **Create users**.
* **Read users**.
* **Update users** (surname, firstname, email).
* **Delete users**.
* **Activate/Deactivate user**.
* **Reset users' password** (_not implemented_).

Each user will be able to : 
* **Change own password** (_not implemented_).
* **Reset own password** (_not implemented_).
* **Retrieve JWT Token**.
"""
