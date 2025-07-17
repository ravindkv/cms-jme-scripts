#!/usr/bin/env python3
"""
Author: Garvita Agarwal
Created: 15th November 2022
Modified: [ChatGPT o1 mini and Ravindra]

Description:
    This script converts 2D jet veto maps stored in ROOT files to JSON format using correctionlib.
    It processes specified veto maps, extracts histogram data, and generates compressed JSON files.
"""

import gzip
import json
import logging
import sys
from pathlib import Path

import numpy as np
import uproot
from correctionlib.schemav2 import Category, CategoryItem, Correction, CorrectionSet, MultiBinning

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def get_content(veto_map_path: str, histogram_name: str) -> MultiBinning:
    """
    Extracts histogram data from a ROOT file and converts it into a MultiBinning schema.

    Args:
        veto_map_path (str): Path to the ROOT file containing the histogram.
        histogram_name (str): Name of the histogram to extract.

    Returns:
        MultiBinning: The histogram data in MultiBinning schema format.
    """
    try:
        with uproot.open(veto_map_path) as file:
            if histogram_name not in file:
                logging.error(f"Histogram '{histogram_name}' not found in file '{veto_map_path}'.")
                sys.exit(1)

            histogram = file[histogram_name].to_hist()
            x_edges, y_edges = histogram.axes.edges

            # Ensure edges are one-dimensional
            x_edges = np.asarray(x_edges).flatten()
            y_edges = np.asarray(y_edges).flatten()

            # Convert edges to lists
            x_edges_list = x_edges.tolist()
            y_edges_list = y_edges.tolist()

            # Debugging: Log the edges' structure
            logging.debug(f"X edges for '{histogram_name}': {x_edges_list}")
            logging.debug(f"Y edges for '{histogram_name}': {y_edges_list}")

            # Validate edges are lists of floats
            if not all(isinstance(edge, (float, int)) for edge in x_edges_list):
                logging.error(f"X edges contain non-float values in histogram '{histogram_name}'.")
                sys.exit(1)
            if not all(isinstance(edge, (float, int)) for edge in y_edges_list):
                logging.error(f"Y edges contain non-float values in histogram '{histogram_name}'.")
                sys.exit(1)

            values = histogram.values().flatten().tolist()

            multi_binning = MultiBinning.parse_obj({
                "inputs": ["eta", "phi"],
                "nodetype": "multibinning",
                "edges": [
                    x_edges_list,
                    y_edges_list,
                ],
                "content": values,
                "flow": "0.0",
            })

            return multi_binning

    except Exception as e:
        logging.error(f"Failed to process histogram '{histogram_name}' in file '{veto_map_path}': {e}")
        sys.exit(1)


def convert_root_to_json(veto_maps: list, output_dir: str = "vetomapsJSON"):
    """
    Converts ROOT histograms to JSON files using correctionlib.

    Args:
        veto_maps (list): List of veto map identifiers.
        output_dir (str, optional): Directory to store the JSON output. Defaults to "vetomapsJSON".
    """
    arr_files = []
    root_files = {}

    for p in veto_maps:
        root_file_path = Path("root") / p / f"{p}.root"
        if not root_file_path.exists():
            logging.error(f"ROOT file '{root_file_path}' does not exist.")
            sys.exit(1)
        root_files[f"{p}_V1"] = str(root_file_path)

    arr_files.append(root_files)

    logging.info("Converting veto maps for the following into JSON:")
    logging.info(json.dumps(arr_files, indent=2))

    for root_files_dict in arr_files:
        corrections = []
        for key, root_file in root_files_dict.items():
            logging.info(f"Processing veto map: {key}")

            # Define metadata for the correction
            name = key
            description = (
                "These are the jet veto maps showing regions with an excess of jets (hot zones) "
                "and lack of jets (cold zones). Using the phi-symmetry of the CMS detector, "
                "these areas with detector and/or calibration issues can be pinpointed."
            )
            version = 1
            inputs = [
                {"name": "type", "type": "string", "description": "Name of the type of veto map. The recommended map for analyses is 'jetvetomap'."},
                {"name": "eta", "type": "real", "description": "Jet eta"},
                {"name": "phi", "type": "real", "description": "Jet phi"},
            ]
            output = {
                "name": "vetomaps",
                "type": "real",
                "description": "Non-zero value for (eta, phi) indicates that the region is vetoed."
            }

            # Extract histograms that do not contain 'trigs' in their names
            try:
                with uproot.open(root_file) as file:
                    histogram_names = [hname.decode() if isinstance(hname, bytes) else hname
                                       for hname in file.keys()
                                       if "trigs" not in hname]
            except Exception as e:
                logging.error(f"Failed to open ROOT file '{root_file}': {e}")
                continue

            if not histogram_names:
                logging.warning(f"No valid histograms found in file '{root_file}'. Skipping.")
                continue

            category_content = []
            for hname in histogram_names:
                # Handle potential suffixes like ";1"
                clean_hname = hname.split(";")[0]
                content = get_content(root_file, hname)
                category_item = CategoryItem.parse_obj({
                    "key": clean_hname,
                    "value": content
                })
                category_content.append(category_item)

            data = Category.parse_obj({
                "nodetype": "category",
                "input": "type",
                "content": category_content,
            })

            # Create Correction object
            correction = Correction.parse_obj({
                "version": version,
                "name": name,
                "description": description,
                "inputs": inputs,
                "output": output,
                "data": data,
            })

            corrections.append(correction)
            logging.info(f"Processed correction for '{key}'.")

        if not corrections:
            logging.warning("No corrections to process for the current set of root files.")
            continue

        # Create CorrectionSet
        correction_set = CorrectionSet(
            schema_version=2,
            corrections=corrections,
            description=(
                f"These are the jet veto maps for {list(root_files_dict.keys())}. "
                "The recommended veto maps to be applied to both data and MC for analysis is 'jetvetomap'."
            )
        )

        # Prepare output directory and file paths
        for key in root_files_dict.keys():
            output_path = Path(output_dir) / key
            output_path.mkdir(parents=True, exist_ok=True)

            json_filename = output_path / "jetvetomaps.json"
            compressed_filename = json_filename.with_suffix(".json.gz")

            # Write JSON to file
            try:
                with json_filename.open("w") as fout:
                    fout.write(correction_set.model_dump_json(exclude_unset=True, indent=2))
                logging.info(f"JSON for '{key}' written at '{json_filename}'.")
            except Exception as e:
                logging.error(f"Failed to write JSON file '{json_filename}': {e}")
                continue

            # Compress the JSON file
            try:
                with json_filename.open('rb') as f_in, gzip.open(compressed_filename, 'wb') as f_out:
                    f_out.writelines(f_in)
                logging.info(f"Compressed and wrote '{compressed_filename}'.")
                json_filename.unlink()  # Remove the original JSON file
            except Exception as e:
                logging.error(f"Failed to compress JSON file '{json_filename}': {e}")
                continue

            logging.info(f"#### Compressed and done writing '{compressed_filename}' \n")

    logging.info("All veto maps have been converted to JSON successfully.")


def main():
    """
    Main function to execute the ROOT to JSON conversion.
    """
    # Define veto maps
    veto_maps = [
        "Summer24Prompt24_RunBCDEFGHI",
        #"Summer23BPixPrompt23_RunD_v1",
        # "Winter24Prompt24_RunF",
    ]

    convert_root_to_json(veto_maps)


if __name__ == "__main__":
    main()

