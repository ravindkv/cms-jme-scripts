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
from pathlib import Path
from collections import OrderedDict
from array import array

import ROOT
import tdrstyle_JERC as TDR
from tdrstyle_JERC import (
    UpdatePad, SetAlternative2DColor, tdrCanvas, tdrDiCanvas,
    GettdrCanvasHist, tdrLeg, tdrDraw, fixOverlay
)

# ROOT and style setup
ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(0)
TDR.extraText = '   Preliminary'

# Constants
HIST_NAMES = OrderedDict([
    ('official', 'jetvetomap'),
    ('hot',      'jetvetomap_hot'),
    ('cold',     'jetvetomap_cold'),
])
SKIP_HISTS = {'asymmetry', 'pull', 'hotandcold', 'official', 'all'}
COLOR_RANGE = {'hot': 10, 'cold': 0}
COLOR_VALUES = {
    'eep':   7.5, 'bpix':   7.5, 'fpix':   7.5,
    'hem1516': 8.5, 'hbp2m1': 7,
    'hep17': 3.6,  'hbpw89': 3.5,
    'hbm2':   1.5, 'hbp12':  1,   'qie11': 0.1
}
LEGEND_LABELS = {
    'hot':  'Hot towers',
    'cold': 'Dead channels',
    'eep':  'EE+ region',
    'bpix': 'BPix region',
    'fpix': 'FPix region'
}


def remove_z_axis(hist: ROOT.TH2) -> None:
    """
    Hide the Z-axis color palette on a 2D histogram.
    """
    UpdatePad()
    palette = hist.GetListOfFunctions().FindObject("palette")
    if palette:
        # Move palette off-canvas
        palette.SetX1NDC(10)
        palette.SetX2NDC(10)
    UpdatePad()


def load_histos(file_name: str, file_version: str) -> OrderedDict:
    """
    Load specified histograms from a ROOT file.

    Returns an OrderedDict mapping histogram keys to ROOT.TH2 objects.
    """
    path = Path('root') / f"{file_name}_{file_version}.root"
    print(f"Loading histograms from: {path}")
    if not path.exists():
        print(f"Error: File not found: {path}")
        return OrderedDict()

    root_file = ROOT.TFile(str(path), "READ")
    histos = OrderedDict()
    for key, hname in HIST_NAMES.items():
        hist = root_file.Get(hname)
        if not hist:
            print(f"Warning: '{hname}' not found. Skipping...")
            continue
        hist.SetDirectory(0)
        histos[key] = hist
    root_file.Close()
    return histos


def verify_content(histos: dict) -> None:
    """
    Compare bin contents of 'official' and 'all' histograms and print differences.
    """
    h_official = histos.get('official')
    h_all = histos.get('all')
    if not h_official or not h_all:
        print("Warning: 'official' or 'all' histogram missing; skipping verification.")
        return

    nx = h_official.GetNbinsX() + 1
    ny = h_official.GetNbinsY() + 1
    for ix in range(nx):
        for iy in range(ny):
            off = h_official.GetBinContent(ix, iy)
            allc = h_all.GetBinContent(ix, iy)
            if off != allc:
                print(f"Bin ({ix},{iy}) differs: official={off} vs all={allc}")


def create_canvas(name: str, lumi: str, year: str, ratio: bool = False) -> ROOT.TCanvas:
    """
    Create and return a styled ROOT canvas for 2D (or ratio) plotting.
    """
    TDR.cms_lumi = lumi
    TDR.cms_energy = '13.6' if '22' in year else '13'

    if ratio:
        canv = tdrDiCanvas(
            name, -5.2, 5.2, -3.15, 3.15, 0, 0.2,
            '#eta_{jet}', '#phi_{jet}',
            ScaleText('Excluded fraction', scale=0.7),
            iPos=0
        )
        GettdrCanvasHist(canv.cd(2)).GetYaxis().SetNdivisions(502)
        canv.cd(1)
    else:
        square = TDR.kSquare if 'jetvetomap' in name else TDR.kRectangular
        extra = False if 'jetvetomap' in name else True
        offset = 0.75 if 'jetvetomap' in name else 0.55
        canv = tdrCanvas(
            name, -5.2, 5.2, -3.15, 3.15,
            '#eta_{jet}', '#phi_{jet}',
            square=square, iPos=0, is2D=True, isExtraSpace=extra
        )
        GettdrCanvasHist(canv).GetYaxis().SetTitleOffset(offset)
    return canv


