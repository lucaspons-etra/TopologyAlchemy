import aiofiles
import json
import logging
import math
from pathlib import Path
from topology import (
    Element,
    Bus,
    LineShape,
    Meter,
    Switch,
    Network,
    UsagePointLocation,
    # VoltageLevel,
    Substation,
    TwoWindingsTransformer,
    ThreeWindingsTransformer,
    Line,
    Load,
    Generator,
    DanglingLine,
    Location,
)
from Utils import Sanitizer
from base_exporter import Exporter

typeTemplates = {
    "substation": {"shape": "CT", "type": "Substation"},
    "bus": {"shape": "bus", "type": "Bus"},
    "load": {"shape": "pod", "type": "Load"},
    "generator": {"shape": "generator", "type": "Generator"},
    "transformer": {"shape": "transformer", "type": "Transformer"},
    "line": {"shape": "line", "type": "Line"},
    "switch": {"shape": "switch", "type": "Switch"},
    "shuntCompensator": {"shape": "shuntCompensator", "type": "ShuntCompensator"},
    "danglingLine": {"shape": "danglingLine", "type": "DanglingLine"},
    "usagePointLocation": {"shape": "pod", "type": "UsagePointLocation"},
    "usagePoint": {
        "shape": "pod",
        "type": "UsagePoint",
        "cim": {
            "amiBillingReady": 4,
            "amiBillingReadySpecified": True,
            "checkBilling": False,
            "checkBillingSpecified": False,
            "connectionState": 1,
            "connectionStateSpecified": True,
            "estimatedLoad": 0,
            "estimatedLoadSpecified": False,
            "grounded": False,
            "groundedSpecified": False,
            "isSdp": True,
            "isSdpSpecified": True,
            "isVirtual": False,
            "isVirtualSpecified": True,
            "minimalUsageExpected": True,
            "minimalUsageExpectedSpecified": True,
            "nominalServiceVoltage": 220.0,
            "nominalServiceVoltageSpecified": True,
            "outageRegion": None,
            "phaseCode": 0,
            "phaseCodeSpecified": False,
            "ratedCurrent": 0.0,
            "ratedCurrentSpecified": False,
            "ratedPowerSpecified": True,
            "readCycle": None,
            "readRoute": None,
            "serviceDeliveryRemark": None,
            "servicePriority": None,
            "ConfigurationEvents": None,
            "Equipments": {"mRID": None, "Names": None},
            "MetrologyRequirements": None,
            "PricingStructures": None,
            "ServiceCategory": None,
            "ServiceLocation": None,
            "ServiceMultipliers": None,
            "ServiceSupplier": None,
        },
    },
    "meter": {
        "shape": "meter",
        "type": "Meter",
        "isVirtual": False,
        "cim": {
            "amrSystem": "ÉTER",
            "ActivityRecords": [],
            "ComFunction": [],
            "ConfigurationEvents": {},
            "ConnectDisconnectFunction": "",
            "EndDeviceInfo": {
                "isSolidState": True,
                "phaseCount": "unknown",
                "ratedCurrent": 0,
                "ratedVoltage": 0,
                "AssetModel": {
                    "corporateStandardKind": "",
                    "modelNumber": 1,
                    "modelVersion": 1,
                    "usageKind": "",
                    "Manufacturer": {"mRID": None},
                },
                "capability": {
                    "autonomousDst": True,
                    "communication": True,
                    "connectDisconnect": True,
                    "demandResponse": True,
                    "electricMetering": True,
                    "gasMetering": False,
                    "metrology": True,
                    "onRequestRead": True,
                    "outageHistory": True,
                    "pressureCompensation": False,
                    "pricingInfo": True,
                    "pulseOutput": True,
                    "relaysProgramming": True,
                    "reverseFlow": True,
                    "superCompressibilityCompensation": False,
                    "temperatureCompensation": False,
                    "textMessage": True,
                    "waterMetering": False,
                },
            },
            "MeterMultipliers": [],
            "Names": "",
            "Seals": [],
            "SimpleEndDeviceFunction": "",
            "electronicAddress": {
                "email1": "notused",
                "email2": "notused",
                "lan": "",
                "mac": "",
                "password": "notused",
                "radio": "notused",
                "userID": "notused",
                "web": "",
            },
            "features": "",
            "formNumber": "Meter",
            "initialCondition": "new",
            "initialLossOfLife": 0,
            "initialLossOfLifeSpecified": True,
            "isVirtual": False,
            "isVirtualSpecified": True,
            "lifecycle": {
                "installationDate": "",
                "manufacturedDate": "",
                "purchaseDate": "",
                "receivedDate": "",
                "removalDate": "",
                "retiredDate": "",
            },
            "lotNumber": "",
            "purchasePrice": 0,
            "purchasePriceSpecified": True,
            "serialNumber": "",
            "timeZoneOffset": 2,
            "timeZoneOffsetSpecified": True,
            "utcNumber": "",
        },
    },
}


