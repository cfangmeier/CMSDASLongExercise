# Code written by:  zaixing.mao@cern.ch && edward.laird@cern.ch from Brown U.
#!/usr/bin/env python
import ROOT as r
import math
import numpy
from sys import argv, exit, stdout, stderr

if len(argv) < 2:
   print 'Usage:python xs_calculator_prefit.py DYCrossSection[optional]'

if len(argv)>1:
   FoundXS= numpy.array([argv[1]],dtype=float)
else:
   FoundXS=1.00

f = r.TFile("prefit.root","recreate")
################################################
# Sevreal Histograms are initiated/produced here
defaultOrder = [('WJets',  r.TColor.GetColor(100,182,232)),
                ('TTJets', r.TColor.GetColor(155,152,204)),
                ('QCD', r.TColor.GetColor(250,202,255)),
                ('DY', r.TColor.GetColor(248,206,104))]


def buildHistDict(nbins):
    histDict = {}
    for iSample, iColor in defaultOrder:
        histDict[iSample+'_OST'] = r.TH1F(iSample+'_OST', '', nbins, 0, 200)
        histDict[iSample+'_OST'].SetFillColor(iColor)
        histDict[iSample+'_OST'].SetMarkerColor(iColor)
        histDict[iSample+'_OST'].SetMarkerStyle(21)
        histDict[iSample+'_OST'].SetLineColor(r.kBlack)

    histDict['data_OST'] = r.TH1F('data_OST', '', nbins, 0, 200)
    histDict['data_OST'].SetMarkerStyle(8)
    histDict['data_OST'].SetMarkerSize(0.9)
    histDict['data_OST'].SetMarkerColor(r.kBlack)


    histDict['DY_SST'] = r.TH1F('DY_SST', '', nbins, 0, 200)
    return histDict
################################################

def setMyLegend(lPosition, lHistList):
    l = r.TLegend(lPosition[0], lPosition[1], lPosition[2], lPosition[3])
    l.SetFillStyle(0)
    l.SetBorderSize(0)
    for i in range(len(lHistList)):
        l.AddEntry(lHistList[i][0], lHistList[i][1], lHistList[i][2])
    return l

def getBins(hist, mass_low, mass_high):
    bin_low = -1
    bin_high = -1
    for i in range(hist.GetNbinsX()):
        if hist.GetBinCenter(i+1) >= mass_low and bin_low == -1:
            bin_low = i+1
        if hist.GetBinCenter(i+1) >= mass_high and bin_high == -1:
            bin_high = i
        if bin_low != -1 and bin_high != -1:
            return bin_low, bin_high
    return bin_low, bin_high

def buildStackDict(histDict, xs_T):
    stackDict = {}
    stackDict['OST'] = r.THStack()

    for iSample, iColor in defaultOrder:
        scale = 1.0
        if iSample != 'DY':
            stackDict['OST'].Add(histDict[iSample+'_OST'])
        else:
            tmpOST = histDict['DY_OST'].Clone()
            tmpOST.Scale(xs_T/6025.2)
            stackDict['OST'].Add(tmpOST)

    return stackDict

def FillHisto(input, output, weight = 1.0):
    for i in range(input.GetNbinsX()):
        output.Fill(input.GetBinCenter(i+1), input.GetBinContent(i+1)*weight)

def buildLegendDict(histDict, position, XS_OST):
    legendDict = {}
    histList = {'T': []}
    histList['T'].append((histDict['data_OST'], 'Observed', 'lep'))
    for iSample, iColor in reversed(defaultOrder):
        if iSample == 'DY':        
            histList['T'].append((histDict[iSample+'_OST'], "%s (xs = %.1f pb)" %(iSample, 6025.5), 'f'))
        else:
            histList['T'].append((histDict[iSample+'_OST'], iSample, 'f'))

    legendDict['T'] = setMyLegend(position, histList['T'])
    return legendDict


