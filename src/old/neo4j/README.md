# Neo4j Exporter

This module exports power system topology data from Topology Alchemy to Neo4j graph database format using Cypher queries.

## Overview

The Neo4j exporter converts the topology model into Cypher CREATE statements that can be executed in Neo4j to build a graph database representation of the power system network.

## Features

- **Node Types**: Creates nodes for all power system components:
  - System
  - Substation
  - Bus
  - Load
  - Generator
  - Transformer (Two and Three Windings)
  - Line
  - Switch
  - DanglingLine
  - UsagePoint
  - UsagePointLocation
  - Meter
  - ShuntCompensator

- **Relationships**: Creates typed relationships between nodes:
  - `HAS_SUBSTATION` - System to Substation
  - `HAS_BUS` - Substation to Bus
  - `HAS_LOAD` - Bus to Load
  - `HAS_GENERATOR` - Bus to Generator
  - `HAS_TRANSFORMER` - Substation to Transformer
  - `CONNECTED_TO` - Equipment to Bus connections
  - `HAS_METER` - UsagePoint to Meter
  - `LOCATED_AT` - UsagePoint to UsagePointLocation
  - `CONTAINS` - Hierarchical containment

- **Properties**: Preserves all relevant properties including:
  - IDs (sanitized and original mRID)
  - Names
  - Electrical parameters (voltage, power, impedance, etc.)
  - Geographical coordinates (latitude/longitude)
  - Line shapes (geometry)
  - Context and system metadata

## Usage

### From Python Code

```python
from converters.neo4j.neo4jExporter import exportTopology
from topology import Network
import logging

# Create or load your topology
topology = Network(...)

# Export to Neo4j Cypher file
logger = logging.getLogger(__name__)
exportTopology(
    topology=topology,
    file="output.cypher",
    context="myContext",
    system="mySystem",
    defaultLayoutMV="default_mv_layout",
    defaultLayoutLV="default_lv_layout",
    logger=logger
)
```

### Loading into Neo4j

Once exported, you can load the Cypher file into Neo4j:

#### Option 1: Neo4j Browser
```cypher
// In Neo4j Browser, copy and paste the contents of the generated .cypher file
```

#### Option 2: cypher-shell
```bash
cat output.cypher | cypher-shell -u neo4j -p password
```

#### Option 3: Python neo4j driver
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

with open("output.cypher", "r") as f:
    cypher_script = f.read()

with driver.session() as session:
    # Split by semicolon and execute each statement
    statements = [s.strip() for s in cypher_script.split(';') if s.strip()]
    for statement in statements:
        if statement and not statement.startswith('//'):
            session.run(statement)

driver.close()
```

## Output Format

The exporter generates a `.cypher` file with the following structure:

1. **Header**: Comments with metadata
2. **Constraints**: CREATE CONSTRAINT statements for unique IDs
3. **Cleanup**: DETACH DELETE for existing data with the same context
4. **System Node**: Creates the root system node
5. **Component Nodes**: Creates all component nodes with properties
6. **Relationships**: MATCH and CREATE statements to link components

### Example Output

```cypher
// Neo4j Cypher Export
// Context: myContext
// System: mySystem

// Create constraints and indexes
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Bus) REQUIRE n.id IS UNIQUE;

// Delete existing data for this context
MATCH (n) WHERE n.context = "myContext" DETACH DELETE n;

// Create System node
CREATE (s:System {id: "mySystem", name: "mySystem", context: "myContext"});

// Substation
CREATE (n:Substation {id: "SUB1", mRID: "SUB1", name: "Main Substation", context: "myContext"});
MATCH (s:System {id: "mySystem"}), (n:Substation {id: "SUB1"}) CREATE (s)-[:HAS_SUBSTATION]->(n);

// Bus
CREATE (n:Bus {id: "BUS1", mRID: "BUS1", name: "Bus 1", nominalVoltage: 20000.0});
MATCH (s:Substation {id: "SUB1"}), (n:Bus {id: "BUS1"}) CREATE (s)-[:HAS_BUS]->(n);
```

## Data Model

### Node Labels and Properties

Each node type has standard properties:
- `id`: Sanitized identifier (unique)
- `mRID`: Original CIM mRID
- `name`: Human-readable name
- `context`: Context identifier
- `system`: System identifier
- `network`: Network identifier
- `type`: Component type
- `shape`: Visual shape identifier

Plus type-specific properties for electrical characteristics, ratings, and configuration.

### Relationships

Relationships follow the physical and logical connectivity of the power system:
- Hierarchical: System → Substation → Equipment
- Connectivity: Equipment ←→ Bus connections
- Association: Equipment → Location

## Querying the Graph

Once loaded into Neo4j, you can query the graph:

### Find all loads connected to a substation
```cypher
MATCH (s:Substation {name: "Main Substation"})-[:HAS_BUS]->(b:Bus)-[:HAS_LOAD]->(l:Load)
RETURN s.name, b.name, l.name, l.ratedPower
```

### Find the shortest path between two buses
```cypher
MATCH path = shortestPath(
  (b1:Bus {id: "BUS1"})-[*]-(b2:Bus {id: "BUS2"})
)
RETURN path
```

### Find all transformers connecting different voltage levels
```cypher
MATCH (t:Transformer)
WHERE t.ratedVoltage1 <> t.ratedVoltage2
RETURN t.name, t.ratedVoltage1, t.ratedVoltage2, t.ratedApparentPower
```

### Get topology around a specific bus
```cypher
MATCH (b:Bus {id: "BUS1"})-[r]-(equipment)
RETURN b, r, equipment
```

## Comparison with MongoDB Exporter

| Feature | MongoDB Exporter | Neo4j Exporter |
|---------|-----------------|----------------|
| Data Model | Document-based collections | Graph with nodes and edges |
| Relationships | Embedded or referenced IDs | First-class graph relationships |
| Queries | Aggregation pipelines | Cypher pattern matching |
| Traversal | Multiple queries | Single path queries |
| Best For | Hierarchical data, analytics | Connected data, topology analysis |

## Notes

- The exporter follows the same structure as the MongoDB exporter for consistency
- Property names match CIM naming conventions where applicable
- Coordinates are stored as separate latitude/longitude properties
- Line shapes are stored as GeoJSON strings in the `geometry` property
- All string values are properly escaped for Cypher syntax
- The context field allows multiple systems to coexist in the same database

## Dependencies

- Python 3.x
- topology module (from Topology Alchemy)
- Utils module (Sanitizer, Transliterate)

Optional for loading:
- Neo4j 4.x or 5.x
- neo4j Python driver (for programmatic loading)

## License

Part of the Topology Alchemy project.
