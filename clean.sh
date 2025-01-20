#!/usr/bin/env bash

usage() {
    echo "Usage: $0 [-m] [-o] notebook.ipynb"
    echo "  -m    Clean metadata"
    echo "  -o    Clean outputs"
    echo "At least one flag is required"
    exit 1
}

clean_metadata=false
clean_outputs=false

while getopts "mo" opt; do
    case $opt in
        m) clean_metadata=true ;;
        o) clean_outputs=true ;;
        ?) usage ;;
    esac
done

shift $((OPTIND-1))

if [ $# -ne 1 ] || [ "$clean_metadata" = false -a "$clean_outputs" = false ]; then
    usage
fi

NOTEBOOK=$1

if [ ! -f "$NOTEBOOK" ]; then
    echo "Error: File '$NOTEBOOK' not found!"
    exit 1
fi

CONVERT_OPTS=""
if [ "$clean_outputs" = true ]; then
    CONVERT_OPTS="$CONVERT_OPTS --ClearOutputPreprocessor.enabled=True"
fi
if [ "$clean_metadata" = true ]; then
    CONVERT_OPTS="$CONVERT_OPTS --ClearMetadataPreprocessor.enabled=True"
fi

jupyter nbconvert \
    $CONVERT_OPTS \
    --to=notebook \
    --inplace \
    --log-level=ERROR "$NOTEBOOK"

echo "Notebook '$NOTEBOOK' has been cleaned."
