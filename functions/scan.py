# ------------------------------ PACKAGES ------------------------------
# General packages
import asyncio
import subprocess
from requests import exceptions, post
from datetime import datetime

# Internal packages
import functions.utils as utils


# ------------------------------ PROCESSING ------------------------------
async def processing(q, domain, output="", uuid="", client_ip=""):
    """Prepare API request for the scan and call it

    Args:
        q (str): Profile/Workflow chosen
        domain (str): Input filename
        output (str, optional): Output type. Default empty.
        uuid (str, optional): Job UUID, it will be used to send a response and as a str in the filename. Default empty.
        client_ip (str, optional): Requester IP address used to send result. Default empty.
    """
    utils.api_log(
        f"API call received. Start processing for {domain}. The uuid is {uuid} and client_ip is {client_ip}"
    )
    current_datetime = datetime.now().strftime("%Y-%m-%d")
    file = (
        f"{current_datetime}_{domain}"
        if not uuid
        else f"{current_datetime}_{domain}_{uuid}"
    )
    utils.api_log(f"Output filename: {file}")

    code = await scan(input=domain, output=file, profile=(q.value), format=output)

    status = "completed" if code == 0 else "error"

    if uuid and client_ip:
        await notify(status, file, uuid, client_ip)
    return status


# ------------------------- Main scan function -------------------------
async def scan(input, output, profile=None, format=""):
    """Run axiom-scan based on arguments provided

    Args:
        input (str): Input filename
        output (str): Output filename
        profile (str, optional): Single scan case. Defaults to None.
        format (str, optional): Output type. Default empty.

    Returns:
        code: return error/success code
    """
    if format is None:
        format = ""
    tool = None
    outype = None
    count = 0
    utils.axiom_log("-----------------------")
    match profile:
        case "ip_list":
            tool = "dnsx -re"
        case "dns_list":
            tool = "amass"
            return
        case "web_list":
            tool = "gau"
        case "waf_check":
            tool = "wafw00f"
            utils.add_https_to_each_line(input)
        case "ssl_check":
            tool = "testssl"
            utils.add_https_to_each_line(input)
        case "http_check":
            tool = "httpx -fr -sc -location -title -method"
        case "dns_check":
            tool = "whois"
            return
        case "web_scan":
            tool = "aquatone"
        case "port_scan":
            tool = "nmap -sV -sC"
        case _:
            utils.axiom_log(f"Invalid profile: {profile}, discarding scan")
            utils.axiom_log("-----------------------")
            return 1
    utils.axiom_log(f"Tool used: {tool}")
    match format:
        case "" | "txt":
            outype = "-o"
        case "json":
            outype = "-oJ"
        case "html":
            outype = "-oH"
        case _:
            utils.axiom_log(f"Invalid format: {format}, discarding scan")
            utils.axiom_log("-----------------------")
            return 1
    utils.axiom_log(f"Output format: {outype}")
    count = 0
    # Determine the file type and count the number of lines, entries, or rows
    if ".json" in input:
        count = utils.count_entries_in_json(f"/var/tmp/scan_input/{input}")
    elif ".csv" in input:
        count = utils.count_rows_in_csv(f"/var/tmp/scan_input/{input}")
    elif ".txt" in input:
        count = utils.count_lines_in_txt(f"/var/tmp/scan_input/{input}")
    else:
        utils.axiom_log(f"Incorrect input filename : {input}")

    with open(f"/var/tmp/scan_input/{input}", "r") as file:
        lines_list = [line.strip() for line in file.readlines()]
    await utils.instances_needed(count)  # Start needed instances

    starttime = datetime.now().strftime("%H:%M:%S")
    await axiom(tool, outype, input, f"/var/tmp/scan_output/{output}", profile)
    endtime = datetime.now().strftime("%H:%M:%S")

    utils.save_to_bucket(output)

    length = f"{starttime} - {endtime}"
    utils.scanner_json(lines_list, tool, length)
    utils.stop_instances()
    subprocess.run(
        [f"rm /var/tmp/scan_input/{input}"],
        shell=True,
    )
    utils.axiom_log("-----------------------")
    return 0


async def notify(status, file, uuid, client_ip):
    try:
        callback_url = f"http://{client_ip}/callback"
        response = post(
            callback_url, json={"status": status, "file": file, "uuid": uuid}
        )
        response.raise_for_status()
    except exceptions.RequestException as e:
        utils.api_log(f"Failed to notify client IP: {client_ip}, error: {e}")


async def axiom(module, outype, input, output, profile):
    command = f"axiom-scan /var/tmp/scan_input/{input} -m {module} {outype} {output}"
    utils.axiom_log(f"Start of {profile} for /var/tmp/scan_input/{input}")
    utils.axiom_log(f"axiom-scan /var/tmp/scan_input/{input} -m {module} -o {output}")
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = await asyncio.get_event_loop().run_in_executor(
        None, process.communicate
    )
    if "exiting" in stdout:
        utils.axiom_log("Command failed with error")
        utils.axiom_log(
            f"End of {profile} using {module}, see error at: /var/log/scanner/axiom.log"
        )
        return 1
    if process.returncode != 0:
        utils.axiom_log("Command failed with error: ")
        utils.axiom_log(stderr)
        utils.axiom_log(
            f"End of {profile} using {module}, see error at: /var/log/scanner/axiom.log"
        )
        utils.stop_instances()
        return 1
    utils.axiom_log("Command output:")
    utils.axiom_log(stdout)
    utils.axiom_log(
        f"End of {profile} using {module}, succesfull result: /var/tmp/scan_output/{output}\n"
    )
    return 0
