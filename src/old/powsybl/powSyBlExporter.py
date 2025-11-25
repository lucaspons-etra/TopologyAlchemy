from topology import Switch, Network, Substation, VoltageLevel, TwoWindingsTransformer, ThreeWindingsTransformer, Line, Load, Generator, DanglingLine, ShuntCompensator
from Utils import Sanitizer, Transliterate

def exportTopology(topology:Network, file, prefix,logger):
    sanitizer = Sanitizer()
    sanitizer.setPrefix(prefix)
    logger.info("> Starting XIIDM exporting '{}'".format(str(file)))
    output = f'''<?xml version="1.0" encoding="UTF-8"?>
    <iidm:network xmlns:iidm="http://www.itesla_project.eu/schema/iidm/1_0" id="{topology.idTopology}" caseDate="2020-01-01T00:00:00.000+00:00" forecastDistance="0" sourceFormat="test">'''
    for substation in topology.substations:
        output += exportSubstation(substation)
    for line in topology.lines:
        output += exportLine(line)
    output += f'''
    </iidm:network>'''
    outputXIIDM = open(file,'w', encoding="utf8")
    outputXIIDM.write(output)
    outputXIIDM.flush()
    outputXIIDM.close()
    logger.info("Finished XIIDM exporting!")
    return True

def exportSubstation(substation:Substation):
    output = ''
    sanitizer = Sanitizer()
    output += f'''
    <iidm:substation id="{sanitizer.sanitizeId(substation.id)}">
        <iidm:property name="coords" value="{ str(substation.coords)}"/>
        <iidm:property name="name" value="{substation.name}"/>'''
    for voltageLevel in substation.voltageLevels:
        output += exportVoltageLevel(voltageLevel)
    for twoWindingsTransformer in substation.twoWindingsTransformers:
        output +=  exportTwoWindingsTransformer(twoWindingsTransformer)
    for threeWindingsTransformer in substation.threeWindingsTransformers:
        output += exportThreeWindingsTransformer(threeWindingsTransformer)
    output += f'''
    </iidm:substation>'''
    return output

def exportVoltageLevel(voltageLevel: VoltageLevel):
    output = ''
    sanitizer = Sanitizer()
    output += f'''
    <iidm:voltageLevel id="{voltageLevel.id}" nominalV="{voltageLevel.nominalV}" lowVoltageLimit="{voltageLevel.nominalV * 0.8}" highVoltageLimit="{voltageLevel.nominalV * 1.2}" topologyKind="BUS_BREAKER">
      <iidm:property name="type" value="{voltageLevel.type}"/>
      <iidm:busBreakerTopology>'''
    for bus in voltageLevel.buses:
        output += f'''
        <iidm:bus id="{sanitizer.sanitizeId(bus.id)}">
          <iidm:property name="name" value="{sanitizer.sanitizeId(bus.id)}"/>
          <iidm:property name="type" value="{voltageLevel.type}"/>
        </iidm:bus>'''
    for bus in voltageLevel.buses:
        for switch in bus.switches:
            output += exportSwitch(switch)
    output += f'''
      </iidm:busBreakerTopology>'''
    for bus in voltageLevel.buses:
        for load in bus.loads:
            output += exportLoad(load)
        for generator in bus.generators:
            output += exportGenerator(generator)
        for danglingLine in bus.danglingLines:
            output += exportDanglingLine(danglingLine)
        for shuntCompensator in bus.shuntCompensators:
            output += exportShuntCompensator(shuntCompensator)
    output += f'''
    </iidm:voltageLevel>'''
    return output