class JsonExporter(Exporter):
    """JSON Exporter for exporting topology to JSON format."""

    def required_parameters(self) -> dict:
        return {
            "output_file": None,
            "context": None,
            "system": None,
        }

    @classmethod
    def name(cls) -> str:
        return "JsonExporter"

    def __init__(self):
        self.type_templates = typeTemplates

    def export_topology_full(
        self,
        topology: Network,
        file: str,
        context: str,
        system: str,
        logger: logging.Logger,
    ) -> bool:
        """
        Export topology to JSON format with full parameters.

        Args:
            topology: The network topology to export
            file: Output file path
            context: Context string for the export
            system: System identifier
            logger: Logger instance

        Returns:
            bool: True if export successful, False otherwise
        """
        params = {
            "output_file": file,
            "context": context,
            "system": system,
        }
        return self._export_topology_impl(topology, logger, params)

    def _export_element(
        self,
        element: Element,
        element_type: str,
        context: str,
        system: str,
        network: str,
    ) -> dict:
        """Export a single element to JSON format."""
        sanitizer = Sanitizer(system, element.prefix)
        element_id = sanitizer.sanitizeId(element.id)
        json_obj = self.type_templates[element_type].copy()
        json_obj.update(
            {
                "_id": element_id,
                "context": context + element_type + "#" + element_id,
                "mRID": element.id,
                "name": element.name,
                "system": system,
                "network": network,
            }
        )
        if hasattr(element, "feeder_num") and element.feeder_num is not None:
            json_obj.update({"feederNumber": element.feeder_num})
        if isinstance(element, Location) and element.coords:
            json_obj["geometry"] = {
                "type": "Point",
                "coordinates": element.coords[::-1],  # [lat, lon] to [lon, lat]
            }
        if isinstance(element, LineShape) and element.line_shape:
            json_obj["geometry"] = {
                "type": "LineString",
                "coordinates": [coords[::-1] for coords in element.line_shape],
            }
        return json_obj

    def default_parameters(self) -> dict:
        return {
            "file": None,  # Output file path
            "context": None,  # Context string
            "system": None,  # System identifier
        }

    async def _export_topology_impl(
        self, network: Network, logger: logging.Logger, params: dict = {}
    ) -> dict[str, Path]:
        """Internal implementation of topology export."""

        output_file_elems = params.get("output_file").split(".")
        context = params.get("context")
        system = params.get("system")

        result = {}

        for sub_topology in [network] + network.getElements("subTopologies"):
            if len(output_file_elems) > 1:
                output_file = ".".join(output_file_elems[:-1]) + f"_{sub_topology.id}." + output_file_elems[-1]
            else:
                output_file = f"{output_file_elems[0]}_{sub_topology.id}"

            logger.info("> Starting JSON exporting '{}'".format(str(output_file)))

            # systems = []
            substations = []
            buses = []
            loads = []
            usage_point_locations = []
            usage_points = []
            generators = []
            transformers = []
            lines = []
            dangling_lines = []
            switches = []
            meters = []

            # systems.append(
            #     self._export_system(
            #         network, context, system, default_layout_mv, default_layout_lv
            #     )
            # )

            for sub in sub_topology.getElements("substations"):
                substations.append(self._export_substation(sub, context, system, sub_topology.network))
                for bus in sub.getElements("buses"):
                    buses.append(self._export_bus(bus, sub.id, context, system, sub_topology.network))
                    for load in bus.getElements("loads"):
                        loads.append(self._export_load(load, sub.id, context, system, sub_topology.network))
                        if len(load.getElements("meters")) > 0:
                            for meter in load.getElements("meters"):
                                meters.append(self._export_meter(meter, context, system, sub_topology.network))
                    for up in bus.getElements("usagePointLocations"):
                        upl = self._export_usage_point_location(up, sub.id, context, system, sub_topology.network)
                        usage_point_locations.append(upl)
                    for u in bus.getElements("usagePoints"):
                        usage_points.append(self._export_usage_point(u, context, system, sub_topology.network))
                        if len(u.getElements("meters")) > 0:
                            for meter in u.getElements("meters"):
                                meters.append(self._export_meter(meter, context, system, sub_topology.network))
                    for generator in bus.getElements("generators"):
                        generators.append(self._export_generator(generator, sub.id, context, system, sub_topology.network))
                        if len(generator.getElements("meters")) > 0:
                            for meter in generator.getElements("meters"):
                                meters.append(self._export_meter(meter, context, system, sub_topology.network))
                    for dangling_line in bus.getElements("danglingLines"):
                        dangling_lines.append(self._export_dangling_line(dangling_line, sub.id, context, system, sub_topology.network))
                for switch in sub.getElements("switches"):
                    switches.append(self._export_switch(switch, sub.id, context, system, sub_topology.network))
                for trafo in sub.getElements("twoWindingsTransformers"):
                    transformers.append(self._export_two_windings_transformer(trafo, sub.id, context, system, sub_topology.network))
                for trafo in sub.getElements("threeWindingsTransformers"):
                    transformers.append(self._export_three_windings_transformer(trafo, sub.id, context, system, sub_topology.network))
                for line in sub.getElements("lines"):
                    lines.append(self._export_line(line, context, system, sub_topology.network))
            
            for bus in sub_topology.getElements("buses"):
                buses.append(self._export_bus(bus, None, context, system, sub_topology.network))
                for load in bus.getElements("loads"):
                    loads.append(self._export_load(load, None, context, system, sub_topology.network))
                    if len(load.getElements("meters")) > 0:
                        for meter in load.getElements("meters"):
                            meters.append(self._export_meter(meter, context, system, sub_topology.network))
                for up in bus.getElements("usagePointLocations"):
                    upl = self._export_usage_point_location(up, None, context, system, sub_topology.network)
                    usage_point_locations.append(upl)
                for u in bus.getElements("usagePoints"):
                    usage_points.append(self._export_usage_point(u, context, system, sub_topology.network))
                    if len(u.getElements("meters")) > 0:
                        for meter in u.getElements("meters"):
                            meters.append(self._export_meter(meter, context, system, sub_topology.network))
                for generator in bus.getElements("generators"):
                    generators.append(self._export_generator(generator, None, context, system, sub_topology.network))
                    if len(generator.getElements("meters")) > 0:
                        for meter in generator.getElements("meters"):
                            meters.append(self._export_meter(meter, context, system, sub_topology.network))
                for dangling_line in bus.getElements("danglingLines"):
                    dangling_lines.append(self._export_dangling_line(dangling_line, None, context, system, sub_topology.network))
            for switch in sub_topology.getElements("switches"):
                switches.append(self._export_switch(switch, None, context, system, sub_topology.network))
            for line in sub_topology.getElements("lines"):
                lines.append(self._export_line(line, context, system, sub_topology.network))

            async with aiofiles.open(output_file, 'w', encoding="utf8") as output_json:
                # await output_json.write("db.eter_systems.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_substations.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_buses.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_loads.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_generators.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_transformers.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_lines.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_switches.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_danglingLines.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_usagePointLocations.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_usagePoints.deleteMany({\"context\":/" + context + "/})\n")
                # await output_json.write("db.eter_meters.deleteMany({\"context\":/" + context + "/})\n")

                await output_json.write("{\n")
                # await output_json.write("db.eter_systems.insertMany( [" + (",\n".join(systems)) + "])\n")
                await output_json.write("  \"substations\": [" + (",\n".join(substations)) + "],\n")
                await output_json.write("  \"buses\": [" + (",\n".join(buses)) + "],\n")
                await output_json.write("  \"loads\": [" + (",\n".join(loads)) + "],\n")
                await output_json.write("  \"generators\": [" + (",\n".join(generators)) + "],\n")
                await output_json.write("  \"transformers\": [" + (",\n".join(transformers)) + "],\n")
                await output_json.write("  \"lines\": [" + (",\n".join(lines)) + "],\n")
                await output_json.write("  \"switches\": [" + (",\n".join(switches)) + "],\n")
                await output_json.write("  \"danglingLines\": [" + (",\n".join(dangling_lines)) + "],\n")
                await output_json.write("  \"usagePointLocations\": [" + (",\n".join(usage_point_locations)) + "],\n")
                await output_json.write("  \"usagePoints\": [" + (",\n".join(usage_points)) + "],\n")
                await output_json.write("  \"meters\": [" + (",\n".join(meters)) + "]\n")
                await output_json.write("}\n")

                await output_json.flush()

                result[sub_topology.id] = Path(output_file)

        logger.info("Finished JSON exporting!")
        return result

    # def _export_system(
    #     self,
    #     topology: Network,
    #     context: str,
    #     system: str,
    #     default_layout_mv: str,
    #     default_layout_lv: str,
    # ) -> str:
    #     """Export system information."""
    #     networks = {}

    #     networks[system] = {
    #         "name": topology.name,
    #         "networkId": topology.id,
    #         "feeder": False,
    #         "layout": default_layout_mv if default_layout_mv is not None else None,
    #         "elements": {},
    #     }

    #     for t in topology.getElements("subTopologies"):
    #         networks[t.id] = {
    #             "name": t.name,
    #             "networkId": t.id,
    #             "feeder": True,
    #             "layout": default_layout_lv if default_layout_lv is not None else None,
    #             "elements": {},
    #         }

    #     output = json.dumps(
    #         {
    #             "_id": system,
    #             "name": system,
    #             "context": context,
    #             "powSyBl": {"networks": list(networks.values())},
    #         },
    #         ensure_ascii=False,
    #     )
    #     return output

    def _export_substation(
        self, substation: Substation, context: str, system: str, network: str
    ) -> str:
        """Export substation information."""
        json_obj = self._export_element(
            substation, "substation", context, system, network
        )
        json_obj.update(
            {
                "voltageLevels": sorted(
                    list(
                        {bus.voltageLevel.id for bus in substation.getElements("buses")}
                    )
                )
            }
        )

        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_bus(
        self, element: Bus, substation: str, context: str, system: str, network: str
    ) -> str:
        """Export bus information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(element, "bus", context, system, network)
        json_obj.update(
            {
                "voltageLevel": element.voltageLevel.id,
                "nominalVoltage": element.voltageLevel.nominalV * 1000,  # kV to V
                "type": element.voltageLevel.type,
            }
        )

        if substation is not None:
            json_obj.update(
                {
                    "substation": sanitizer.sanitizeId(substation),
                }
            )

        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_load(
        self, element: Load, substation: str, context: str, system: str, network: str
    ) -> str:
        """Export load information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(element, "load", context, system, network)
        json_obj.update(
            {
                "bus": sanitizer.sanitizeId(element.parent.id),
                "ratedPower": element.p,  # kW
                "referenceReactivePower": element.q,  # kvar
            }
        )
        if substation is not None:
            json_obj.update(
                {
                    "substation": sanitizer.sanitizeId(substation),
                }
            )
        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_usage_point_location(
        self,
        element: UsagePointLocation,
        substation: str,
        context: str,
        system: str,
        network: str,
    ) -> str:
        """Export usage point location information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(
            element, "usagePointLocation", context, system, network
        )
        json_obj.update(
            {
                "bus": sanitizer.sanitizeId(element.parent.id),
            }
        )
        if substation is not None:
            json_obj.update(
                {
                    "substation": sanitizer.sanitizeId(substation),
                }
            )
        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_usage_point(
        self, element: Meter, context: str, system: str, network: str
    ) -> str:
        """Export usage point information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(element, "usagePoint", context, system, network)
        json_obj.update(
            {
                "bus": sanitizer.sanitizeId(element.parent.id),
                "usagePointLocation": sanitizer.sanitizeId(element.location.id),
            }
        )
        json_obj["cim"].update(
            {
                "location": sanitizer.sanitizeId(element.location.id),
                "endDevices": [sanitizer.sanitizeId(element.id)],
                "ratedPower": element.ratedPower,
                "Names": {"name": element.name, "NameType": None},
            }
        )

        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_meter(
        self, element: Meter, context: str, system: str, network: str
    ) -> str:
        """Export meter information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(element, "meter", context, system, network)
        json_obj.update(
            {
                "usagePoint": sanitizer.sanitizeId(element.parent.id),
                "installedPower": element.p,  # kW
                "referenceReactivePower": element.q,  # kvar
            }
        )
        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_generator(
        self,
        element: Generator,
        substation: str,
        context: str,
        system: str,
        network: str,
    ) -> str:
        """Export generator information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(element, "generator", context, system, network)
        json_obj.update(
            {
                "bus": sanitizer.sanitizeId(element.parent.id),
                "controllable": element.controllable,
                "installedPower": element.maxP,  # kW
            }
        )
        if substation is not None:
            json_obj.update(
                {
                    "substation": sanitizer.sanitizeId(substation),
                }
            )
        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_two_windings_transformer(
        self,
        element: TwoWindingsTransformer,
        substation: str,
        context: str,
        system: str,
        network: str,
    ) -> str:
        """Export two windings transformer information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(
            element, "transformer", context, system, network
        )
        json_obj.update(
            {
                "substation": sanitizer.sanitizeId(element.parent.id),
                "bus1": sanitizer.sanitizeId(element.bus1.id),
                "bus2": sanitizer.sanitizeId(element.bus2.id),
                "r": element.r,
                "x": element.x,
                "g": element.g,
                "b": element.b,
                "ratedApparentPower": element.nominal,  # kVA
                "ratedVoltage1": element.bus1.voltageLevel.nominalV * 1000,  # kV to V
                "ratedVoltage2": element.bus2.voltageLevel.nominalV * 1000,  # kV to V
                "voltageLevel1": element.bus1.voltageLevel.id,
                "voltageLevel2": element.bus2.voltageLevel.id,
            }
        )

        # Panda Power parameters
        panda_power_params = {
            "i0_percent": element.i0_percent,
            "pfe_kw": element.pfe_kw,
            "shift_degree": element.shift_degree,
            "std_type": element.std_type,
            "tap_max": element.tap_max,
            "tap_min": element.tap_min,
            "tap_neutral": element.tap_neutral,
            "tap_pos": element.tap_pos,
            "tap_side": element.tap_side,
            "tap_step_degree": element.tap_step_degree,
            "tap_step_percent": element.tap_step_percent,
            "vk_percent": element.vk_percent,
            "vkr_percent": element.vkr_percent,
        }

        dict_copy = panda_power_params.copy()
        for key, value in dict_copy.items():
            if value is None or value == "" or (isinstance(value, float) and math.isnan(value)):
                panda_power_params.pop(key)

        if panda_power_params:
            json_obj.update({"pandaPowerParameters": panda_power_params})

        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_three_windings_transformer(
        self,
        element: ThreeWindingsTransformer,
        substation: str,
        context: str,
        system: str,
        network: str,
    ) -> str:
        """Export three windings transformer information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(
            element, "transformer", context, system, network
        )
        json_obj.update(
            {
                "substation": sanitizer.sanitizeId(element.parent.id),
                "bus1": sanitizer.sanitizeId(element.bus1.id),
                "bus2": sanitizer.sanitizeId(element.bus2.id),
                "bus3": sanitizer.sanitizeId(element.bus3.id),
                "r1": element.r1,
                "r2": element.r2,
                "r3": element.r3,
                "x1": element.x1,
                "x2": element.x2,
                "x3": element.x3,
                "g1": element.g1,
                "g2": element.g2,
                "g3": element.g3,
                "b1": element.b1,
                "b2": element.b2,
                "b3": element.b3,
                "ratedApparentPower1": element.ratedS1,  # kVA
                "ratedApparentPower2": element.ratedS2,  # kVA
                "ratedApparentPower3": element.ratedS3,  # kVA
                "ratedVoltageStarBus": element.ratedStar * 1000,  # kV to V
                "ratedVoltage1": element.bus1.voltageLevel.nominalV * 1000,  # kV to V
                "ratedVoltage2": element.bus2.voltageLevel.nominalV * 1000,  # kV to V
                "ratedVoltage3": element.bus3.voltageLevel.nominalV * 1000,  # kV to V
                "voltageLevel1": element.bus1.voltageLevel.id,
                "voltageLevel2": element.bus2.voltageLevel.id,
                "voltageLevel3": element.bus3.voltageLevel.id,
            }
        )
        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_dangling_line(
        self,
        element: DanglingLine,
        substation: str,
        context: str,
        system: str,
        network: str,
    ) -> str:
        """Export dangling line information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(
            element, "danglingLine", context, system, network
        )
        json_obj.update(
            {
                "bus": sanitizer.sanitizeId(element.parent.id),
                "type": element.type,
                "controllable": element.controllable,
            }
        )
        if substation is not None:
            json_obj.update(
                {
                    "substation": sanitizer.sanitizeId(substation),
                }
            )

        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_switch(
        self, element: Switch, substation: str, context: str, system: str, network: str
    ) -> str:
        """Export switch information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(element, "switch", context, system, network)
        json_obj.update(
            {
                "bus1": sanitizer.sanitizeId(element.bus1.id),
                "bus2": sanitizer.sanitizeId(element.bus2.id),
            }
        )
        if substation is not None:
            json_obj.update(
                {
                    "substation": sanitizer.sanitizeId(substation),
                }
            )
        output = json.dumps(json_obj, ensure_ascii=False)
        return output

    def _export_line(
        self, element: Line, context: str, system: str, network: str
    ) -> str:
        """Export line information."""
        sanitizer = Sanitizer(system, element.prefix)
        json_obj = self._export_element(element, "line", context, system, network)
        json_obj.update(
            {
                "bus1": sanitizer.sanitizeId(element.bus1.id),
                "bus2": sanitizer.sanitizeId(element.bus2.id),
                "voltageLevel1": element.voltageLevel.id,
                "voltageLevel2": element.voltageLevel.id,
                "length": element.length,
                "shape": element.type,
                "type": element.type,
                "cable": str(element.cable),
                "currentLimit": (
                    element.currentLimit
                    if element.currentLimit and element.currentLimit > 0
                    else None
                ),
                "r": element.r,
                "g1": element.g1,
                "g2": element.g2,
                "b1": element.b1,
                "b2": element.b2,
                "x": element.x,
            }
        )

        if element.line_shape:
            json_obj["geometry"] = {
                "type": "LineString",
                "coordinates": [coords[::-1] for coords in element.line_shape],
            }

        output = json.dumps(json_obj, ensure_ascii=False)
        return output
