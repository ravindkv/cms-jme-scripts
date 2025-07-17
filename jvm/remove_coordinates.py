import ROOT
import sys

# Hard-coded regions to remove: list of (etaMin, etaMax, phiMin, phiMax)
REGIONS = [
    (-2.043, -1.566, 2.443461, 2.7925268),
    (-2.043, -1.83,  2.7925268, 3.0543262)
]

def remove_regions(input_filename, output_filename, hist_name, regions):
    # Open the input ROOT file
    input_file = ROOT.TFile.Open(input_filename, "READ")
    if not input_file or input_file.IsZombie():
        print(f"Error: Cannot open input file '{input_filename}'.")
        sys.exit(1)
    print(f"Opened input file: {input_filename}")

    # Retrieve the histogram
    h2 = input_file.Get(hist_name)
    if not h2:
        print(f"Error: Histogram '{hist_name}' not found in the input file.")
        input_file.Close()
        sys.exit(1)
    print(f"Retrieved histogram '{hist_name}'.")

    # Clone to modify, keep original name and title
    modified = h2.Clone()
    modified.SetDirectory(0)

    # Access binning and axes
    xaxis = modified.GetXaxis()
    yaxis = modified.GetYaxis()
    nbinsX = modified.GetNbinsX()
    nbinsY = modified.GetNbinsY()
    print(f"Histogram dimensions: X bins = {nbinsX}, Y bins = {nbinsY}")

    # Loop over bins and zero out regions
    removed_bins = 0
    for ix in range(1, nbinsX + 1):
        eta = xaxis.GetBinCenter(ix)
        for iy in range(1, nbinsY + 1):
            phi = yaxis.GetBinCenter(iy)
            for eta_min, eta_max, phi_min, phi_max in regions:
                if eta_min < eta < eta_max and phi_min < phi < phi_max:
                    modified.SetBinContent(ix, iy, 0)
                    removed_bins += 1
                    break
    print(f"Zeroed out {removed_bins} bins within specified regions.")

    # Write to output file
    output_file = ROOT.TFile.Open(output_filename, "RECREATE")
    if not output_file or output_file.IsZombie():
        print(f"Error: Cannot create output file '{output_filename}'.")
        input_file.Close()
        sys.exit(1)
    print(f"Opened output file: {output_filename}")

    output_file.cd()

    # Copy all objects, replacing the target histogram with modified
    for key in input_file.GetListOfKeys():
        kname = key.GetName()   # this is “jetasymmetrymap” (or “jetvetomap_hot”, etc.)
        obj   = key.ReadObj()
        
        if kname == hist_name:
            modified.Write(kname)             # write your zeroed‐out jetvetomap
        else:
            obj.Write(kname)                  # write every other object under its original key
        print(f"Written '{kname}' to output file.")


    output_file.Close()
    input_file.Close()
    print("All objects have been written to the output file successfully.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python remove_coordinates.py <input_root_file> <output_root_file> <hist_name>")
        sys.exit(1)

    input_root_file = sys.argv[1]
    output_root_file = sys.argv[2]
    histogram_name = sys.argv[3]

    remove_regions(input_root_file, output_root_file, histogram_name, REGIONS)