def exportTwoWindingsTransformer(twoWindingsTransformer :TwoWindingsTransformer):
    sanitizer = Sanitizer()
    return f'''
    <iidm:twoWindingsTransformer id="{sanitizer.sanitizeId(twoWindingsTransformer.id)}" r="{twoWindingsTransformer.r}" x="{twoWindingsTransformer.x}" g="{twoWindingsTransformer.g}" b="{twoWindingsTransformer.b}" ratedU1="{twoWindingsTransformer.ratedU1}" ratedU2="{twoWindingsTransformer.ratedU2}" bus1="{sanitizer.sanitizeId(twoWindingsTransformer.bus1)}" connectableBus1="{sanitizer.sanitizeId(twoWindingsTransformer.bus1)}" voltageLevelId1="{twoWindingsTransformer.voltageLevel1.id}" bus2="{sanitizer.sanitizeId(twoWindingsTransformer.bus2)}" connectableBus2="{sanitizer.sanitizeId(twoWindingsTransformer.bus2)}" voltageLevelId2="{twoWindingsTransformer.voltageLevel2.id}" ratedS="{twoWindingsTransformer.nominal}">
      <iidm:property name="name" value="{twoWindingsTransformer.id}"/>
    </iidm:twoWindingsTransformer>'''

def exportThreeWindingsTransformer(threeWindingsTransformer :ThreeWindingsTransformer):
    sanitizer = Sanitizer()
    return f'''
    <iidm:threeWindingsTransformer id="{sanitizer.sanitizeId(threeWindingsTransformer.id)}" 
        r1="{threeWindingsTransformer.r1}" x1="{threeWindingsTransformer.x1}" ratedU1="{threeWindingsTransformer.ratedU1}" g1="{threeWindingsTransformer.g1}" b1="{threeWindingsTransformer.b1}" 
        r2="{threeWindingsTransformer.r2}" x2="{threeWindingsTransformer.x2}" ratedU2="{threeWindingsTransformer.ratedU2}" g2="{threeWindingsTransformer.g2}" b2="{threeWindingsTransformer.b2}" 
        r3="{threeWindingsTransformer.r3}" x3="{threeWindingsTransformer.x3}" ratedU3="{threeWindingsTransformer.ratedU3}" g3="{threeWindingsTransformer.g3}" b3="{threeWindingsTransformer.b3}" 
        bus1="{sanitizer.sanitizeId(threeWindingsTransformer.bus1)}" connectableBus1="{sanitizer.sanitizeId(threeWindingsTransformer.bus1)}" voltageLevelId1="{threeWindingsTransformer.voltageLevel1.id}" 
        bus2="{sanitizer.sanitizeId(threeWindingsTransformer.bus2)}" connectableBus2="{sanitizer.sanitizeId(threeWindingsTransformer.bus2)}" voltageLevelId2="{threeWindingsTransformer.voltageLevel2.id}"
        bus3="{sanitizer.sanitizeId(threeWindingsTransformer.bus3)}" connectableBus3="{sanitizer.sanitizeId(threeWindingsTransformer.bus3)}" voltageLevelId3="{threeWindingsTransformer.voltageLevel3.id}"
        self.ratedU = "{threeWindingsTransformer.ratedU}"
        RatedS1="{threeWindingsTransformer.ratedS1}" RatedU1="{threeWindingsTransformer.ratedU1}"
        RatedS2="{threeWindingsTransformer.ratedS2}" RatedU2="{threeWindingsTransformer.ratedU2}"
        RatedS3="{threeWindingsTransformer.ratedS3}" RatedU3="{threeWindingsTransformer.ratedU3}">
    <iidm:property name="name" value="{threeWindingsTransformer.id}"/>
    </iidm:threeWindingsTransformer>'''
    
