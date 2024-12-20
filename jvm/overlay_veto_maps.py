# original script: https://gitlab.cern.ch/cms-jetmet/JERCProtoLab/-/blob/master/macros/plotting/PlotVetoMaps.py?ref_type=heads

import os, ROOT
ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.gStyle.SetOptStat(0)
ROOT.gStyle.SetOptFit(0)
from array import array
from collections import OrderedDict
from tdrstyle_JERC import *
import tdrstyle_JERC as TDR
TDR.extraText  = '   Preliminary'

def RemoveZAxis(hist):
    UpdatePad()
    palette = hist.GetListOfFunctions().FindObject("palette")
    if palette == None:
        return
    palette.SetX1NDC(10)
    palette.SetX2NDC(10)
    UpdatePad()

class PlotVetoMaps():
    def __init__(self, year, file_name, file_version, lumi_info):
        self.hnames = OrderedDict([
            #('asymmetry',  'jetasymmetrymap'),
            #('pull',       'jetpullsummap'),
            ('official',   'jetvetomap'),
            #('hotandcold', 'jetvetomap_hotandcold'),
            #('hot',        'jetvetomap_hot'),
            #('cold',       'jetvetomap_cold'),
            #('eep',        'jetvetomap_eep'),
            #('hem1516',    'jetvetomap_hem1516'),
            #('hbp2m1',     'jetvetomap_hbp2m1'),
            #('hep17',      'jetvetomap_hep17'),
            #('hbpw89',     'jetvetomap_hbpw89'),
            #('hbm2',       'jetvetomap_hbm2'),
            #('hbp12',      'jetvetomap_hbp12'),
            #('qie11',      'jetvetomap_qie11'),
            #('bpix',       'jetvetomap_bpix'),
            ('fpix',       'jetvetomap_fpix'),
            ('all',        'jetvetomap_all'),
            ])
        self.year = year
        self.file_name = file_name
        self.file_version = file_version
        self.lumi_info = lumi_info
        self.outputPath = 'Pdfs/VetoMaps/'
        os.system('mkdir -p '+self.outputPath)
        self.LoadHistos()

    def LoadHistos(self):
        #inputPath = '../../'+self.year+'/jet_veto_maps/'+self.file_name+'_'+self.file_version+'.root'
        inputPath = 'root/'+self.file_name+'_'+self.file_version+'.root'
        print(inputPath)
        f_ = ROOT.TFile(inputPath)
        self.histos = OrderedDict()
        for name,hname in self.hnames.items():
            self.histos[name] = f_.Get(hname)
            if self.histos[name]==None:
                del self.histos[name]
                continue
            self.histos[name].SetDirectory(0)
        f_.Close()

    def VerifyContent(self):
        h_official = self.histos['official']
        h_all = self.histos['all']
        for x in range(h_official.GetNbinsX()+1):
            for y in range(h_official.GetNbinsY()+1):
                if h_official.GetBinContent(x,y)!=h_all.GetBinContent(x,y):
                    print('Different content in bin '+str(x)+'-'+str(y)+': '+str(h_official.GetBinContent(x,y))+' '+str(h_all.GetBinContent(x,y)))

    def CreateCanvas(self,canvName):
        TDR.cms_lumi = self.lumi_info
        TDR.cms_energy = '13.6' if '22' in self.year else '13'
        square, isExtraSpace, offset = (kSquare, False, 0.75) if 'jetvetomap' in canvName else (kRectangular, True, 0.55)
        if "ratio" in canvName:
            canv = tdrDiCanvas(canvName, -5.2, 5.2, -3.15, 3.15,0,0.2,'#eta_{jet}', '#phi_{jet}', ScaleText('Excluded fraction', scale = 0.7), iPos=0)
            GettdrCanvasHist(canv.cd(2)).GetYaxis().SetNdivisions(502)
            canv.cd(1)
        else:
            canv = tdrCanvas(canvName, -5.2, 5.2, -3.15, 3.15,'#eta_{jet}', '#phi_{jet}', square=square, iPos=0, is2D=True, isExtraSpace=isExtraSpace)
            GettdrCanvasHist(canv).GetYaxis().SetTitleOffset(offset)
        return canv

    def PlotAsymmetry(self, mode='asymmetry'):
        canvName = mode+'map_'+self.file_name
        canv = self.CreateCanvas(canvName)
        if not mode in self.histos: return
        hist_ref = self.histos[mode]
        SetAlternative2DColor(hist_ref)
        hist_ref.GetZaxis().SetTitle(mode.capitalize())
        hist_ref.Draw('same colz')
        #palette = hist_ref.GetListOfFunctions().FindObject("palette")
        #palette.SetX1(5.27)
        #palette.SetX2(5.9)
        #palette.SetY1(-3.15)
        #palette.SetY2(3.15)
        hist_veto_map = self.histos['hotandcold']
        hist_veto_map.SetLineColor(ROOT.kBlack)
        hist_veto_map.Draw('same box')
        fixOverlay()
        canv.SaveAs(os.path.join(self.outputPath,canvName+'.png'))
        canv.Close()

    def PlotJetVetoMap(self, mode=""):
        isRatio = "ratio" in mode
        canvName = 'jetvetomap_'+self.file_name
        if isRatio:
            canvName += "_ratio"
        skip_hists = ['asymmetry','pull','hotandcold', 'official', 'all']
        canv = self.CreateCanvas(canvName)
        nhists = len((set(self.histos.keys()))-set(skip_hists))
        leg = tdrLeg(0.15,0.91-0.035*(nhists),0.35,0.91, 0.035)
        if isRatio:
            leg = tdrLeg(0.18,0.89-0.045*(nhists),0.35,0.89, 0.05)
        values = { 'hot': 10, 'cold': 0, 'eep': 7.5, 'bpix': 7.5, 'fpix': 7.5,
                  'hem1516': 8.5, 'hbp2m1': 7,
                  'hep17': 3.6, 'hbpw89':3.5,
                  'hbm2':1.5, 'hbp12':1, 'qie11':0.1}
        hists = {}
        for name,hist in self.histos.items():
            if name in skip_hists: continue
            ishotcold = name=='hot' or name=='cold' or name=='all'
            SetAlternative2DColor(hist)
            hist.GetZaxis().SetRangeUser(values['cold'],values['hot'])
            for x in range(hist.GetNbinsX()+1):
                for y in range(hist.GetNbinsY()+1):
                    if not ishotcold and hist.GetBinContent(x,y)==100: hist.SetBinContent(x,y,values[name])
                    if hist.GetBinContent(x,y)==100: hist.SetBinContent(x,y,values['hot'])
                    if hist.GetBinContent(x,y)==-100: hist.SetBinContent(x,y,values['cold']+0.1)
            if name == 'all':
                hist.SetLineColor(ROOT.kBlack)
                hist.Draw('same box')
            else:
                hist.Draw('same colz')
                color = TDR.MyPalette[-1] if name=='hot' else TDR.MyPalette[0]
                if not ishotcold:
                    color = TDR.MyPalette[int(len(TDR.MyPalette)*values[name]/(values['hot']-values['cold']))]
                RemoveZAxis(hist)
                hist.SetLineColor(rt.kBlack)
                hist.SetFillColor(color)
                legname = name
                if name=='hot': legname = 'Hot towers'
                if name=='cold': legname = 'Dead channels'
                if name=='eep': legname = 'EE+ region'
                if name=='bpix': legname = 'BPix region'
                if name=='fpix': legname = 'FPix region'
                leg.AddEntry(hist,legname,'f')
            hists[name] = hist
        fixOverlay()
        if isRatio:
            href = self.histos['all']
            bins = href.GetXaxis().GetXbins()
            fractions = OrderedDict()
            for name in ['hot', 'cold', 'else', 'all']:
                fractions[name] = rt.TH1F(name,name, len(bins)-1, array('d',bins))
            for name, hist in self.histos.items():
                if name in skip_hists: continue
                ishotcold = name=='hot' or name=='cold' or name=='all'
                frac_name = name if ishotcold else 'else'
                for x in range(len(bins)+1):
                    removed = sum(1 for y in range(1, hist.GetNbinsY()+1) if (hist.GetBinContent(x,y)!=0))
                    if name == 'hot':
                        removed = sum(1 for y in range(1, href.GetNbinsY()+1) if (href.GetBinContent(x,y)!=0))
                    removed /= href.GetNbinsY()
                    fractions[frac_name].SetBinContent(x,removed)
            canv.cd(2)
            for name, frac in fractions.items():
                color, color2, fstyle, alpha = rt.kBlack, rt.kBlack, 1001, 0.3
                if name=='all':
                    fstyle = 0
                if name=='hot':
                    color, color2 = rt.kRed+1, rt.kRed-9
                if name=='cold':
                    color, color2 = rt.kAzure+2, rt.kAzure-8
                if name=='else':
                    color, color2 = rt.kOrange+1, rt.kOrange-1
                frac.SetLineWidth(2)
                tdrDraw(frac, 'hist', lcolor=color, fcolor =color2, fstyle=fstyle, alpha=0.90)
            fixOverlay()
        canv.SaveAs(os.path.join(self.outputPath,canvName+'.png'))
        canv.Close()

    def Plot(self):
        self.VerifyContent()
        #self.PlotAsymmetry(mode='asymmetry')
        #self.PlotAsymmetry(mode='pull')
        self.PlotJetVetoMap(mode="")
        #self.PlotJetVetoMap(mode="ratio")

