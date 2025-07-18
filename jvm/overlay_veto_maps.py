#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Updated script for plotting veto maps, originally from:
# https://gitlab.cern.ch/cms-jetmet/JERCProtoLab/-/blob/master/macros/plotting/PlotVetoMaps.py?ref_type=heads
#
# USAGE: python overlay_veto_maps.py
#
# Requires ROOT, tdrstyle_JERC, and the appropriate environment setup.
#

import os
import ROOT
from array import array
from collections import OrderedDict
from pathlib import Path

from tdrstyle_JERC import *
import tdrstyle_JERC as TDR

ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(0)

TDR.extraText = '   Preliminary'

def remove_z_axis(hist):
    """
    Remove the Z-axis (color palette) from a 2D histogram.

    Args:
        hist (ROOT.TH2): The histogram from which to remove the palette.
    """
    UpdatePad()
    palette = hist.GetListOfFunctions().FindObject("palette")
    if palette is None:
        return
    # Move palette off-canvas (effectively hide it)
    palette.SetX1NDC(10)
    palette.SetX2NDC(10)
    UpdatePad()


class PlotVetoMaps:
    """
    A class to load, verify, and plot jet veto maps (2D histograms).

    Attributes:
        year (str): The data-taking or production year (e.g., 'Winter24Prompt24').
        file_name (str): The base name of the input ROOT file.
        file_version (str): The version string of the input ROOT file.
        lumi_info (str): The luminosity string to display on plots.
        hnames (OrderedDict): The names of the histograms to retrieve from file.
        output_path (str): The directory path where plots will be saved.
        histos (OrderedDict): Dictionary of loaded ROOT histograms.
    """

    def __init__(self, year, file_name, file_version, lumi_info):
        """
        Constructor for PlotVetoMaps.

        Args:
            year (str): The data-taking or production year (e.g., 'Winter24Prompt24').
            file_name (str): The base name of the input ROOT file.
            file_version (str): The version string of the input ROOT file.
            lumi_info (str): The luminosity string to display on plots.
        """
        self.year = year
        self.file_name = file_name
        self.file_version = file_version
        self.lumi_info = lumi_info

        # Define histogram names to extract from the input ROOT file
        self.hnames = OrderedDict([
            # Uncomment if needed:
            # ('asymmetry',  'jetasymmetrymap'),
            # ('pull',       'jetpullsummap'),
            ('official', 'jetvetomap'),
            # ('hotandcold', 'jetvetomap_hotandcold'),
             ('hot',        'jetvetomap_hot'),
             ('cold',       'jetvetomap_cold'),
            # ('eep',        'jetvetomap_eep'),
            # ('hem1516',    'jetvetomap_hem1516'),
            # ('hbp2m1',     'jetvetomap_hbp2m1'),
            # ('hep17',      'jetvetomap_hep17'),
            # ('hbpw89',     'jetvetomap_hbpw89'),
            # ('hbm2',       'jetvetomap_hbm2'),
            # ('hbp12',      'jetvetomap_hbp12'),
            # ('qie11',      'jetvetomap_qie11'),
            # ('bpix',       'jetvetomap_bpix'),
            #('fpix', 'jetvetomap_fpix'),
            #('all', 'jetvetomap_all'),
        ])

        # Create output directory
        self.output_path = Path('Pdfs') / 'VetoMaps'
        self.output_path.mkdir(parents=True, exist_ok=True)

        # Load histograms
        self.histos = OrderedDict()
        self.load_histos()

    def load_histos(self):
        """
        Load histograms from the specified ROOT file and store them in self.histos.
        """
        # Adjust input path to your directory structure as needed
        input_path = Path('root') / f"{self.file_name}_{self.file_version}.root"
        print(f"Loading histograms from: {input_path}")
        if not input_path.exists():
            print(f"Error: File not found: {input_path}")
            return

        root_file = ROOT.TFile(str(input_path), "READ")
        for name, hname in self.hnames.items():
            hist = root_file.Get(hname)
            # If the histogram doesn't exist in file, skip it
            if not hist:
                print(f"Warning: Histogram '{hname}' not found in {input_path}. Skipping...")
                continue
            hist.SetDirectory(0)
            self.histos[name] = hist

        root_file.Close()

    def verify_content(self):
        """
        Verify that the contents of 'official' and 'all' histograms match, 
        printing differences if found.
        """
        h_official = self.histos.get('official')
        h_all = self.histos.get('all')
        if not h_official or not h_all:
            print("Warning: 'official' or 'all' histogram not found. Cannot verify content.")
            return

        # Loop over bins and compare
        for x in range(h_official.GetNbinsX() + 1):
            for y in range(h_official.GetNbinsY() + 1):
                off_content = h_official.GetBinContent(x, y)
                all_content = h_all.GetBinContent(x, y)
                if off_content != all_content:
                    print(
                        f"Different content in bin {x}-{y}: "
                        f"{off_content} vs {all_content}"
                    )

    def create_canvas(self, canv_name):
        """
        Create a tdr canvas for 2D plotting.

        Args:
            canv_name (str): Name of the canvas.

        Returns:
            ROOT.TCanvas: The created canvas.
        """
        # Set luminosity info
        TDR.cms_lumi = self.lumi_info
        # Determine collision energy for label
        TDR.cms_energy = '13.6' if '22' in self.year else '13'

        # Decide on canvas shape and offset
        if 'jetvetomap' in canv_name:
            square = kSquare
            is_extra_space = False
            offset = 0.75
        else:
            square = kRectangular
            is_extra_space = True
            offset = 0.55

        # Check if ratio plot
        if "ratio" in canv_name:
            canv = tdrDiCanvas(
                canv_name, -5.2, 5.2, -3.15, 3.15, 0, 0.2,
                '#eta_{jet}', '#phi_{jet}',
                ScaleText('Excluded fraction', scale=0.7),
                iPos=0
            )
            GettdrCanvasHist(canv.cd(2)).GetYaxis().SetNdivisions(502)
            canv.cd(1)
        else:
            canv = tdrCanvas(
                canv_name, -5.2, 5.2, -3.15, 3.15,
                '#eta_{jet}', '#phi_{jet}',
                square=square, iPos=0, is2D=True, isExtraSpace=is_extra_space
            )
            # Adjust y-axis offset for title
            GettdrCanvasHist(canv).GetYaxis().SetTitleOffset(offset)

        return canv

    def plot_jet_veto_map(self, mode=""):
        """
        Plot jet veto map(s) from the loaded histograms.

        Args:
            mode (str, optional): If "ratio", produces a ratio plot. Defaults to "".
        """
        is_ratio = ("ratio" in mode)
        canv_name = f'jetvetomap_{self.file_name}'
        if is_ratio:
            canv_name += "_ratio"

        # Histograms we do not plot in this method
        skip_hists = ['asymmetry', 'pull', 'hotandcold', 'official', 'all']

        # Create the canvas
        canv = self.create_canvas(canv_name)

        # Build legend
        # Count how many histos we'll actually plot
        n_hists = len(set(self.histos.keys()) - set(skip_hists))
        leg_height = 0.035 if not is_ratio else 0.045
        y2_legend = 0.81 if not is_ratio else 0.89
        leg = tdrLeg(0.15, y2_legend - leg_height * n_hists, 0.35, y2_legend, 0.035)

        if is_ratio:
            leg = tdrLeg(
                0.18, y2_legend - leg_height * n_hists,
                0.35, y2_legend, 0.05
            )

        # Predefine value ranges for coloring
        values = {
            'hot': 10, 'cold': 0, 'eep': 7.5, 'bpix': 7.5, 'fpix': 7.5,
            'hem1516': 8.5, 'hbp2m1': 7,
            'hep17': 3.6, 'hbpw89': 3.5,
            'hbm2': 1.5, 'hbp12': 1, 'qie11': 0.1
        }

        # Plot each relevant histogram
        for name, hist in self.histos.items():
            if name in skip_hists:
                continue

            # Decide coloring
            is_hotcold = (name in ['hot', 'cold', 'all'])
            SetAlternative2DColor(hist)
            hist.GetZaxis().SetRangeUser(values['cold'], values['hot'])

            # Replace "100"/"-100" with the relevant color-coded bin content
            for x in range(hist.GetNbinsX() + 1):
                for y in range(hist.GetNbinsY() + 1):
                    bin_content = hist.GetBinContent(x, y)
                    if (not is_hotcold) and (bin_content == 100):
                        hist.SetBinContent(x, y, values[name])
                    if bin_content == 100:
                        hist.SetBinContent(x, y, values['hot'])
                    if bin_content == -100:
                        hist.SetBinContent(x, y, values['cold'] + 0.1)

            # Draw
            if name == 'all':
                # Draw boundary
                hist.SetLineColor(ROOT.kBlack)
                hist.Draw('same box')
            else:
                hist.Draw('same colz')
                color = TDR.MyPalette[-1] if name == 'hot' else TDR.MyPalette[0]
                if not is_hotcold:
                    # Map color based on fraction between cold/hot
                    fraction = (values[name] - values['cold']) / (values['hot'] - values['cold'])
                    index = int(len(TDR.MyPalette) * fraction)
                    color = TDR.MyPalette[min(index, len(TDR.MyPalette) - 1)]
                remove_z_axis(hist)
                hist.SetLineColor(ROOT.kBlack)
                hist.SetFillColor(color)

                # Legend text
                legend_name = name
                if name == 'hot':
                    legend_name = 'Hot towers'
                if name == 'cold':
                    legend_name = 'Dead channels'
                if name == 'eep':
                    legend_name = 'EE+ region'
                if name == 'bpix':
                    legend_name = 'BPix region'
                if name == 'fpix':
                    legend_name = 'FPix region'

                leg.AddEntry(hist, legend_name, 'f')

        fixOverlay()

        if is_ratio:
            # Ratio mode: second pad
            href = self.histos.get('all')
            if not href:
                print("Warning: 'all' histogram not found. Cannot create ratio.")
            else:
                # Initialize ratio histograms
                bins = href.GetXaxis().GetXbins()
                fractions = OrderedDict({
                    'hot':  ROOT.TH1F('hot',  'hot',  len(bins) - 1, array('d', bins)),
                    'cold': ROOT.TH1F('cold', 'cold', len(bins) - 1, array('d', bins)),
                    'else': ROOT.TH1F('else', 'else', len(bins) - 1, array('d', bins)),
                    'all':  ROOT.TH1F('all',  'all',  len(bins) - 1, array('d', bins)),
                })

                for name, hist in self.histos.items():
                    if name in skip_hists:
                        continue
                    is_hotcold = (name in ['hot', 'cold', 'all'])
                    frac_name = name if is_hotcold else 'else'
                    for x in range(1, len(bins)):
                        removed = sum(
                            1 for y in range(1, hist.GetNbinsY() + 1)
                            if hist.GetBinContent(x, y) != 0
                        )
                        # If it's 'hot', consider 'all' bins?
                        if name == 'hot':
                            removed = sum(
                                1 for y in range(1, href.GetNbinsY() + 1)
                                if href.GetBinContent(x, y) != 0
                            )
                        # Normalize to total Y bins
                        removed /= href.GetNbinsY()
                        fractions[frac_name].SetBinContent(x, removed)

                # Draw the second pad with ratio histos
                canv.cd(2)
                for f_name, frac in fractions.items():
                    color_main = ROOT.kBlack
                    fill_color = ROOT.kBlack
                    fill_style = 1001
                    if f_name == 'all':
                        fill_style = 0  # no fill
                    if f_name == 'hot':
                        color_main = ROOT.kRed + 1
                        fill_color = ROOT.kRed - 9
                    elif f_name == 'cold':
                        color_main = ROOT.kAzure + 2
                        fill_color = ROOT.kAzure - 8
                    elif f_name == 'else':
                        color_main = ROOT.kOrange + 1
                        fill_color = ROOT.kOrange - 1

                    frac.SetLineWidth(2)
                    tdrDraw(frac, 'hist', lcolor=color_main, fcolor=fill_color, fstyle=fill_style, alpha=0.90)

                fixOverlay()

        # Save the canvas
        save_path = self.output_path / f"{canv_name}.png"
        canv.SaveAs(str(save_path))
        canv.Close()

    def plot(self):
        """
        Main plotting method: verify the histogram content
        and produce standard veto map plots.
        """
        # Verify the content consistency of 'official' and 'all'
        self.verify_content()

        # Example: If you need asymmetry or pull plots, enable these:
        # self.PlotAsymmetry(mode='asymmetry')
        # self.PlotAsymmetry(mode='pull')

        # Plot the standard jet veto map
        self.plot_jet_veto_map(mode="")

        # Optionally, plot ratio version:
        # self.plot_jet_veto_map(mode="ratio")


