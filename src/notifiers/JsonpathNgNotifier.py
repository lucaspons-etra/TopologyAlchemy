import json
import logging


from base_notifier import Notifier
from topology import Network
import jsonpath_rw_ext
from types import SimpleNamespace

class JsonpathNgNotifier(Notifier):
    @classmethod
    def name(cls) -> str:
        return "JsonpathNgNotifier"
    
    def required_parameters(self) -> dict:
        return {
            "jsonpath_expression": None,
            "replacement_value": None
        }
        
    async def _notify_impl(self, network: Network, data, logger: logging.Logger, params: dict = {}) -> (bool, object):
        params_ns = SimpleNamespace(**params)
        jsonpath_expression = params.get("jsonpath_expression").format(network=network, params=params_ns)
        replacement_value = params.get("replacement_value").format(network=network, data=data, params=params_ns)

        try:
            jsonpath_expr = jsonpath_rw_ext.parse(jsonpath_expression)
            for match in jsonpath_expr.find(data):
                path = match.path
                path.update(data, replacement_value)

            return True, data
        except Exception as e:
            logger.error(f"Failed to evaluate JSONPath expression '{jsonpath_expression}': {e}")
            return False