from marshmallow import Schema, fields, post_load, post_dump, EXCLUDE
from topology import Switch, Network, VoltageLevel, Substation, VoltageLevel, TwoWindingsTransformer, ThreeWindingsTransformer, Line, Load, Generator, DanglingLine, ShuntCompensator
from Utils import Sanitizer, Transliterate


class GeometrySchema(Schema):
       type = fields.Str(default="Point")
       coordinates = fields.List(fields.Float())
       
class SubstationSchema(Schema):
    _id = fields.Str(attribute="id",dump_only=True )
    id = fields.Str(data_key="_id", load_only=True )
    shape = fields.Str(dump_default="LV",dump_only=True)
    type =fields.Str(dump_default="LV",dump_only=True)
    feeder = fields.Str()
    feeder_num = fields.Int()
    coords = fields.List(fields.Float())
    geometry = fields.Nested(GeometrySchema)
	
    class Meta:
        unknown = EXCLUDE
        additional = ('name',)
 
    def __init__(self, *args, **kwargs):
        prefix = kwargs.pop('prefix', None)
        context = kwargs.pop('context', None)
        super(SubstationSchema, self).__init__(*args, **kwargs)
        self.context = context
        self.sanitizer = Sanitizer()
        if 'prefix' in kwargs:
            self.sanitizer.setPrefix(prefix)
 
    @post_load
    def make_Substation(self, data, **kwargs):
        if 'geometry' in data:
               data['coords'] = data['geometry']['coordinates']
               del data['geometry']
        return Substation(**data)
    
    @post_dump
    def wrap_with_geometry(self, data, many, **kwargs):
        if 'coords' in data:
            data['geometry'] = {
                'type': 'Point',
                'coordinates': data['coords']
            }
        data['_id']=self.sanitizer.sanitizeId(data['_id'])
        data['context']=self.context
        del data['coords']
        return data

class VoltageLevelSchema(Schema):
    _id = fields.Str(attribute="id",dump_only=True )
    id = fields.Str(data_key="_id", load_only=True )
   	
    class Meta:
        unknown = EXCLUDE
        additional = ('name',)
 
    def __init__(self, *args, **kwargs):
        prefix = kwargs.pop('prefix', None)
        context = kwargs.pop('context', None)
        super(SubstationSchema, self).__init__(*args, **kwargs)
        self.context = context
        self.sanitizer = Sanitizer()
        if 'prefix' in kwargs:
            self.sanitizer.setPrefix(prefix)