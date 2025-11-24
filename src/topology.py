"""
Topology Data Model Module

This module defines the core data structures for representing electrical grid topologies.
It provides a comprehensive object-oriented model for power system networks including:

- Network hierarchy (networks, sub-networks, substations)
- Electrical components (buses, lines, transformers, switches)
- Power equipment (loads, generators, usage points, meters)
- Geographical information (locations, line shapes)

The data model supports both Medium Voltage (MV) and Low Voltage (LV) networks,
with flexible voltage level management and relationships between components.

Part of the OPENTUNITY EU Project - Topology Alchemy toolkit.

Classes:
    Identifiable: Base class for all identifiable objects
    Location: Geographical coordinate container
    LineShape: Line geometry representation
    Element: Base element with location support
    Container: Element that can contain other elements
    Network: Top-level network container
    Substation: Physical substation with equipment
    VoltageLevel: Voltage level grouping
    Bus: Electrical connection point
    Line: Transmission/distribution line
    Switch: Switching device
    Transformer: Power transformers (2-winding and 3-winding)
    Load: Consumption point
    Generator: Generation unit
    UsagePoint: Consumer connection point
    Meter: Measurement device
"""

from ast import Dict
import json
from re import sub
from sys import prefix
from Utils import Transliterate,Sanitizer


class Identifiable:
    def __init__(self, id, name, parent = None, prefix=None):
        self.id = str(id)
        # self.name = Transliterate.process(str(name)) if name is not None else ''
        self.name = str(name) if name is not None else ''
        self.parent = parent
        self.prefix=prefix
        self.prefix = self.getPrefix()

    def getPrefix(self, ):
        return self.prefix if self.prefix!=None else ("" if self.parent==None else self.parent.getPrefix()) 
        
    def getId(self,id):
        sanitizer = Sanitizer(system="", prefix=self.prefix)
        return sanitizer.sanitizeId(id)
        #return (self.prefix + "_" if not self.prefix=="" and not id.startswith(self.prefix) else "") + str(Transliterate.process(id))        
        
class Location():
    def __init__(self,coords=[]):
        self.coords = coords

class LineShape():
    def __init__(self,line_shape=[]):
        self.line_shape = line_shape
        
class Element(Identifiable):
    def __init__(self, id, name , parent = None,prefix=None, location:Location=None):
        Identifiable.__init__(self,id, name=name, prefix=prefix, parent=parent)
        self.location = location
        self.measurements = None
        
    def add_measurements(self,measurements):
        self.measurements=measurements
        

class Container(Element):
    def __init__(self, id, name , parent = None,prefix=None, location:Location=None, containerElements=[]):
        Element.__init__(self, id, name=name, parent = parent,prefix=prefix, location=location )
        self.elements = {e:[] for e in containerElements}
                
    def addElement(self, type, element):
        if type in self.elements:
            self.elements[type].append(element)
        else:
            self.elements[type] = [element]
        return element

    def getElements(self, type):
        # if not type in self.elements:
        #     print("ERROR:" + type + " not found in " + self.id)
        return self.elements[type] if type in self.elements else []
        
    def getElement(self, type, id):
        id=str(id)
        
        # if not type in self.elements:
        #     print("ERROR:" + type + " not found in " + self.id)
        for element in self.getElements(type):
            if element.id == id:
                return element
        return None 

