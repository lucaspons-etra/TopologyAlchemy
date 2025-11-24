# Topology Alchemy Examples

This directory contains example scripts and data to help you get started with Topology Alchemy.

## Directory Structure

```
examples/
├── README.md                          # This file
├── basic_conversion.py                # Simple format conversion
├── programmatic_usage.py              # Using Topology Alchemy as a library
├── create_topology_from_scratch.py   # Build topology programmatically
├── excel_to_pandapower.sh             # Shell script example
└── data/                              # Sample data files (placeholder)
```

## Running Examples

### Command-Line Examples

#### 1. Excel to PandaPower

Convert an Excel file to PandaPower format:

```bash
python ../src/main.py \
  --iFormat ExcelImporter \
  --input_file data/sample_network.xlsx \
  --oFormat PandapowerExporter \
  --output_file output/network.json \
  --network_id sample_network
```

#### 2. With Low Voltage Processing

Process both MV and LV networks:

```bash
python ../src/main.py \
  --iFormat ExcelImporter \
  --input_file data/sample_network.xlsx \
  --process_lv true \
  --oFormat PandapowerExporter \
  --output_file output/network_with_lv.json \
  --network_id sample_network
```

#### 3. Multiple Formats with Visualization

Export to JSON and create visualization:

```bash
python ../src/main.py \
  --iFormat ExcelImporter \
  --input_file data/sample_network.xlsx \
  --oFormat JsonExporter \
  --output_file output/network.json \
  --nFormat CytoscapeJsExporter \
  --network_id sample_network
```

### Python Script Examples

#### 1. Basic Conversion Script

See `basic_conversion.py` for a simple conversion example.

```bash
python basic_conversion.py
```

#### 2. Programmatic Usage

See `programmatic_usage.py` for using Topology Alchemy as a library.

```bash
python programmatic_usage.py
```

#### 3. Create Topology from Scratch

See `create_topology_from_scratch.py` for building topologies programmatically.

```bash
python create_topology_from_scratch.py
```

## Sample Data Files

The `data/` directory contains sample topology data in various formats:

- `sample_network.xlsx` - Example Excel topology file
- `sample_network.json` - Example PandaPower network
- `sample_network.xiidm` - Example PowSyBl network

**Note**: These are placeholder files. You should replace them with your actual network data.

## Expected Output

Running these examples will create output files in the `output/` directory (created automatically if it doesn't exist).

## Troubleshooting

### Common Issues

1. **Module not found**: Make sure you've installed all dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```

2. **Input file not found**: Verify the path to your input file is correct.

3. **Missing parameters**: Each importer/exporter requires specific parameters. Check the main README for details.

### Getting Help

- Check the [main README](../README.md) for more information
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines
- Open an issue on GitHub if you encounter problems

## Next Steps

After running these examples:

1. Modify the example scripts to work with your data
2. Explore other importers and exporters
3. Create custom notifiers for your use case
4. Contribute your examples back to the project!

## License

These examples are part of the Topology Alchemy project and are licensed under the Apache License 2.0.