def xs_calculator(fileList = [], mass_low = 25, mass_high = 125, nbins = 15):

    #print 'Estimating Z->ll xs in visible mass region (%.1f, %.1f)' %(mass_low, mass_high)

    ZTT_OST = 0.0 #data - all other bkg in opposite sign tight tau isolation region
    QCD_SST = 0.0 #data - all other bkg in same sign tight tau isolation region
    DY_OST = 0.0
    DY_SST = 0.0


    QCD_SS_to_OS_SF = 0.84

    histDict = buildHistDict(nbins)
    #loop over all the samples
    for iFileName, iFileLocation in fileList:
        isData = False
        if iFileName == 'data':
            isData = True
        isDY = False
        if iFileName == 'DY':
            isDY = True

        ifile = r.TFile(iFileLocation)
        weight = -1.0
        if isData:
            weight = 1.0

        lowBin, highBin = getBins(ifile.Get('Mt_h'), mass_low, mass_high)
        FillHisto(ifile.Get('Mt_h'), histDict[iFileName+'_OST'])

        if not isDY:
            ZTT_OST += weight*ifile.Get('Mt_h').Integral(lowBin, highBin) 
            QCD_SST += weight*ifile.Get('Mt_hSS').Integral(lowBin, highBin)
            FillHisto(ifile.Get('Mt_hSS'), histDict['QCD_OST'], weight)

        else:
            FillHisto(ifile.Get('Mt_hSS'), histDict['DY_SST'])
            DY_OST += ifile.Get('Mt_h').Integral(lowBin, highBin)


    lowBin, highBin = getBins(histDict['DY_SST'], mass_low, mass_high)
    XS_OST = FoundXS*6025.2
    histDict['QCD_OST'].Add(histDict['DY_SST'], -1.0)
    #histDict['QCD_OST'].Add(histDict['DY_SST'], -1.0*XS_OST/6025.2)
    histDict['QCD_OST'].Scale(QCD_SS_to_OS_SF)

    stackDict = buildStackDict(histDict, XS_OST)
    legendDict = buildLegendDict(histDict, (0.6, 0.8 - 0.06*4, 0.85, 0.8), XS_OST)

    for i in range(histDict['data_OST'].GetNbinsX()):
        histDict['data_OST'].SetBinError(i+1, math.sqrt(abs(histDict['data_OST'].GetBinContent(i+1))))

    #plot
    pdf = 'stack_mt.pdf'
    c = r.TCanvas("c","Test", 800, 600)
    max_t = 1.2*max(stackDict['OST'].GetMaximum(), histDict['data_OST'].GetMaximum())
    stackDict['OST'].Draw('hist H')
    stackDict['OST'].SetTitle(' ; M_{T}(e #slash{p}_{T}) [GeV]; Events / 20 GeV')
    stackDict['OST'].SetMaximum(max_t)
    stackDict['OST'].GetYaxis().SetTitleOffset(1.3)
    histDict['data_OST'].Draw('same PE')
    print 'Observation: %0.2f' %(histDict['data_OST'].Integral(lowBin,highBin))
    print 'ZTT (unscaled) Expected: %0.2f' %(histDict['DY_OST'].Integral(lowBin,highBin))
    print 'TT Expected: %0.2f' %(histDict['TTJets_OST'].Integral(lowBin,highBin))
    print 'W Expected: %0.2f' %(histDict['WJets_OST'].Integral(lowBin,highBin))
    print 'QCD Expected: %0.2f' %(histDict['QCD_OST'].Integral(lowBin,highBin))
    legendDict['T'].Draw('same')
    c.SaveAs('%s' %pdf)

    opticut_h = r.TH1F('opticut_h', 'opticut_h', nbins, 0, 200)
    BgMC_h = histDict['TTJets_OST']
    BgMC_h.Add(histDict['WJets_OST'])
    BgMC_h.Add(histDict['QCD_OST'])
    DY_h = histDict['DY_OST']
    BgMC_h.Draw()
    c.SaveAs('BgMC_h.pdf')
    DY_h.Draw()
    c.SaveAs('DY_h.pdf')
    max_r = 0.0
    max_i = -1
    for i in range(DY_h.GetNbinsX()):
        DY_I = DY_h.Integral(0,i+1)
        BgMC_I = BgMC_h.Integral(0,i+1)
        print DY_I, BgMC_I
        opticut_h.SetBinContent(i+1,DY_I/math.sqrt(DY_I+BgMC_I))
        if max_r < DY_I/math.sqrt(DY_I+BgMC_I):
            max_r = DY_I/math.sqrt(DY_I+BgMC_I)
            max_i = i+1
    print 'Mt Cut: %f' % (opticut_h.GetBinCenter(max_i)+10.0)
    opticut_h.Draw()
    c.SaveAs('opticut.pdf')
    
    f.Write()
    f.Close()


    print 'DY->ll xs used: %.1f pb' %XS_OST

dirName = '.'

fileList = [('DY', '%s/DYJetsToLL.root' %dirName),
            ('TTJets', '%s/TTJets.root' %dirName),
            ('WJets', '%s/WJetsToLNu.root' %dirName),
            ('data', '%s/SingleEle.root' %dirName)
            ]

xs_calculator(fileList = fileList, mass_low = 25, mass_high = 125, nbins = 10)