class  VoltageLevel(Container):
    def __init__(self, id, name , nominalV=None, type='MV',network:Element=None):
        Element.__init__(self,id, name , parent=network)
        Container.__init__(self,id, name , parent=network, containerElements= ["buses", "switches", "lines"])
        self.nominalV = nominalV        
        self.type=type
        # self.feeder=feeder
        # self.feederNum=feederNum
        
    def hasBus(self, id):
        return self.getElement("buses",id) != None
    
    def getBus(self, id):
        return self.getElement("buses",id)
    
    # def addBus(self, id, name ):        
    #     bus = Bus(id, name , type_=self.type, voltageLevel=self)
    #     self.addElement("buses",bus)
    #     return bus
          
    # def addSwitch(self, id, bus1, bus2, open, retained=False):
    #     s = Switch(id, id,self.getBus(bus1).id, self.getBus(bus2).id, open, retained=False,parent=self)
    #     self.addElement("switches",s)
    #     return s

    # def addLine(self, id, name, bus1, bus2, r=0, x=0, g1=0, b1=0, g2=0, b2=0, currentLimit=0, lineShape=[],length=0,cable=''):
    #     if(bus1 == bus2):
    #         print("bucle eliminado")
    #         return
    #     #TODO: complete
        
    #     vl1:VoltageLevel = bus1.parent
    #     vl2:VoltageLevel = bus2.parent
    #     line:Line = Line(id, name , self, vl1, vl2, bus1, bus2, r,x, g1, b1, g2, b2, currentLimit,vl1.type,length,cable,self.prefix,lineShape)
    #     self.addElement("lines",line)
    #     return line

class Network(Container):
    def __init__(self,id,name , parent=None, prefix=None, network=None, system=None):         
        Container.__init__(self,id,name, parent=parent, prefix=prefix, containerElements=["buses","lines","switches","substations","voltageLevels","subTopologies"])
        self.network = network if network else id
        self.system = system
        self.type = 'MV' if parent is None else 'LV'

    def addSubTopology(self, id,name ):
        t = Network(id,name,network=id, parent=self, prefix=id, system=self.system)
        self.addElement("subTopologies",t)
        return t

    def getSubTopology(self, id):
        return self.getElement("subTopologies",id)
    
    def addSubstation(self, id, name , coords=[]):
        s:Substation = self.getElement("substations",id)
        if s== None:
            s = Substation(id, name=name, coords= coords, parent=self)
            self.addElement("substations",s)
        return s
    
    def hasBus(self, id):
        return self.getElement("buses", id) is not None
    
    def addBus(self, id, name, voltageLevel:VoltageLevel, coords=[],feeder_num=None):
        return self.addElement("buses", Bus(id, name, network=self, voltageLevel=voltageLevel, coords=coords,feeder_num=feeder_num))
    
    def getBus(self, id):
        return self.getElement("buses", id)
    
    def addSwitch(self, id, name, bus1, bus2, open=False, retained=False, coords=[],feeder_num=None):
        s = Switch(id, name, bus1, bus2, open, retained, network=self, coords=coords, feeder_num=feeder_num)
        self.addElement("switches",s)
        return s

    def addLine(self, id, name, bus1, bus2, r=0, x=0, g1=0, b1=0, g2=0, b2=0, currentLimit=0, line_shape=[],length=0,cable='',feeder_num=None):
        if(bus1 == bus2):
            print("bucle eliminado")
            return
        return self.addElement("lines",Line(id, name , bus1= bus1, bus2= bus2,r= r, x=x ,g1= g1,b1= b1,g2= g2,b2= b2,currentLimit= currentLimit, length=length,cable= cable,line_shape=line_shape, network=self, feeder_num=feeder_num))

    def getSubstation(self, id):
        return self.getElement("substations",id)
            
    def getLoad(self, id):
        for sub in self.getElements("substations"):
            for b in sub.getElements("buses"):
                l = b.getElement("loads",id)
                if l is not None:
                    return l
        for b in self.getElements("buses"):
            l = b.getElement("loads",id)
            if l is not None:
                return l
        return None
    
    def getUsagePointLocation(self, id):
        for sub in self.getElements("substations"):
            for b in sub.getElements("buses"):
                up = b.getElement("usagePointLocations",id)
                if up is not None:
                    return up
        for b in self.getElements("buses"):
            up = b.getElement("usagePointLocations",id)
            if up is not None:
                return up
        return None

    def getUsagePoint(self, id):
        for sub in self.getElements("substations"):
            for b in sub.getElements("buses"):
                up = b.getElement("usagePoints",id)
                if up is not None:
                    return up
        
        for b in self.getElements("buses"):
            up = b.getElement("usagePoints",id)
            if up is not None:
                return up
        return None
    
    def getGenerator(self, id):
        for sub in self.getElements("substations"):
            for b in sub.getElements("buses"):
                gen = b.getElement("generators",id)
                if gen is not None:
                    return gen
        for b in self.getElements("buses"):
            gen = b.getElement("generators",id)
            if gen is not None:
                return gen
        return None

    def getSubstationFromBus(self, id):
        for substation in self.getElements("substations"):
            if substation.getElement("buses",id) != None:
                return substation
        return None

    def getBus(self, id):
        for sub in self.getElements("substations"):
            b= sub.getElement("buses",id)
            if b is not None:
                return b
        return  self.getElement("buses",id)
        
    
    def getVoltageLevel(self, id):
        return  self.getElement("voltageLevels",id)            
        
    def addVoltageLevel(self, id, name, nominalV,type='MV'):
        vl = self.getElement("voltageLevels",id)
        if vl is not None:
            return vl
        vl = VoltageLevel(id, name, nominalV,type, network=self)
        self.addElement("voltageLevels",vl)
        return vl

    def hasVoltageLevel(self, id):
        return self.getElement("voltageLevels",id)!=None

