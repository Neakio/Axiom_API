# ------------------------------ PACKAGES ------------------------------
# Standard imports
import asyncio
from dotenv import load_dotenv

# Third-party libraries
from fastapi import (
    Query,
    File,
    UploadFile,
    Depends,
    Request,
    APIRouter,
)
from fastapi.responses import JSONResponse

# Local imports
import functions.utils as utils
import functions.scan as scan
import endpoints.security as security

# Database
import postgres.models as models


################################## [ INIT ] ##################################
load_dotenv()
profiles, formats, workflows = utils.load_json()
ValidprofilesEnum = utils.create_enum("ValidprofilesEnum", profiles)
ValidformatsEnum = utils.create_enum("ValidformatsEnum", formats)
ValidworkflowsEnum = utils.create_enum("ValidworkflowsEnum", workflows)

router = APIRouter(prefix="/scans", tags=["scans"])

scan_queue = asyncio.Queue()

################################## [ FUNCTION ] ##################################


async def process_queue():
    """Continuously monitor the queue for new scan jobs."""
    while True:
        job = await scan_queue.get()
        await handle_scan(job)
        scan_queue.task_done()


async def handle_scan(job):
    """Process each scan job one at a time."""
    code = await scan.processing(
        job["q"], job["domain"], job["output"], job["uuid"], job["client_ip"]
    )
    if code == "completed":
        utils.api_log(f"Scan for {job['domain']} completed successfully.")
    else:
        utils.api_log(f"Scan for {job['domain']} failed.")


################################### [ API ] ##################################
# ------------------------------ Scan Execution ------------------------------


# API endpoint for unique scan
@router.get("/")
async def single_scan(
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    q: ValidprofilesEnum = Query(..., description="Must be one of the valid values."),
    domain: str = Query(..., min_length=1, description="Cannot be empty"),
    output: ValidformatsEnum = Query(
        None, description="Optional format. Must be one of the valid values."
    ),
    uuid: str = Query(None, min_length=1, description="Optional to notify end of scan"),
):
    utils.api_log(
        f"Single scan requested by {current_user.email} (IP : {request.client.host}). Domain is {domain} and case is {q.value}"
    )
    filename = f"{domain}.txt"
    with open(
        f"/var/tmp/scan_input/{filename}", "w", encoding="utf-8"
    ) as f:  # Save single input as file in input folder
        f.write(f"{domain}\n")
    utils.api_log(f"Temporary file saved as /var/tmp/scan_input/{filename}")

    request_data = {
        "domain": filename,
        "q": q,
        "output": output,
        "uuid": uuid,
        "client_ip": request.client.host,
    }

    # Append the job to the in-memory queue
    await scan_queue.put(request_data)
    utils.api_log("Job sent to queue")

    # Return immediately to the requester
    return JSONResponse({"message": "Job sent to queue"})


# API endpoint for file scan
@router.post("/")
async def file_scan(
    request: Request,
    current_user: models.User = Depends(security.get_current_user),
    q: ValidprofilesEnum = Query(..., description="Must be one of the valid values."),
    domain: UploadFile = File(...),
    output: ValidformatsEnum = Query(
        None, description="Optional format. Must be one of the valid values."
    ),
    uuid: str = Query(None, min_length=1, description="Optional to notify end of scan"),
):
    contents = await domain.read()  # Wait & Read uploaded file
    utils.api_log(
        f"File scan requested by {current_user.email} (IP : {request.client.host}). File is here /var/tmp/scan_input/{domain.filename} and case is {q}"
    )
    with open(f"/var/tmp/scan_input/{domain.filename}", "wb") as f:
        f.write(contents)
    request_data = {
        "domain": domain.filename,
        "q": q,
        "output": output,
        "uuid": uuid,
        "client_ip": request.client.host,
    }
    await scan_queue.put(request_data)
    utils.api_log("Job sent to queue")

    # Return immediately to the requester
    return JSONResponse({"message": "Job sent to queue"})