def exportLine(line: Line):
    sanitizer = Sanitizer()
    return f'''
    <iidm:line id="{sanitizer.sanitizeId(line.id)}" r="{line.r}" x="{line.x}" g1="{line.g1}" b1="{line.b1}" g2="{line.g2}" b2="{line.b2}" 
    bus1="{sanitizer.sanitizeId(line.bus1)}" connectableBus1="{sanitizer.sanitizeId(line.bus1)}" voltageLevelId1="{line.voltageLevel1.id}" 
    bus2="{sanitizer.sanitizeId(line.bus2)}" connectableBus2="{sanitizer.sanitizeId(line.bus2)}" voltageLevelId2="{line.voltageLevel2.id}">
        <iidm:property name="name" value="{line.id}"/>
        <iidm:property name="coords" value="{line.coords}"/>
        <iidm:property name="type" value="{line.type}"/>
        <iidm:currentLimits1 permanentLimit="{line.currentLimit}" />
    </iidm:line>'''

def exportLoad(load: Load):
    sanitizer = Sanitizer()
    return f'''
      <iidm:load id="{sanitizer.sanitizeId(load.id)}" loadType="UNDEFINED" p0="{load.p0}" q0="{load.q0}" bus="{sanitizer.sanitizeId(load.bus)}" 
      connectableBus="{sanitizer.sanitizeId(load.bus)}">
        <iidm:property name="name" value="{load.id}"/>
        <iidm:property name="type" value="{load.type}"/>
        <iidm:property name="coords" value="{load.coords}"/>
        <iidm:property name="meters" value="{load.meters}"/>
      </iidm:load>'''
      
def exportGenerator(generator: Generator):
    sanitizer = Sanitizer()
    return f'''
      <iidm:generator id="{sanitizer.sanitizeId(generator.id)}" energySource="OTHER" minP="{generator.minP}" maxP="{generator.maxP}" 
      voltageRegulatorOn="{"true" if generator.voltageRegulatorOn else "false"}" targetP="{generator.targetP}" 
      targetV="{generator.targetV}" targetQ="{generator.targetQ}" bus="{sanitizer.sanitizeId(generator.bus)}" connectableBus="{sanitizer.sanitizeId(generator.bus)}">
        <iidm:property name="name" value="{generator.id}"/>
        <iidm:property name="type" value="{generator.type}"/>
        <iidm:property name="coords" value="{generator.coords}"/>
        <iidm:minMaxReactiveLimits minQ="{generator.minQ}" maxQ="{generator.maxQ}"/>
      </iidm:generator>'''
      
def exportDanglingLine(danglingLine:DanglingLine):
    sanitizer = Sanitizer()
    return f'''
      <iidm:danglingLine id="{sanitizer.sanitizeId(danglingLine.id)}" p0="{danglingLine.p0}" q0="{danglingLine.q0}" r="0" x="0" g="0" b="0" 
      bus="{sanitizer.sanitizeId(danglingLine.bus)}" connectableBus="{sanitizer.sanitizeId(danglingLine.bus)}">
        <iidm:property name="name" value="{danglingLine.id}"/>
        <iidm:property name="type" value="{danglingLine.type}"/>
      </iidm:danglingLine>'''

def exportShuntCompensator(shuntCompensator:ShuntCompensator):
    sanitizer = Sanitizer()
    return f'''
      <iidm:shunt id="{sanitizer.sanitizeId(shuntCompensator.id)}" bPerSection="{shuntCompensator.bPerSection}" maximumSectionCount="{shuntCompensator.maxSecCount}" 
      currentSectionCount="{shuntCompensator.maxSecCount}" bus="{sanitizer.sanitizeId(shuntCompensator.bus)}" connectableBus="{sanitizer.sanitizeId(shuntCompensator.bus)}">
        <iidm:property name="name" value="{shuntCompensator.id}"/>
      </iidm:shunt>'''

def exportSwitch(switch: Switch):
    sanitizer = Sanitizer()
    return f'''
    <iidm:switch id="{sanitizer.sanitizeId(switch.id)}" bus1="{sanitizer.sanitizeId(switch.bus1)}" bus2="{sanitizer.sanitizeId(switch.bus2)}" open="{switch.open}" retained="{switch.retained}">
        <iidm:property name="name" value="{switch.id}"/>
    </iidm:switch>'''