class Substation(Container,Location):
    def __init__(self, id, name ,parent:Network, coords=[]):
        Container.__init__(self,id,name=name,parent=parent,containerElements= ["buses", "switches","lines","twoWindingsTransformers","threeWindingsTransformers"])
        Location.__init__(self,coords=coords)
 
    def getBus(self, id):        
        return self.getElement("buses",id)
        
    def getLoad(self,id):
        for bus in self.getElements("buses"):
            l:Load = bus.getElement("loads",id)
            if l != None: 
                return l
        return None
    
    def getUsagePointLocation(self,id):
        for bus in self.getElements("buses"):
            up:UsagePointLocation = bus.getElement("getUsagePointLocation",id)
            if up != None: 
                return up
        return None
    
    def addTransformer(self, id, name, bus1:Container, bus2:Container, r=None, x=None, g=None, b=None, nominal=None,
                       i0_percent=None, pfe_kw=None, shift_degree=None, std_type=None, tap_max=None, tap_min=None,
                       tap_neutral=None, tap_pos=None, tap_side=None, tap_step_degree=None, tap_step_percent=None,
                       vk_percent=None, vkr_percent=None, coords=[]):
        return self.addElement("twoWindingsTransformers",TwoWindingsTransformer(
            id, name,self, bus1, bus2, r=r, x=x, g=g, b=b, nominal=nominal, i0_percent=i0_percent, pfe_kw=pfe_kw, shift_degree=shift_degree,
            std_type=std_type, tap_max=tap_max, tap_min=tap_min, tap_neutral=tap_neutral, tap_pos=tap_pos, tap_side=tap_side,
            tap_step_degree=tap_step_degree, tap_step_percent=tap_step_percent, vk_percent=vk_percent, vkr_percent=vkr_percent, coords=coords))

    def addTriTransformer(self, id, name, bus1, bus2, bus3, r1=None, x1=None, g1=None, b1=None, r2=None, x2=None, g2=None, b2=None, r3=None, x3=None, g3=None, b3=None,  ratedS1=None, ratedS2=None, ratedS3=None, ratedStar=None, coords=[]):
        return self.addElement("threeWindingsTransformers",ThreeWindingsTransformer(
            id, name,self, bus1, bus2, bus3,  r1=r1, x1=x1, g1=g1, b1=b1, r2=r2, x2=x2, g2=g2, b2=b2, r3=r3, x3=x3, g3=g3, b3=b3, ratedS1=ratedS1, ratedS2=ratedS2, ratedS3=ratedS3, ratedStar=ratedStar, coords=coords))

    # def addTriTransformer(self, id, bus1, bus2, bus3, ratedU, r1, x1, g1, b1, r2, x2, g2, b2, r3, x3, g3, b3, ratedU1, ratedU2, ratedU3, ratedS1, ratedS2, ratedS3):
    #     voltageLevel1 = self.getVoltageLevelFromBus(bus1)
    #     voltageLevel2 = self.getVoltageLevelFromBus(bus2)
    #     voltageLevel3 = self.getVoltageLevelFromBus(bus3)
    #     if not(voltageLevel1):
    #         voltageLevel1 = self.addVoltageLevel(bus1, ratedU1, 'MV' if ratedU1 > LIMIT_MV else 'LV')
    #         voltageLevel1.addBus(bus1)
    #         # logger.warn("Bus '" + bus1 + "' does not have voltage level")
    #     elif voltageLevel1.nominalV != ratedU1:
    #         print("Bus '" + bus1 + "' voltage (" + str(voltageLevel1.nominalV) + ") differs from transformer rated voltage (" + str(ratedU1) + ")")
    #     if not(voltageLevel2):
    #         voltageLevel2 = self.addVoltageLevel(bus2, ratedU2, 'MV' if ratedU2 > LIMIT_MV else 'LV')
    #         voltageLevel2.addBus(bus2)
    #         # logger.warn("Bus '" + bus2 + "' does not have voltage level")
    #     elif voltageLevel2.nominalV != ratedU2:
    #         print("Bus '" + bus2 + "' voltage (" + str(voltageLevel2.nominalV) + ") differs from transformer rated voltage (" + str(ratedU2) + ")")
    #     if not(voltageLevel3):
    #         voltageLevel3 = self.addVoltageLevel(bus2, ratedU3, 'MV' if ratedU3 > LIMIT_MV else 'LV')
    #         voltageLevel3.addBus(bus3)
    #         # logger.warn("Bus '" + bus3 + "' does not have voltage level")
    #     elif voltageLevel3.nominalV != ratedU3:
    #         print("Bus '" + bus3 + "' voltage (" + str(voltageLevel3.nominalV) + ") differs from transformer rated voltage (" + str(ratedU3) + ")")
        
    #     self.threeWindingsTransformers.append(ThreeWindingsTransformer(
    #         id, id,self.getBus(bus1).id, self.getBus(bus2).id, self.getBus(bus3).id, voltageLevel1, voltageLevel2, voltageLevel3, ratedU, r1, x1, g1, b1, r2, x2, g2, b2, r3, x3, g3, b3, ratedU1, ratedU2, ratedU3, ratedS1, ratedS2, ratedS3,self.prefix ))

    def hasBus(self, id):
        return self.getElement("buses", id) is not None
    
    def getBus(self, id):
        return self.getElement("buses", id)
    
    def addBus(self, id, name, voltageLevel:VoltageLevel, coords=[], feeder_num=None):
        bus = Bus(id, name, voltageLevel=voltageLevel, substation=self, coords=coords, feeder_num=feeder_num)
        self.addElement("buses", bus)
        return bus
          
    # def addSwitch(self, id, bus1, bus2, open, retained=False):
    #     s = Switch(id, id,bus1, bus2, open, retained, substation=self)
    #     self.addElement("switches", s)
    #     return s

    def addLine(self, id, name, bus1, bus2, r=0, x=0, g1=0, b1=0, g2=0, b2=0, currentLimit=0, lineShape=[],length=0,cable=''): 
        if(bus1 == bus2):
            print("bucle eliminado")
            return
        
        line:Line = Line(id, name, bus1=bus1, bus2=bus2, r=r, x=x , g1=g1, b1=b1, g2=g2, b2=b2, currentLimit=currentLimit, length=length, cable=cable, line_shape=lineShape, substation=self)
        self.addElement("lines",line)
        return line

