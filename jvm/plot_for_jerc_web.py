#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMS TDR‑style jet‑veto overlay, “boxes only” version:

  • Read `jetvetomap`, `jetvetomap_hot`, `jetvetomap_cold`  
  • Use `tdrCanvas`’s own axes + CMS header  
  • Overlay hot/cold bins via `tdrDraw(...)`  
  • Call `UpdatePad()` & `fixOverlay()` for perfect TDR layering  
  • Save as jetvetomap_hotcold.png
"""

import ROOT
import tdrstyle_JERC as TDR
from tdrstyle_JERC import (
    UpdatePad, SetAlternative2DColor,
    tdrCanvas, tdrLeg, GettdrCanvasHist,
    tdrDraw, fixOverlay
)

# === 1) CMS style setup ===
ROOT.gROOT.SetBatch(True)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(0)

TDR.extraText  = "   Preliminary"
TDR.cms_lumi   = "   ,2024 RunBtoI, 109fb^{-1}"
TDR.cms_energy = "13.6"


def load_histos(filename: str):
    f = ROOT.TFile.Open(filename, "READ")
    if not f or f.IsZombie():
        raise IOError(f"Cannot open '{filename}'")
    master = f.Get("jetvetomap")
    hot    = f.Get("jetvetomap_hot")
    cold   = f.Get("jetvetomap_cold")
    for obj, name in ((master, "jetvetomap"),
                      (hot,    "jetvetomap_hot"),
                      (cold,   "jetvetomap_cold")):
        if not obj:
            raise KeyError(f"Histogram '{name}' not found")
        obj.SetDirectory(0)
    f.Close()
    return master, hot, cold


def build_masks(master, hot, cold):
    hotMask  = master.Clone("hotMask")
    coldMask = master.Clone("coldMask")
    hotMask .Reset("ICESM")
    coldMask.Reset("ICESM")
    nx, ny = master.GetNbinsX(), master.GetNbinsY()
    for ix in range(1, nx+1):
        for iy in range(1, ny+1):
            if master.GetBinContent(ix, iy) == 0:
                continue
            if hot.GetBinContent(ix, iy) != 0:
                hotMask.SetBinContent(ix, iy, 1)
            elif cold.GetBinContent(ix, iy) != 0:
                coldMask.SetBinContent(ix, iy, 1)
    return hotMask, coldMask


def draw_map(master, hotMask, coldMask, output_name: str):
    # 1) Make a TDR canvas (frame + CMS header)
    c = tdrCanvas(
        "c", -5.2, 5.2, -3.15, 3.15,
        "#eta_{jet}", "#phi_{jet}",
        square=TDR.kSquare, iPos=0,
        is2D=True, isExtraSpace=True
    )
    c.SetRightMargin(0.10); 

    # 2) Force a pad update so we can layer correctly
    UpdatePad()

    # 3) Grab the empty frame & label it
    frame = GettdrCanvasHist(c)
    frame.SetTitle("Jet Veto Map;#eta_{jet};#phi_{jet}")
    frame.GetYaxis().SetTitleOffset(0.8);

    # 4) (Optional) set an alt color palette if you ever draw colz
    #    but here we stay boxes-only:
    # SetAlternative2DColor(master)

    # 5) Overlay hot bins via tdrDraw
    tdrDraw(
        hotMask, "box",
        lcolor=ROOT.kRed+1, fcolor=ROOT.kRed-3,
        fstyle=1001, alpha=1.0
    )

    # 6) Overlay cold bins via tdrDraw
    tdrDraw(
        coldMask, "box",
        lcolor=ROOT.kAzure+1, fcolor=ROOT.kAzure-7,
        fstyle=1001, alpha=1.0
    )

    # 7) Legend
    leg = tdrLeg(0.15, 0.75, 0.35, 0.82, 0.035)
    leg.AddEntry(hotMask,  "Hot towers",    "f")
    leg.AddEntry(coldMask, "Dead channels", "f")
    leg.Draw()

    # 8) Final overlay fix and save
    fixOverlay()
    c.SaveAs(output_name)
    c.Close()



def main():
    master, hot, cold = load_histos("root/Summer24Prompt24_RunBCDEFGHI_V1.root")
    hotMask, coldMask = build_masks(master, hot, cold)
    draw_map(master, hotMask, coldMask, "jetvetomap_hotcold.png")


if __name__ == "__main__":
    main()

