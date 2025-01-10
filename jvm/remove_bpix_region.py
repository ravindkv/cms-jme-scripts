import ROOT
import sys

def remove_bpix_region(input_filename, output_filename):
    # Open the input ROOT file
    input_file = ROOT.TFile.Open(input_filename, "READ")
    if not input_file or input_file.IsZombie():
        print(f"Error: Cannot open input file '{input_filename}'.")
        sys.exit(1)
    
    print(f"Opened input file: {input_filename}")

    removeFrom = "jetvetomap_cold"
    tobeRemoved = "jetvetomap_bpix"
    # Retrieve the histograms
    jetvetomap = input_file.Get(removeFrom)
    jetvetomap_bpix = input_file.Get(tobeRemoved)

    if not jetvetomap:
        print(f"Error: '{removeFrom}' histogram not found in the input file.")
        input_file.Close()
        sys.exit(1)
    
    if not jetvetomap_bpix:
        print("Error: 'jetvetomap_bpix' histogram not found in the input file.")
        input_file.Close()
        sys.exit(1)
    
    print(f"Retrieved '{removeFrom}' and {tobeRemoved} histograms.")

    # Clone the jetvetomap to modify it
    modified_jetvetomap = jetvetomap.Clone(removeFrom)
    modified_jetvetomap.SetTitle(f"{removeFrom} with {tobeRemoved} removed")
    modified_jetvetomap.SetDirectory(0)  # Detach from any ROOT directory

    # Check that both histograms have the same binning
    if (jetvetomap.GetNbinsX() != jetvetomap_bpix.GetNbinsX() or
        jetvetomap.GetNbinsY() != jetvetomap_bpix.GetNbinsY()):
        print(f"Error: '{removeFrom}' and {tobeRemoved} have different binning.")
        input_file.Close()
        sys.exit(1)
    
    nbinsX = jetvetomap.GetNbinsX()
    nbinsY = jetvetomap.GetNbinsY()

    print(f"Histogram dimensions: X bins = {nbinsX}, Y bins = {nbinsY}")

    # Loop over all bins and remove the region
    for ix in range(1, nbinsX + 1):
        for iy in range(1, nbinsY + 1):
            bpix_content = jetvetomap_bpix.GetBinContent(ix, iy)
            if bpix_content > 0:
                # Set the corresponding bin in jetvetomap to zero
                modified_jetvetomap.SetBinContent(ix, iy, 0)

    print(f"Removed {tobeRemoved} from '{removeFrom}'.")

    # Open the output ROOT file
    output_file = ROOT.TFile.Open(output_filename, "RECREATE")
    if not output_file or output_file.IsZombie():
        print(f"Error: Cannot create output file '{output_filename}'.")
        input_file.Close()
        sys.exit(1)
    
    print(f"Opened output file: {output_filename}")

    # Set the output file as the current directory
    output_file.cd()

    # Iterate over all keys in the input file and write them to the output file
    keys = input_file.GetListOfKeys()
    for key in keys:
        obj = key.ReadObj()
        obj_name = obj.GetName()
        obj_class = obj.IsA().GetName()

        if obj_name == removeFrom:
            # Write the modified jetvetomap
            modified_jetvetomap.Write()
            print(f"Written modified '{removeFrom}' to output file.")
        elif obj.InheritsFrom("TH1") or obj.InheritsFrom("TH2") or obj.InheritsFrom("TH3"):
            # Handle histogram objects
            obj_clone = obj.Clone(obj_name)
            obj_clone.SetDirectory(0)  # Detach from any ROOT directory
            obj_clone.Write()
            print(f"Written '{obj_name}' as '{obj.GetName()}' to output file.")
        else:
            # For non-histogram objects (e.g., directories), write them as-is
            obj.Write()
            print(f"Written non-histogram object '{obj_name}' to output file.")

    # Close the files
    output_file.Close()
    input_file.Close()

    print("All histograms and objects have been written to the output file successfully.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python remove_bpix_region.py <input_root_file> <output_root_file>")
        print("Example: python remove_bpix_region.py Summer23BPixPrompt23_RunD_v1.root Summer23BPixPrompt23_RunD_v1_modified.root")
        sys.exit(1)
    
    # Define input and output file names from command-line arguments
    input_root_file = sys.argv[1]
    output_root_file = sys.argv[2]

    # Call the function to process the ROOT file
    remove_bpix_region(input_root_file, output_root_file)