class Bus(Container, Location):
    def __init__(self, id, name ,  voltageLevel:VoltageLevel=None, substation:Substation= None, network:Network=None, coords=[], feeder_num=None):
        Container.__init__(self,id, name , parent=substation if substation!=None else network, prefix=voltageLevel.prefix, containerElements=["usagePoints","usagePointLocations","loads","generators","danglingLines","shuntCompensators"])
        Location.__init__(self,coords=coords)
        self.voltageLevel = voltageLevel
        self.feeder_num = feeder_num
        if not self.voltageLevel.hasBus(id):
            self.voltageLevel.addElement("buses",self)
        
    
    def getLoad(self, id):
        for load in self.loads:
            if load.id==id: 
                return load
        return None
    
    def getUsagePointLocation(self, id):
        for up in self.usagePointLocations:
            if up.id==id: 
                return up
        return None
    
    def getGenerator(self,id):
        for generator in self.generators:
            if generator.id==id: 
                return generator
        return None
    
    def addLoad(self, id, name,  p=None, q=None, type=None, coords=None):
        return self.addElement("loads", Load(id, name, self, p=p, q=q,  type=type, coords=coords))

    def addMvGenerator(self, id, name, minP=None, maxP=None, targetP=None, targetV=None, targetQ=None, minQ=None, maxQ=None, controllable=True, coords=None):
        return self.addElement("generators", MvGenerator(id, name, self, minP, maxP, targetP, targetV, targetQ, minQ, maxQ, controllable, coords))

    def addUsagePointLocation(self, id, name , coords=None, feeder_num=None):
        return self.addElement("usagePointLocations",UsagePointLocation(id,name,self, coords=coords, feeder_num=feeder_num))

    def addUsagePoint(self, id, name, usagePointLocation: Container, ratedPower=None, feeder_num=None):
        up:UsagePoint = UsagePoint(id,name,self, usagePointLocation=usagePointLocation, ratedPower=ratedPower, feeder_num=feeder_num)
        usagePointLocation.linkUsagePoint(up)
        return self.addElement("usagePoints",up)
    
    def addGenerator(self, id, name, usagePointLocation: Container, minP=None, maxP=None, targetP=None, targetV=None, targetQ=None, minQ=None, maxQ=None, controllable=True, type=None, coords=None, feeder_num=None):
        gen:Generator = Generator(id, name, self, usagePointLocation=usagePointLocation, minP=minP, maxP=maxP, targetP=targetP, targetV=targetV, targetQ=targetQ, minQ=minQ, maxQ=maxQ, controllable=controllable, type=type, coords=coords, feeder_num=feeder_num)
        usagePointLocation.linkUsagePoint(gen)
        return self.addElement("generators",gen)

    def addDanglingLine(self, id, name, p=None, q=None, type="MV", controllable=True, feeder_num=None):
        return self.addElement("danglingLines", DanglingLine(self.id + "_" + id, name, self, p=p, q=q, type=type, controllable=controllable, feeder_num=feeder_num))

    def addShuntCompensator(self, id, bus, maxSecCount, bPerSection, gPerSection):
        self.shuntCompensators.append(ShuntCompensator(
            id, id,maxSecCount, bPerSection, gPerSection, bus,self.prefix))
        