def main():
    """
    Main function to run over a list of file versions and produce the plots.
    """
    file_versions = [
        #{'year': 'Winter22Run3', 'file_name': 'Winter22Run3_RunCD', 'file_version': 'v1', 'lumi_info': '2022 RunCD, 7.6 fb^{-1}'},
        #{'year': 'Summer22Run3', 'file_name': 'Summer22_23Sep2023_RunCD',  'file_version': 'v1', 'lumi_info': '2022, 5.7 fb^{-1}'},
        #{'year': 'Summer22EERun3', 'file_name': 'Summer22EE_23Sep2023_RunEFG','file_version': 'v1', 'lumi_info': '2022, 27 fb^{-1}'},
        #{'year': 'Summer23Run3', 'file_name': 'Summer23Prompt23_RunC','file_version': 'v1', 'lumi_info': '2023, 18 fb^{-1}'},
        #{'year': 'Summer23BPixRun3', 'file_name': 'Summer23BPixPrompt23_RunD','file_version': 'v1', 'lumi_info': '2023, 9 fb^{-1}'},
        #{'year': 'Winter24Prompt24', 'file_name': 'Winter24Prompt24_2024BCDEFGHI', 'file_version': 'v1_tmp', 'lumi_info': '2024 RunBtoI, 109 fb^{-1}'},
        {'year': 'Summer24Prompt24', 'file_name': 'Summer24Prompt24_RunBCDEFGHI', 'file_version': 'V1', 'lumi_info': '2024 RunBtoI, 109 fb^{-1}'},
       #  {'year': 'Summer20UL18', 'file_name': 'hotjets-UL18',       'file_version': 'v1', 'lumi_info': '2018, 59.8 fb^{-1}'},
       #  {'year': 'Summer20UL17', 'file_name': 'hotjets-UL17',       'file_version': 'v1', 'lumi_info': '2017, 41.5 fb^{-1}'},
       #  {'year': 'Summer20UL16APV', 'file_name': 'hotjets-UL16',       'file_version': 'v1', 'lumi_info': '2016, 36.3 fb^{-1}'},
       #  {'year': 'Summer20Run2', 'file_name': 'hotjets-Run2',       'file_version': 'v1', 'lumi_info': 'Run2, 138 fb^{-1}'},
    ]

    for info in file_versions:
        pvm = PlotVetoMaps(**info)
        pvm.plot()


if __name__ == '__main__':
    main()

