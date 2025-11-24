
  [meteorCalls.topologyViewer.topology]: async (system, network) => {
    MongoTopologyViewer.checkInitialized();
    check(system, String);
    check(network, String);
    const elements = {};
    // const query = system ? { system, network } : { network };
    const query = { system, network };

    const [
      allSubstations,
      allBuses,
      feeder,
      allTransformers,
      allLoads,
      allGenerators,
      allDanglingLines,
      allLines,
      allSwitches,
      allUsagePointLocations,
    ] = await Promise.all([
      MongoTopologyViewer.citric.findAll(citricLayer('substations'), query),
      MongoTopologyViewer.citric.findAll(citricLayer('buses'), query),
      MongoTopologyViewer.citric.findOne(citricLayer('buses'), {
        system,
        _id: network,
      }),
      MongoTopologyViewer.citric.findAll(citricLayer('transformers'), query),
      MongoTopologyViewer.citric.findAll(citricLayer('loads'), query),
      MongoTopologyViewer.citric.findAll(citricLayer('generators'), query),
      MongoTopologyViewer.citric.findAll(citricLayer('danglingLines'), query),
      MongoTopologyViewer.citric.findAll(citricLayer('lines'), query),
      MongoTopologyViewer.citric.findAll(citricLayer('switches'), query),
      MongoTopologyViewer.citric.findAll(
        citricLayer('usagePointLocations'),
        query,
      ),
    ]);

    // if (feeder) {
    //   allBuses.push(feeder);
    //   const substationFeeder = await MongoTopologyViewer.citric.findOne(Meteor.settings.public.layer + '_substations', {
    //     system: system,
    //     _id: feeder.substation,
    //   });
    //   allSubstations.push(substationFeeder);
    // }

    let busesDict = {};

    getCoordsFromLine = (elem) => {
      const l = allLines.find((line) => line.bus1 === elem || line.bus2 === elem);
      if (!l) return;
      if (l.bus1 == elem) return l.geometry?.coordinates[0];
      if (l.bus2 == elem) return l.geometry?.coordinates[l.geometry?.coordinates?.length - 1];
    };

    getCoordsFromTx = (bus) => {
      const tx = allTransformers.find((t) => t.bus1 === bus || t.bus2 === bus);
      if (!tx) return;
      return tx.geometry?.coordinates || getCoordsFromLine(tx.bus1) || getCoordsFromLine(tx.bus2);
    };

    getCoordsFromBus = (bus) => {
      const b = allBuses.find((b) => b._id === bus);
      if (!b) return;
      return b.geometry?.coordinates || getCoordsFromLine(bus);
    };

    await _.each(
      allSubstations.filter((e) => !!e),
      async (substation) => {
        const substationId = `SUBSTATION@${substation._id}`;
        const powsyblId = substation._id;
        elements[substationId] = {
          data: {
            id: substationId,
            name: substation.name, // || substation._id,
            type: 'SUBSTATION',
            fict: !substation.name ? 1 : 0,
            powsyblId,
            lat: substation.geometry ? substation.geometry.coordinates[1] : 0,
            lon: substation.geometry ? substation.geometry.coordinates[0] : 0,
          },
        };

        // transformers
        if (!feeder) {
          const transformers = allTransformers.filter(
            (t) => t.substation == substation._id,
          );
          _.each(transformers, (transformer) => {
            if (transformer.bus1 && transformer.bus2 && transformer.bus3) {
              const transformerId = `3WINDINGSTRANSFORMER@${transformer._id}`;
              const line1Id = `TRANSFORMER_LINE1@${transformer._id}`;
              const line2Id = `TRANSFORMER_LINE2@${transformer._id}`;
              const line3Id = `TRANSFORMER_LINE3@${transformer._id}`;
              elements[line1Id] = {
                data: {
                  id: line1Id,
                  source: `BUS@${transformer.bus1}`,
                  target: transformerId,
                  type: 'TRANSFORMER_LINE',
                },
              };
              elements[line2Id] = {
                data: {
                  id: line2Id,
                  source: `BUS@${transformer.bus2}`,
                  target: transformerId,
                  type: 'TRANSFORMER_LINE',
                },
              };
              elements[line3Id] = {
                data: {
                  id: line3Id,
                  source: `BUS@${transformer.bus3}`,
                  target: transformerId,
                  type: 'TRANSFORMER_LINE',
                },
              };
              const coords = transformer.geometry?.coordinates
                || getCoordsFromBus(transformer.bus1)
                || getCoordsFromBus(transformer.bus2)
                || getCoordsFromBus(transformer.bus3)
                || [0, 0];
              elements[transformerId] = {
                data: {
                  id: transformerId,
                  _id: transformer._id,
                  powsyblId: transformer._id,
                  name: transformer.name || transformer._id,
                  parent: `SUBSTATION@${transformer.substation}`,
                  type: '3WINDINGSTRANSFORMER',
                  lat: coords[1],
                  lon: coords[0],
                },
              };
            } else if (transformer.bus1 && transformer.bus2) {
              const transformerId = `2WINDINGSTRANSFORMER@${transformer._id}`;
              const line1Id = `TRANSFORMER_LINE1@${transformer._id}`;
              const line2Id = `TRANSFORMER_LINE2@${transformer._id}`;
              elements[line1Id] = {
                data: {
                  id: line1Id,
                  source: `BUS@${transformer.bus1}`,
                  target: transformerId,
                  type: 'TRANSFORMER_LINE',
                },
              };
              elements[line2Id] = {
                data: {
                  id: line2Id,
                  source: `BUS@${transformer.bus2}`,
                  target: transformerId,
                  type: 'TRANSFORMER_LINE',
                },
              };
              const coords = transformer.geometry?.coordinates
                || getCoordsFromBus(transformer.bus1)
                || getCoordsFromBus(transformer.bus2)
                || [0, 0];
              elements[transformerId] = {
                data: {
                  id: transformerId,
                  _id: transformer._id,
                  powsyblId: transformer._id,
                  name: transformer.name || transformer._id,
                  parent: `SUBSTATION@${transformer.substation}`,
                  type: '2WINDINGSTRANSFORMER',
                  lat: coords[1],
                  lon: coords[0],
                },
              };
            }
          });
        }
      },
    );

    // buses
    await _.each(allBuses, async (configuredBus) => {
      const busId = `BUS@${configuredBus._id}`;
      const coords = configuredBus.geometry?.coordinates
        || getCoordsFromLine(configuredBus._id)
        || getCoordsFromTx(configuredBus._id)
        || [0, 0];
      elements[busId] = {
        data: {
          id: busId,
          powsyblId: configuredBus._id,
          name: configuredBus.name || configuredBus._id,
          parent: configuredBus.feederNum
            ? null
            : `SUBSTATION@${configuredBus.substation}`,
          type: 'BUS',
          nominalVoltage: configuredBus.nominalVoltage,
          lat: coords[1],
          lon: coords[0],
        },
      };
      busesDict[configuredBus._id] = configuredBus._id;

      // loads
      const loads = allLoads.filter((l) => l.bus == configuredBus._id);
      await _.each(loads, async (load) => {
        const loadId = `LOAD@${load._id}`;
        const lineId = `LOAD_LINE@${load._id}`;
        elements[lineId] = {
          data: {
            id: lineId,
            source: busId,
            target: loadId,
            type: 'LOAD_LINE',
          },
        };
        elements[loadId] = {
          data: {
            id: loadId,
            powsyblId: load._id,
            name: load.name || load._id,
            parent: configuredBus.feederNum
              ? null
              : `SUBSTATION@${configuredBus.substation}`,
            type: 'LOAD',
            lat: load.geometry.coordinates[1],
            lon: load.geometry.coordinates[0],
          },
        };
        //busesDict[configuredBus._id]=configuredBus._id
      });

      // generators

      const generators = allGenerators.filter((g) => {
        return g.bus == configuredBus._id;
      });
      _.each(generators, (generator) => {
        const generatorId = `GENERATOR@${generator._id}`;
        const lineId = `GENERATOR_LINE@${generator._id}`;
        elements[lineId] = {
          data: {
            id: lineId,
            source: busId,
            target: generatorId,
            type: 'GENERATOR_LINE',
          },
        };
        elements[generatorId] = {
          data: {
            id: generatorId,
            powsyblId: generator._id,
            name: generator.name || generator._id,
            parent: configuredBus.feederNum
              ? null
              : `SUBSTATION@${configuredBus.substation}`,
            type: 'GENERATOR',
            lat: generator.geometry?.coordinates[1],
            lon: generator.geometry?.coordinates[0],
          },
        };
        //busesDict[configuredBus._id]=configuredBus._id
      });


      // danglingLines
      //const danglingLines = await MongoTopologyViewer.citric.findAll(Meteor.settings.public.layer + "_danglingLines",{ bus:configuredBus._id, type: {"$ne":'LV'}});
      const danglingLines = allDanglingLines.filter((d) => {
        return d.bus == configuredBus._id;
      });
      _.each(danglingLines, (danglingLine) => {
        const danglingLineId = `DANGLINGLINE@${danglingLine._id}`;
        const lineId = `DANGLINGLINE_LINE@${danglingLine._id}`;
        elements[lineId] = {
          data: {
            id: lineId,
            source: busId,
            target: danglingLineId,
            type: 'DANGLINGLINE_LINE',
          },
        };
        const coords = danglingLine.geometry?.coordinates
          || getCoordsFromBus(danglingLine.bus)
          || [0, 0];
        elements[danglingLineId] = {
          data: {
            id: danglingLineId,
            powsyblId: danglingLine._id,
            name: danglingLine.name || danglingLine._id,
            parent: configuredBus.feederNum
              ? null
              : `SUBSTATION@${configuredBus.substation}`,
            type: 'DANGLINGLINE',
            lat: coords[1],
            lon: coords[0],
          },
        };
        //busesDict[configuredBus._id]=configuredBus._id
      });

      // usagePointLocations
      const usagePointLocations = allUsagePointLocations.filter(
        (l) => l.bus == configuredBus._id,
      );
      await _.each(usagePointLocations, async (usagePointLocation) => {
        const usagePointLocationId = `USAGE_POINT_LOCATION@${usagePointLocation._id}`;
        const lineId = `USAGE_POINT_LOCATION_LINE@${usagePointLocation._id}`; // TODO: rename to USAGE_POINT_LOCATION_LINE  (without the @) ?
        elements[lineId] = {
          data: {
            id: lineId,
            source: busId,
            target: usagePointLocationId,
            type: 'USAGE_POINT_LOCATION_LINE',
          },
        };
        elements[usagePointLocationId] = {
          data: {
            id: usagePointLocationId,
            powsyblId: usagePointLocation._id,
            name: usagePointLocation.name || usagePointLocation._id,
            parent: configuredBus.feeder
              ? null
              : `SUBSTATION@${configuredBus.substation}`,
            type: 'USAGE_POINT_LOCATION',
            lat: usagePointLocation.geometry.coordinates[1],
            lon: usagePointLocation.geometry.coordinates[0],
          },
        };
        //busesDict[configuredBus._id]=configuredBus._id
      });
    });

    const busesIds = Object.keys(busesDict);

    const lines = allLines.filter((l) => busesIds.includes(l.bus1) && busesIds.includes(l.bus2));
    _.each(lines, (line) => {
      if (line.bus1 && line.bus2) {
        const bus1 = allBuses.find((bus) => bus._id === line.bus1);
        const bus2 = allBuses.find((bus) => bus._id === line.bus2);
        const lineId = `LINE@${line._id}`;
        elements[lineId] = {
          data: {
            powsyblId: line._id,
            id: lineId,
            name: line.name || line._id,
            source: `BUS@${line.bus1}`,
            target: `BUS@${line.bus2}`,
            type: 'LINE',
            typeLine: 'LINE_' + line.type,
            parent:
              line.voltageLevelId2 && bus1.substation === bus2.substation
                ? bus1.substation
                : null,
            currentLimit: line.currentLimit,
            r: +line.r,
            x: +line.x,
            nominalVoltage: bus1.nominalVoltage,
          },
        };
      }
    });

    const switches = allSwitches.filter((s) => busesIds.includes(s.bus1) && busesIds.includes(s.bus2));
    _.each(switches, (_switch) => {
      if (_switch.bus1 && _switch.bus2) {
        const switchId = `SWITCH@${_switch._id}`;
        const line1Id = `SWITCH_LINE1@${_switch._id}`;
        const line2Id = `SWITCH_LINE2@${_switch._id}`;
        elements[line1Id] = {
          data: {
            id: line1Id,
            source: `BUS@${_switch.bus1}`,
            target: switchId,
            type: 'SWITCH_LINE',
          },
        };
        elements[line2Id] = {
          data: {
            id: line2Id,
            source: `BUS@${_switch.bus2}`,
            target: switchId,
            type: 'SWITCH_LINE',
          },
        };
        const coords = _switch.geometry?.coordinates
          || getCoordsFromBus(_switch.bus1)
          || getCoordsFromBus(_switch.bus2)
          || [0, 0];
        elements[_switch._id] = {
          data: {
            id: switchId,
            powsyblId: _switch._id,
            name: _switch.name || _switch._id,
            parent: null, //`SUBSTATION@${MongoTopologyViewer.configuredBuses.find((b) => b._id === _switch.bus).substation}`,
            type: 'SWITCH',
            open: 0,
            lat: coords[1],
            lon: coords[0],
          },
        };
      }
    });
    const result = _.map(Object.keys(elements), (e) => elements[e]);

    return result;
  },