class UsagePoint(Container):
    def __init__(self, id, name , bus:Bus,usagePointLocation:Location=None,ratedPower=None, feeder_num=None):
        Container.__init__(self,id, name , parent=bus, location=usagePointLocation,containerElements= ["meters"])
        self.ratedPower = ratedPower
        self.feeder_num = feeder_num
        
    def addMeter(self, id, name, p=0, q=0, feeder_num=None):
        m:Meter = Meter(id, name, p=p, q= q, parent=self, feeder_num=feeder_num)
        self.addElement("meters",m)
        return m 

class UsagePointLocation(Container, Location):
    def __init__(self, id, name , bus:Bus, type='MV', coords=None, feeder_num=None):
        Container.__init__(self,id, name , parent=bus, containerElements=["usagePoints", "generators"])        
        Location.__init__(self,coords)
        self.type=type
        self.feeder_num = feeder_num
    
    def linkUsagePoint(self, usagePoint:UsagePoint):
        self.addElement("usagePoints", usagePoint)
        return usagePoint

class Generator(Container, Location):
    def __init__(self, id, name , bus:Bus, usagePointLocation:Location=None, minP=None, maxP=None, targetP=None, targetV=None, targetQ=None, minQ=None, maxQ=None,controllable=None, type="MV", coords=None, feeder_num=None):
        Container.__init__(self,id, name , parent=bus, location=usagePointLocation, containerElements=["meters"])
        Location.__init__(self,coords)
        self.minP = minP
        self.maxP = maxP
        self.targetP = targetP
        self.targetV = targetV
        self.targetQ = targetQ
        self.minQ = minQ
        self.maxQ = maxQ
        self.controllable = controllable
        self.type=type
        self.feeder_num = feeder_num
        
    def addMeter(self, id, name, p=0, q=0, feeder_num=None):
        m:Meter = Meter(id, name, p=p, q=q, parent=self, feeder_num=feeder_num)
        self.addElement("meters",m)
        return m 

