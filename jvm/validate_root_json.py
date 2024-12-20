#!/usr/bin/env python3
"""
Author: [ChatGPT o1 mini]
Created: [December 20, 2024]
Modified: [Current Date]

Description:
    This script validates a specific jet veto map by comparing bin contents between a ROOT file
    and its corresponding JSON file. It identifies and reports differences in bin contents to
    ensure the integrity of the conversion process.
"""

import argparse
import gzip
import json
import logging
import sys
from pathlib import Path

import numpy as np
import uproot


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def load_root_histogram(root_file_path: str, histogram_name: str):
    """
    Loads a histogram from a ROOT file.

    Args:
        root_file_path (str): Path to the ROOT file.
        histogram_name (str): Name of the histogram to load.

    Returns:
        tuple: (x_edges, y_edges, bin_contents) if successful.

    Raises:
        FileNotFoundError: If the ROOT file does not exist.
        KeyError: If the histogram is not found in the ROOT file.
    """
    try:
        root_path = Path(root_file_path)
        if not root_path.exists():
            raise FileNotFoundError(f"ROOT file '{root_file_path}' does not exist.")

        with uproot.open(root_file_path) as file:
            if histogram_name not in file:
                raise KeyError(f"Histogram '{histogram_name}' not found in '{root_file_path}'.")

            histogram = file[histogram_name].to_hist()
            x_edges, y_edges = histogram.axes.edges
            bin_contents = histogram.values().flatten()

            # Ensure edges are one-dimensional
            x_edges = np.asarray(x_edges).flatten()
            y_edges = np.asarray(y_edges).flatten()

            return x_edges, y_edges, bin_contents

    except Exception as e:
        logging.error(f"Error loading histogram from ROOT file: {e}")
        sys.exit(1)


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

                return x_edges, y_edges, bin_contents

        # If map not found after iterating
        raise KeyError(f"Map '{map_name}' not found in any correction within '{json_file_path}'.")

    except Exception as e:
        logging.error(f"Error loading map from JSON file: {e}")
        # Optionally, print the full traceback for debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)


def compare_histograms(root_hist: tuple, json_hist: tuple, map_name: str, tolerance: float = 1e-6):
    """
    Compares two histograms and prints differences where the bin content differs beyond a tolerance.

    Args:
        root_hist (tuple): (x_edges, y_edges, bin_contents) from ROOT.
        json_hist (tuple): (x_edges, y_edges, bin_contents) from JSON.
        map_name (str): Name of the map being compared.
        tolerance (float, optional): Threshold below which differences are ignored. Defaults to 1e-6.

    Returns:
        int: Number of differing bins.
    """
    x_edges_root, y_edges_root, bin_contents_root = root_hist
    x_edges_json, y_edges_json, bin_contents_json = json_hist

    # Compare bin edges
    if not np.allclose(x_edges_root, x_edges_json, atol=tolerance):
        logging.error(f"X edges mismatch for map '{map_name}'.")
        sys.exit(1)
    if not np.allclose(y_edges_root, y_edges_json, atol=tolerance):
        logging.error(f"Y edges mismatch for map '{map_name}'.")
        sys.exit(1)

    num_bins = len(bin_contents_root)
    if len(bin_contents_json) != num_bins:
        logging.error(f"Number of bins mismatch for map '{map_name}': ROOT has {num_bins}, JSON has {len(bin_contents_json)}.")
        sys.exit(1)

    differences = 0

    logging.info(f"Comparing histograms for map '{map_name}':")
    logging.info(f"Total number of bins: {num_bins}")

    # Determine the number of phi bins from y_edges
    num_phi_bins = len(y_edges_root) - 1

    for idx in range(num_bins):
        root_val = bin_contents_root[idx]
        json_val = bin_contents_json[idx]
        diff = root_val - json_val
        if abs(diff) > tolerance:
            differences += 1
            # Calculate bin indices (assuming eta varies first, then phi)
            eta_bin = (idx // num_phi_bins) + 1
            phi_bin = (idx % num_phi_bins) + 1
            logging.warning(
                f"Difference found in bin (eta_bin={eta_bin}, phi_bin={phi_bin}): ROOT={root_val}, JSON={json_val}, Diff={diff}"
            )

    if differences == 0:
        logging.info(f"No differences found between ROOT and JSON for map '{map_name}'.")
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
        description="Validate a jet veto map by comparing bin contents between a ROOT file and a JSON file."
    )
    parser.add_argument(
        '-r', '--root-file',
        required=True,
        help="Path to the input ROOT file."
    )
    parser.add_argument(
        '-j', '--json-file',
        required=True,
        help="Path to the input JSON file (can be .json or .json.gz)."
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

    root_file = args.root_file
    json_file = args.json_file
    map_name = args.map_name
    tolerance = args.tolerance

    logging.info(f"Starting validation for map '{map_name}'.")
    logging.info(f"ROOT file: {root_file}")
    logging.info(f"JSON file: {json_file}")
    logging.info(f"Tolerance: {tolerance}")

    # Load histograms
    root_hist = load_root_histogram(root_file, map_name)
    json_hist = load_json_map(json_file, map_name)

    # Compare histograms
    differences = compare_histograms(root_hist, json_hist, map_name, tolerance)

    if differences == 0:
        logging.info(f"Validation successful: No differences found for map '{map_name}'.")
    else:
        logging.warning(f"Validation completed: {differences} differing bins found for map '{map_name}'. Please review the discrepancies.")

    sys.exit(0 if differences == 0 else 1)


if __name__ == "__main__":
    main()