def plot_jet_veto_map(
    histos: dict,
    file_name: str,
    output_dir: Path,
    lumi: str,
    year: str,
    ratio: bool = False
) -> None:
    """
    Plot veto maps (and optional ratio) for the given histograms and save as PNG.
    """
    mode_suffix = "_ratio" if ratio else ""
    canv_name = f"jetvetomap_{file_name}{mode_suffix}"
    canv = create_canvas(canv_name, lumi, year, ratio)

    # Legend setup
    n_items = len(histos) - len(SKIP_HISTS & set(histos.keys()))
    leg_h = 0.045 if ratio else 0.035
    y_top = 0.89 if ratio else 0.81
    leg = tdrLeg(0.18 if ratio else 0.15,
                 y_top - leg_h * n_items,
                 0.35, y_top,
                 leg_h)

    # Plot each histogram
    for key, hist in histos.items():
        if key in SKIP_HISTS:
            continue

        is_hotcold = key in {'hot', 'cold', 'all'}
        SetAlternative2DColor(hist)
        hist.GetZaxis().SetRangeUser(COLOR_RANGE['cold'], COLOR_RANGE['hot'])

        # Replace sentinel bin values
        nx = hist.GetNbinsX() + 1
        ny = hist.GetNbinsY() + 1
        for ix in range(nx):
            for iy in range(ny):
                val = hist.GetBinContent(ix, iy)
                if not is_hotcold and val == 100:
                    hist.SetBinContent(ix, iy, COLOR_VALUES.get(key, 0))
                if val == 100:
                    hist.SetBinContent(ix, iy, COLOR_RANGE['hot'])
                if val == -100:
                    hist.SetBinContent(ix, iy, COLOR_RANGE['cold'] + 0.1)

        if key == 'all':
            hist.SetLineColor(ROOT.kBlack)
            hist.Draw('same box')
        else:
            hist.Draw('same colz')
            # Choose fill color
            if key in ('hot', 'cold', 'all'):
                color = TDR.MyPalette[-1] if key == 'hot' else TDR.MyPalette[0]
            else:
                frac = (COLOR_VALUES.get(key, 0) - COLOR_RANGE['cold']) / (
                    COLOR_RANGE['hot'] - COLOR_RANGE['cold']
                )
                idx = min(int(len(TDR.MyPalette) * frac), len(TDR.MyPalette) - 1)
                color = TDR.MyPalette[idx]
            remove_z_axis(hist)
            hist.SetLineColor(ROOT.kBlack)
            hist.SetFillColor(color)

            label = LEGEND_LABELS.get(key, key)
            leg.AddEntry(hist, label, 'f')

    fixOverlay()

    # Ratio pad drawing
    if ratio:
        href = histos.get('all')
        if not href:
            print("Warning: 'all' histogram missing; cannot draw ratio.")
        else:
            # Prepare ratio histograms
            bins = href.GetXaxis().GetXbins()
            edges = list(bins) if bins.GetSize() else [
                href.GetXaxis().GetBinLowEdge(i + 1)
                for i in range(href.GetNbinsX() + 1)
            ]
            fractions = OrderedDict({
                'hot':  ROOT.TH1F('hot',  'hot',  len(edges)-1, array('d', edges)),
                'cold': ROOT.TH1F('cold', 'cold', len(edges)-1, array('d', edges)),
                'else': ROOT.TH1F('else', 'else', len(edges)-1, array('d', edges)),
                'all':  ROOT.TH1F('all',  'all',  len(edges)-1, array('d', edges)),
            })

            for key, hist in histos.items():
                if key in SKIP_HISTS:
                    continue
                target = key if key in ('hot', 'cold', 'all') else 'else'
                for ix in range(1, len(edges)):
                    removed = sum(
                        hist.GetBinContent(ix, iy) != 0
                        for iy in range(1, hist.GetNbinsY() + 1)
                    )
                    # For 'hot', base on href
                    if key == 'hot':
                        removed = sum(
                            href.GetBinContent(ix, iy) != 0
                            for iy in range(1, href.GetNbinsY() + 1)
                        )
                    removed /= href.GetNbinsY()
                    fractions[target].SetBinContent(ix, removed)

            canv.cd(2)
            for fname, hist in fractions.items():
                lw = 2
                lcolor = ROOT.kBlack
                fstyle = 1001
                fcolor = ROOT.kBlack
                alpha = 0.90

                if fname == 'hot':
                    lcolor = ROOT.kRed + 1
                    fcolor = ROOT.kRed - 9
                elif fname == 'cold':
                    lcolor = ROOT.kAzure + 2
                    fcolor = ROOT.kAzure - 8
                elif fname == 'else':
                    lcolor = ROOT.kOrange + 1
                    fcolor = ROOT.kOrange - 1
                elif fname == 'all':
                    fstyle = 0

                hist.SetLineWidth(lw)
                tdrDraw(hist, 'hist',
                        lcolor=lcolor, fcolor=fcolor,
                        fstyle=fstyle, alpha=alpha)

            fixOverlay()

    # Save output
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{canv_name}.png"
    canv.SaveAs(str(out_file))
    canv.Close()


def main():
    """
    Main entry point: iterate over file versions and produce veto map plots.
    """
    output_dir = Path('Pdfs') / 'VetoMaps'
    versions = [
        {
            'year': 'Summer24Prompt24',
            'file_name': 'Summer24Prompt24_RunBCDEFGHI',
            'file_version': 'V1',
            'lumi_info': '2024 RunBtoI, 109 fb^{-1}'
        },
    ]

    for info in versions:
        histos = load_histos(info['file_name'], info['file_version'])
        if not histos:
            continue
        verify_content(histos)
        plot_jet_veto_map(
            histos,
            info['file_name'],
            output_dir,
            info['lumi_info'],
            info['year'],
            ratio=False
        )
        # To also produce ratio plots, uncomment:
        # plot_jet_veto_map(..., ratio=True)


if __name__ == '__main__':
    main()

