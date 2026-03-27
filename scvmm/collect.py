import logging
from typing import Optional

import winrm
import json

from scvmm.models import WinRMConfig
from scvmm.constants import SCVMM_DATA_COLLECTION_SCRIPT

logger = logging.getLogger(__name__)

def collect_scvmm_data(
    hostname: str,
    username: str,
    password: str,
    winrm_config: Optional[WinRMConfig] = None,
):
    """Collect SCVMM data via WinRM.

    Args:
        hostname: SCVMM server hostname
        username: Authentication username
        password: Authentication password
        winrm_config: Optional WinRM connection configuration

    Returns:
        Dictionary containing SCVMM clusters and VMs data
    """
    logger.info(f"Collecting data from SCVMM server at {hostname} with username {username}")

    # Use provided config or create defaults
    if winrm_config is None:
        url = f"http://{hostname}:5985/wsman"
        transport = "ntlm"
        logger.debug("Using default WinRM configuration (HTTP, port 5985, NTLM)")
    else:
        url = f"{winrm_config.protocol}://{hostname}:{winrm_config.port}{winrm_config.path}"
        transport = winrm_config.transport
        logger.debug(
            f"Using custom WinRM configuration: {winrm_config.protocol}://{hostname}:"
            f"{winrm_config.port}{winrm_config.path}, transport={transport}"
        )

    session = winrm.Session(url, auth=(username, password), transport=transport)

    ps_script = SCVMM_DATA_COLLECTION_SCRIPT

    try:
        result = session.run_ps(ps_script)
        if result.status_code != 0:
            logger.error(f"PowerShell script execution failed with status code {result.status_code}: {result.std_err.decode()}")
            raise Exception(f"PowerShell script execution failed: {result.std_err.decode()}")
        
        data = json.loads(result.std_out.decode())
        logger.info("Successfully collected data from SCVMM server")
        #logger.debug(f"Raw data collected from SCVMM server: {data}")
        return data
    except Exception as e:
        logger.error(f"Error collecting data from SCVMM server: {e}")
        raise