class DanglingLine(Element):
    #def __init__(self, id, p, q, bus,type="MV", controllable = False, network=None, remoteNetwork=None):
    def __init__(self, id, name ,bus:Bus, p=None, q=None,type="MV", controllable = False, feeder_num=None):
        Element.__init__(self,id, name ,parent=bus)
        self.p = p
        self.q = q
        self.type=type
        self.controllable=controllable
        self.feeder_num=feeder_num

class Load(Container, Location):
    def __init__(self, id,name, bus:Bus, p=None, q=None, type='MV', coords=None):
        Container.__init__(self,id, name , parent=bus,  containerElements=["meters"] )
        Location.__init__(self,coords)
        self.p = p if p is not None else 0
        self.q = q if q is not None else 0
        self.type=type
        # self.meters=[]
        
    def addMeter(self, id, name, p, q):
        m:Meter = Meter(id, name, p, q, parent=self)
        self.addElement("meters",m)
        return m
        # self.meters.append(Meter(id, name, p, q, parent=self))

class MvGenerator(Container, Location):
    def __init__(self, id,name, bus:Bus, minP=None, maxP=None, targetP=None, targetV=None, targetQ=None, minQ=None, maxQ=None, controllable=True, coords=None):
        Container.__init__(self, id, name, parent=bus, containerElements=["meters"] )
        Location.__init__(self, coords)
        self.minP = minP
        self.maxP = maxP
        self.targetP = targetP
        self.targetV = targetV
        self.targetQ = targetQ
        self.minQ = minQ
        self.maxQ = maxQ
        self.controllable = controllable
        self.type="MV"
        # self.meters=[]
        
    def addMeter(self, id, name, p, q):
        m:Meter = Meter(id, name, p, q, parent=self)
        self.addElement("meters",m)
        return m
        # self.meters.append(Meter(id, name, p, q, parent=self))

class Line(Element, LineShape):
    def __init__(self, id, name , bus1:Bus, bus2:Bus, r, x, g1, b1, g2, b2, currentLimit,type='MV',length=0, cable='', prefix=None,line_shape=[], substation:Substation=None, network:Network=None, feeder_num=None):
        Element.__init__(self,id, name ,prefix=prefix, parent=substation if substation!=None else network)
        LineShape.__init__(self,line_shape=line_shape)
        self.line_shape=line_shape
        if bus1.voltageLevel != bus2.voltageLevel:
            print("ERROR: Voltage levels of buses " + bus1.id + " and " + bus2.id + " are different")      
        
        self.bus1 = bus1
        self.bus2 = bus2
        self.voltageLevel = self.bus1.voltageLevel
        self.r = r if r is not None else 0
        self.x = x if x is not None else 0
        self.g1 = g1 if g1 is not None else 0
        self.b1 = b1 if b1 is not None else 0
        self.g2 = g2 if g2 is not None else 0
        self.b2 = b2 if b2 is not None else 0
        self.currentLimit = currentLimit
        self.type=self.voltageLevel.type
        self.length=length
        self.cable=cable
        self.feeder_num = feeder_num

