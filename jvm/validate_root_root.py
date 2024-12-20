#!/usr/bin/env python3
"""
Author: [Your Name]
Created: [Date]

Description:
    This script validates a specific jet veto map by comparing bin contents between two ROOT files.
    It identifies and reports differences in bin contents to ensure the integrity of updates or
    modifications made to the ROOT histograms before announcing them to the CMS collaboration.
"""

import argparse
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

def compare_histograms(old_hist: tuple, new_hist: tuple, histogram_name: str, tolerance: float = 1e-6):
    """
    Compares two histograms and prints differences where the bin content differs beyond a tolerance.

    Args:
        old_hist (tuple): (x_edges, y_edges, bin_contents) from the old ROOT file.
        new_hist (tuple): (x_edges, y_edges, bin_contents) from the new ROOT file.
        histogram_name (str): Name of the histogram being compared.
        tolerance (float, optional): Threshold below which differences are ignored. Defaults to 1e-6.

    Returns:
        int: Number of differing bins.
    """
    x_edges_old, y_edges_old, bin_contents_old = old_hist
    x_edges_new, y_edges_new, bin_contents_new = new_hist

    # Compare bin edges
    if not np.allclose(x_edges_old, x_edges_new, atol=tolerance):
        logging.error(f"X edges mismatch for histogram '{histogram_name}'.")
        sys.exit(1)
    if not np.allclose(y_edges_old, y_edges_new, atol=tolerance):
        logging.error(f"Y edges mismatch for histogram '{histogram_name}'.")
        sys.exit(1)

    num_bins_old = len(bin_contents_old)
    num_bins_new = len(bin_contents_new)

    if num_bins_new != num_bins_old:
        logging.error(f"Number of bins mismatch for histogram '{histogram_name}': Old ROOT has {num_bins_old} bins, New ROOT has {num_bins_new} bins.")
        sys.exit(1)

    differences = 0

    logging.info(f"Comparing histograms for '{histogram_name}':")
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
                f"Difference found in bin (eta_bin={eta_bin}, phi_bin={phi_bin}): Old ROOT={old_val}, New ROOT={new_val}, Diff={diff}"
            )

    if differences == 0:
        logging.info(f"No differences found between the two ROOT files for histogram '{histogram_name}'.")
    else:
        logging.warning(f"Total differing bins for histogram '{histogram_name}': {differences}")

    return differences

def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Validate a jet veto map by comparing bin contents between two ROOT files."
    )
    parser.add_argument(
        '-o', '--old-root',
        required=True,
        help="Path to the old ROOT file."
    )
    parser.add_argument(
        '-n', '--new-root',
        required=True,
        help="Path to the new ROOT file."
    )
    parser.add_argument(
        '-m', '--histogram-name',
        required=True,
        help="Name of the histogram to validate (e.g., 'jetvetomap')."
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

    old_root_file = args.old_root
    new_root_file = args.new_root
    histogram_name = args.histogram_name
    tolerance = args.tolerance

    logging.info(f"Starting validation for histogram '{histogram_name}'.")
    logging.info(f"Old ROOT file: {old_root_file}")
    logging.info(f"New ROOT file: {new_root_file}")
    logging.info(f"Tolerance: {tolerance}")

    # Load histograms from both ROOT files
    old_hist = load_root_histogram(old_root_file, histogram_name)
    new_hist = load_root_histogram(new_root_file, histogram_name)

    # Compare histograms
    differences = compare_histograms(old_hist, new_hist, histogram_name, tolerance)

    if differences == 0:
        logging.info(f"Validation successful: No differences found for histogram '{histogram_name}'.")
    else:
        logging.warning(f"Validation completed: {differences} differing bins found for histogram '{histogram_name}'. Please review the discrepancies.")

    sys.exit(0 if differences == 0 else 1)

if __name__ == "__main__":
    main()

