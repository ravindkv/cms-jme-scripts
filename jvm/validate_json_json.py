#!/usr/bin/env python3
"""
Author: [Your Name]
Created: [Date]
Modified: [Current Date]

Description:
    This script validates a specific jet veto map by comparing bin contents between two JSON files.
    It identifies and reports differences in bin contents to ensure the integrity of updates or
    modifications made to the JSON maps before announcing them to the CMS collaboration.
"""

import argparse
import gzip
import json
import logging
import sys
from pathlib import Path

import numpy as np
import uproot  # Required only if interacting with ROOT files elsewhere


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def load_json_map(json_file_path: str, map_name: str):
    """
    Loads a specific map from a JSON file.

    Args:
        json_file_path (str): Path to the JSON file.
        map_name (str): Name of the map to load.

    Returns:
        tuple: (x_edges, y_edges, bin_contents) if successful.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
        KeyError: If the map is not found in the JSON file.
        ValueError: If the JSON structure is invalid.
    """
    try:
        json_path = Path(json_file_path)
        if not json_path.exists():
            raise FileNotFoundError(f"JSON file '{json_file_path}' does not exist.")

        # Determine if the JSON is compressed
        if json_path.suffix == '.gz':
            with gzip.open(json_path, 'rt') as f:
                json_content = f.read()
        else:
            with open(json_path, 'r') as f:
                json_content = f.read()

        # Parse JSON content
        data = json.loads(json_content)

        # Navigate to the corrections
        corrections = data.get("corrections", [])
        if not corrections:
            raise ValueError("No 'corrections' found in the JSON file.")

        # Iterate through corrections to find the specified map
        for correction in corrections:
            data_section = correction.get("data", {})
            if data_section.get("nodetype") != "category":
                continue  # Skip if not a category nodetype

            content = data_section.get("content", [])
            for item in content:
                if item.get("key") != map_name:
                    continue  # Not the map we're looking for

                value = item.get("value", {})
                if value.get("nodetype") != "multibinning":
                    continue  # Not a multibinning nodetype

                # Extract edges and content
                edges = value.get("edges", [])
                if len(edges) != 2:
                    raise ValueError(f"Map '{map_name}' does not have two edge arrays.")

                x_edges = np.array(edges[0]).flatten()
                y_edges = np.array(edges[1]).flatten()
                bin_contents = np.array(value.get("content", [])).flatten()

                # Validate extracted data
                if x_edges.size == 0 or y_edges.size == 0:
                    raise ValueError(f"Map '{map_name}' has empty edge arrays.")
                if bin_contents.size == 0:
                    raise ValueError(f"Map '{map_name}' has empty bin contents.")

                print(x_edges)
                print(y_edges)
                print(bin_contents)
                print(len(bin_contents))
                print(sum(bin_contents))
                return x_edges, y_edges, bin_contents

        # If map not found after iterating
        raise KeyError(f"Map '{map_name}' not found in any correction within '{json_file_path}'.")

    except Exception as e:
        logging.error(f"Error loading map from JSON file: {e}")
        # Optionally, print the full traceback for debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)


def compare_histograms(old_hist: tuple, new_hist: tuple, map_name: str, tolerance: float = 1e-6):
    """
    Compares two histograms and prints differences where the bin content differs beyond a tolerance.

    Args:
        old_hist (tuple): (x_edges, y_edges, bin_contents) from the old JSON.
        new_hist (tuple): (x_edges, y_edges, bin_contents) from the new JSON.
        map_name (str): Name of the map being compared.
        tolerance (float, optional): Threshold below which differences are ignored. Defaults to 1e-6.

    Returns:
        int: Number of differing bins.
    """
    x_edges_old, y_edges_old, bin_contents_old = old_hist
    x_edges_new, y_edges_new, bin_contents_new = new_hist

    # Compare bin edges
    if not np.allclose(x_edges_old, x_edges_new, atol=tolerance):
        logging.error(f"X edges mismatch for map '{map_name}'.")
        sys.exit(1)
    if not np.allclose(y_edges_old, y_edges_new, atol=tolerance):
        logging.error(f"Y edges mismatch for map '{map_name}'.")
        sys.exit(1)

    num_bins_old = len(bin_contents_old)
    num_bins_new = len(bin_contents_new)

    if num_bins_new != num_bins_old:
        logging.error(f"Number of bins mismatch for map '{map_name}': Old JSON has {num_bins_old} bins, New JSON has {num_bins_new} bins.")
        sys.exit(1)

    differences = 0

    logging.info(f"Comparing histograms for map '{map_name}':")
    logging.info(f"Total number of bins: {num_bins_old}")

    # Determine the number of phi bins from y_edges
    num_phi_bins = len(y_edges_old) - 1

    for idx in range(num_bins_old):
        old_val = bin_contents_old[idx]
        new_val = bin_contents_new[idx]
        diff = new_val - old_val  # Difference: new - old

        if abs(diff) > tolerance:
            differences += 1
            # Calculate bin indices (assuming eta varies first, then phi)
            eta_bin = (idx // num_phi_bins) + 1
            phi_bin = (idx % num_phi_bins) + 1
            logging.warning(
                f"Difference found in bin (eta_bin={eta_bin}, phi_bin={phi_bin}): Old JSON={old_val}, New JSON={new_val}, Diff={diff}"
            )

    if differences == 0:
        logging.info(f"No differences found between the two JSON files for map '{map_name}'.")
    else:
        logging.warning(f"Total differing bins for map '{map_name}': {differences}")

    return differences


def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Validate a jet veto map by comparing bin contents between two JSON files."
    )
    parser.add_argument(
        '-o', '--old-json',
        required=True,
        help="Path to the old JSON file (can be .json or .json.gz)."
    )
    parser.add_argument(
        '-n', '--new-json',
        required=True,
        help="Path to the new JSON file (can be .json or .json.gz)."
    )
    parser.add_argument(
        '-m', '--map-name',
        required=True,
        help="Name of the map to validate (e.g., 'jetvetomap')."
    )
    parser.add_argument(
        '-t', '--tolerance',
        type=float,
        default=1e-6,
        help="Tolerance level for bin content differences. Defaults to 1e-6."
    )
    return parser.parse_args()


def main():
    """
    Main function to execute the validation.
    """
    args = parse_arguments()

    old_json_file = args.old_json
    new_json_file = args.new_json
    map_name = args.map_name
    tolerance = args.tolerance

    logging.info(f"Starting validation for map '{map_name}'.")
    logging.info(f"Old JSON file: {old_json_file}")
    logging.info(f"New JSON file: {new_json_file}")
    logging.info(f"Tolerance: {tolerance}")

    # Load histograms from both JSON files
    old_hist = load_json_map(old_json_file, map_name)
    new_hist = load_json_map(new_json_file, map_name)

    # Compare histograms
    differences = compare_histograms(old_hist, new_hist, map_name, tolerance)

    if differences == 0:
        logging.info(f"Validation successful: No differences found for map '{map_name}'.")
    else:
        logging.warning(f"Validation completed: {differences} differing bins found for map '{map_name}'. Please review the discrepancies.")

    sys.exit(0 if differences == 0 else 1)


if __name__ == "__main__":
    main()

