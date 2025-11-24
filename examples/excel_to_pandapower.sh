#!/bin/bash
# Excel to PandaPower Conversion Script
# Part of the OPENTUNITY EU Project - Topology Alchemy toolkit

# Configuration
INPUT_FILE="data/sample_network.xlsx"
OUTPUT_FILE="output/sample_network.json"
NETWORK_ID="sample_network"
SYSTEM="Example Utility"
LOG_LEVEL="INFO"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================================================"
echo "Topology Alchemy - Excel to PandaPower Conversion"
echo "========================================================================"
echo ""
echo "Configuration:"
echo "  Input:      $INPUT_FILE"
echo "  Output:     $OUTPUT_FILE"
echo "  Network ID: $NETWORK_ID"
echo "  System:     $SYSTEM"
echo "  Log Level:  $LOG_LEVEL"
echo ""

# Check if input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}ERROR: Input file not found: $INPUT_FILE${NC}"
    exit 1
fi

# Create output directory if it doesn't exist
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR"

# Run the conversion
python ../src/main.py \
    --iFormat ExcelImporter \
    --input_file "$INPUT_FILE" \
    --oFormat PandapowerExporter \
    --output_file "$OUTPUT_FILE" \
    --network_id "$NETWORK_ID" \
    --system "$SYSTEM" \
    --logLevel "$LOG_LEVEL"

# Check exit status
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}[SUCCESS] Conversion completed successfully!${NC}"
    echo "  Output saved to: $OUTPUT_FILE"
else
    echo ""
    echo -e "${RED}[FAILED] Conversion failed!${NC}"
    exit 1
fi

echo ""
echo "========================================================================"