def main():
    file_versions =[
        #{'year': 'Winter22Run3', 'file_name': 'Winter22Run3_RunCD', 'file_version': 'v1', 'lumi_info': '2022 RunCD, 7.6 fb^{-1}'},
        #{'year': 'Summer22Run3', 'file_name': 'Summer22_23Sep2023_RunCD',  'file_version': 'v1', 'lumi_info': '2022, 5.7 fb^{-1}'},
        #{'year': 'Summer22EERun3', 'file_name': 'Summer22EE_23Sep2023_RunEFG','file_version': 'v1', 'lumi_info': '2022, 27 fb^{-1}'},
        #{'year': 'Summer23Run3', 'file_name': 'Summer23Prompt23_RunC','file_version': 'v1', 'lumi_info': '2023, 18 fb^{-1}'},
        #{'year': 'Summer23BPixRun3', 'file_name': 'Summer23BPixPrompt23_RunD','file_version': 'v1', 'lumi_info': '2023, 9 fb^{-1}'},
        {'year': 'Winter24Prompt24', 'file_name': 'Winter24Prompt24_2024BCDEFGHI', 'file_version': 'v1', 'lumi_info': '2024 RunBtoI, 109 fb^{-1}'},
       #  {'year': 'Summer20UL18', 'file_name': 'hotjets-UL18',       'file_version': 'v1', 'lumi_info': '2018, 59.8 fb^{-1}'},
       #  {'year': 'Summer20UL17', 'file_name': 'hotjets-UL17',       'file_version': 'v1', 'lumi_info': '2017, 41.5 fb^{-1}'},
       #  {'year': 'Summer20UL16APV', 'file_name': 'hotjets-UL16',       'file_version': 'v1', 'lumi_info': '2016, 36.3 fb^{-1}'},
       #  {'year': 'Summer20Run2', 'file_name': 'hotjets-Run2',       'file_version': 'v1', 'lumi_info': 'Run2, 138 fb^{-1}'},
        ]
    for info in file_versions:
        PVM = PlotVetoMaps(**info)
        PVM.Plot()

if __name__ == '__main__':
    main()

