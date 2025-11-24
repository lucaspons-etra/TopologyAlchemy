import base64
import json
from base_notifier import Notifier
import logging
from pathlib import Path
from topology import Network
from aiohttp import ClientSession, ClientTimeout
import aiofiles

class ApiNotifier(Notifier):
    @classmethod
    def name(cls) -> str:
        return "ApiNotifier"
    
    def required_parameters(self) -> dict:
        return {
            "api_endpoint": None,
            "api_key": "",
            "api_token": "",
            "timeout": 30,  # Default timeout in seconds,
            "method": "GET",  # HTTP method
            "body_template": {},
            "binary_data": False
        }

    async def _notify_impl(self, network: Network, data, logger: logging.Logger, params: dict = {}) -> (bool, object):
        api_endpoint = params.get("api_endpoint").format(network=network, params=params)
        api_key = params.get("api_key")
        api_token = params.get("api_token")
        timeout = params.get("timeout", 30)
        body_template = params.get("body_template")
        use_body = params.get("use_body", True)
        method = params.get("method", "GET").upper()
        binary_data = params.get("binary_data", False)
        
        headers = {
            "X-Auth-Token": api_token,
            "X-User-ID": api_key,
            "Content-Type": "application/json"
        }
        # Read the exported file content. Accept Path, PosixPath or string path-like values.
        
        # Prepare the request body
        if use_body:
            if body_template and isinstance(body_template, dict):
                # If a string template is provided, format it
                try:
                    body = json.loads(body_template).format(network=network, params=params, data=json.loads(data))
                except Exception:
                    # Fall back to raw template string if formatting fails
                    body = body_template
            elif body_template and isinstance(body_template, str):
                # Non-string template (e.g. dict) - convert to string
                try:
                    body = json.loads(body_template.format(network=network, params=params, data=json.dumps(data)))
                except Exception:
                    # Fall back to raw template string if formatting fails
                    body = body_template
            else:
                body = body_template

        bytes_body = None
        if binary_data:
            # If binary data is to be sent, adjust headers and build raw bytes body
            headers["Content-Type"] = "application/octet-stream"
            # Determine bytes from available 'body' or fallback to 'data'
            source = None
            if 'body' in locals():
                source = body
            else:
                source = data

            if isinstance(source, (bytes, bytearray)):
                bytes_body = bytes(source)
            elif isinstance(source, (dict, list)):
                try:
                    bytes_body = json.dumps(source).encode('utf-8')
                except Exception:
                    bytes_body = str(source).encode('utf-8')
            elif isinstance(source, str):
                bytes_body = source.encode('utf-8')
            else:
                bytes_body = str(source).encode('utf-8')
        # Send the data to the API endpoint
        try:
            async with ClientSession(timeout=ClientTimeout(total=timeout)) as session:
                method_func = getattr(session, method.lower(), None)
                if not method_func:
                    logger.error(f"HTTP method {method} is not supported.")
                    return False    

                # Build request kwargs depending on body/binary selection
                request_kwargs = {"headers": headers}
                if binary_data:
                    request_kwargs["data"] = bytes_body
                else:
                    if use_body:
                        # Prefer json= for dict/list bodies, otherwise send as data (string)
                        if isinstance(body, (dict, list)):
                            request_kwargs["json"] = body
                        else:
                            if body is not None:
                                if isinstance(body, (bytes, bytearray)):
                                    request_kwargs["data"] = bytes(body)
                                else:
                                    request_kwargs["data"] = str(body)

                async with method_func(api_endpoint, **request_kwargs) as response:
                    if 200 <= response.status < 300:
                        logger.info(f"Successfully notified API at {api_endpoint}")
                        # Try to parse JSON, otherwise return text
                        try:
                            return (True, await response.json())
                        except Exception:
                            return (True, await response.text())
                    else:
                        txt = await response.text()
                        logger.error(f"API notification failed with status {response.status}: {txt}")
                        return (False, txt)
        except Exception as e:
            logger.error(f"Error during API notification: {e}")
            return (False, str(e))