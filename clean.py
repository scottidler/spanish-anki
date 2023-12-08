#!/bin/env python3

import os
import argparse

from multiprocessing import Pool
from ruamel.yaml import YAML

def process_file(file_path):
    yaml = YAML(typ='safe')
    try:
        with open(file_path, 'r') as file:
            data = yaml.load(file)
            # Check if 'shortdef' is anywhere in the data
            if not any('shortdef' in d for d in data):
                new_name = f"{file_path}.to-be-deleted"
                os.rename(file_path, new_name)
                return f"Renamed: {file_path}"
    except Exception as e:
        return f"Error processing {file_path}: {e}"

    return f"Processed without renaming: {file_path}"

def main(directory):
    # Get all .yml files in the directory
    ymls = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.yml')]

    # Use multiprocessing to process files in batches
    with Pool() as pool:
        results = pool.map(process_file, ymls)

    for result in results:
        print(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process YAML files to find missing 'shortdef' fields")
    parser.add_argument("directory", help="Directory containing YAML files")
    args = parser.parse_args()
    main(args.directory)