class TwoWindingsTransformer(Element, Location):
    def __init__(self, id, name , substation:Substation, bus1, bus2,  r=None, x=None, g=None, b=None, nominal=None,
                 i0_percent=None, pfe_kw=None, shift_degree=None, std_type=None, tap_max=None, tap_min=None,
                 tap_neutral=None, tap_pos=None, tap_side=None, tap_step_degree=None, tap_step_percent=None,
                 vk_percent=None, vkr_percent=None, coords=[]):
        Element.__init__(self,id, name ,parent=substation)
        Location.__init__(self, coords)
        self.r = r if r is not None else 0
        self.x = x if x is not None else 0
        self.g = g if g is not None else 0
        self.b = b if b is not None else 0
        self.bus1 = bus1
        self.bus2 = bus2
        self.nominal = nominal
        self.i0_percent = i0_percent
        self.pfe_kw = pfe_kw
        self.shift_degree = shift_degree
        self.std_type = std_type
        self.tap_max = tap_max
        self.tap_min = tap_min
        self.tap_neutral = tap_neutral
        self.tap_pos = tap_pos
        self.tap_side = tap_side
        self.tap_step_degree = tap_step_degree
        self.tap_step_percent = tap_step_percent
        self.vk_percent = vk_percent
        self.vkr_percent = vkr_percent

class ThreeWindingsTransformer(Element, Location):
    def __init__(self, id, name ,substation:Substation,  bus1, bus2, bus3, ratedStar=None, r1=None, x1=None, g1=None, b1=None, r2=None, x2=None, g2=None, b2=None, r3=None, x3=None, g3=None, b3=None, ratedS1=None, ratedS2=None, ratedS3=None, coords=[]):
        Element.__init__(self,id, name, substation)
        Location.__init__(self, coords)
        self.ratedStar = ratedStar
        self.ratedS1 = ratedS1
        self.ratedS2 = ratedS2
        self.ratedS3 = ratedS3
        self.r1 = r1 if r1 is not None else 0
        self.r2 = r2 if r2 is not None else 0
        self.r3 = r3 if r3 is not None else 0

        self.x1 = x1 if x1 is not None else 0
        self.x2 = x2 if x2 is not None else 0
        self.x3 = x3 if x3 is not None else 0

        self.g1 = g1 if g1 is not None else 0
        self.g2 = g2 if g2 is not None else 0
        self.g3 = g3 if g3 is not None else 0

        self.b1 = b1 if b1 is not None else 0
        self.b2 = b2 if b2 is not None else 0
        self.b3 = b3 if b3 is not None else 0

        self.bus1 = bus1
        self.bus2 = bus2
        self.bus3 = bus3

class Switch(Element, Location):
    def __init__(self, id, name, bus1, bus2, open=False, retained=False, substation:Substation=None, network:Network=None, coords=[], feeder_num=None):
        Element.__init__(self, id, name, substation if substation is not None else network)
        Location.__init__(self, coords)
        if open=="OPEN" or open:
            open=1
        if open=="CLOSED":
            open=0
        if bus1.voltageLevel != bus2.voltageLevel:
            print("ERROR: Voltage levels of buses " + bus1.id + " and " + bus2.id + " are different")
            
        self.voltageLevel = bus1.voltageLevel
        self.bus1 = bus1
        self.bus2 = bus2
        self.open = str(int(open) == 1)
        self.retained = retained
        self.feeder_num = feeder_num

class ShuntCompensator(Element):
    def __init__(self, id, name , maxSecCount, bPerSection, gPerSection, bus:Bus, prefix=None):
        super().__init__(self,id, name ,prefix, parent=bus)
        self.maxSecCount = maxSecCount
        self.bPerSection = bPerSection
        self.gPerSection = gPerSection
        
class Meter(Element):
    def __init__(self, id, name , p, q, parent, feeder_num=None):
        Element.__init__(self, id, name, parent=parent)
        self.p = p
        self.q = q
        self.feeder_num = feeder_num
