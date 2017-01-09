#!/usr/bin/env python
'''
Diffraction functions require for fitting and analyzing data.

mkak 2016.10.04 (originally written spring 2016)
'''

## TO DO:
##  - remove global variables
##  - provide better commenting
##  - work into gui
## mkak 2016.10.26

##########################################################################
# IMPORT PYTHON PACKAGES

import math
import operator
import re
import os
# import argparse
import textwrap
import time

import wx

import numpy as np
from scipy import optimize
from scipy import signal
from scipy import constants

import matplotlib.pyplot as plt
import pylab as plb

from lmfit import minimize, Parameters, Parameter, report_fit

HAS_XRAYUTIL = False
try:
    import xrayutilities as xu
    HAS_XRAYUTIL = True
except ImportError:
    pass

HAS_pyFAI = False
try:
    import pyFAI
    import pyFAI.calibrant
    # from pyFAI.calibration import Calibration
    HAS_pyFAI = True
except ImportError:
    pass

##########################################################################
# GLOBAL CONSTANTS

hc = constants.value(u'Planck constant in eV s')*constants.c*1e7 ## units: keV-A



##########################################################################
##########################################################################
#####               X-RAY/DIFFRACTION CALCULATIONS                  ######
##########################################################################
##########################################################################
def d_from_q(q):
    return (2.*math.pi)/q
##########################################################################
def d_from_twth(twth,wavelength,ang_units='degrees'):
    if not ang_units.startswith('rad'):
        twth = np.radians(twth)
    return wavelength/(2*np.sin(twth/2.))
##########################################################################
def twth_from_d(d,wavelength,ang_units='degrees'):
    twth = 2.*np.arcsin(wavelength/(2.*d))
    if ang_units.startswith('rad'):
        return twth
    else:
        return np.degrees(twth)
##########################################################################
def twth_from_q(q,wavelength,ang_units='degrees'):
    twth = 2.*np.arcsin((q*wavelength)/(4.*math.pi))
    if ang_units.startswith('rad'):
        return twth
    else:
        return np.degrees(twth)
##########################################################################
def q_from_d(d):
    return (2.*math.pi)/d
##########################################################################
def q_from_twth(twth,wavelength,ang_units='degrees'):
    if not ang_units.startswith('rad'):
        twth = np.radians(twth)
    return ((4.*math.pi)/wavelength)*np.sin(twth/2.)
##########################################################################
def E_from_lambda(wavelength,E_units='keV',lambda_units='A'):
    '''
    E = hf ; E = hc/lambda
    '''
    if lambda_units == 'm':
        wavelength = wavelength*1e10
    elif lambda_units == 'nm':
        wavelength = wavelength*1e1
    if E_units == 'keV':
        return hc/wavelength
    else:
        return (hc/wavelength)*1e3 # eV
##########################################################################
def lambda_from_E(E,E_units='keV',lambda_units='A'):
    '''
    E = hf ; E = hc/lambda
    '''
    if E_units != 'keV':
        E = E*1e-3 # keV
    if lambda_units == 'm':
        return (hc/E)*1e-10
    elif lambda_units == 'nm':
        return (hc/E)*1e-1
    else:
        return hc/E # A
##########################################################################




##########################################################################
##########################################################################
#####                 pyFAI RELATED FUNCTIONS                       ######
##########################################################################
##########################################################################
def integrate_xrd(xrd_map, ai=None,AI=None, calfile=None, unit='q', steps=10000, 
                  save=False, file='~/test.xy', mask=None, dark=None):
    '''
    Uses pyFAI (poni) calibration file and 2D XRD image to produce 1D XRD data

    Must provide one of following: ai, AI, or calfile!
    options :
    ai -
    AI - 
    calfile - 
    unit - 
    steps - 
    save -
    file - 
    mask - 
    dark - 
    '''

    if HAS_pyFAI:
        if ai is None:
            if AI is None:
                try:
                    ai = pyFAI.load(calfile)
                except IOError:
                    print('No calibration parameters specified.')
                    return
            else:
                ai = calculate_ai(AI)
        
        attrs = {}
        if unit == '2th':
            attrs.update({'unit':'2th_deg'})
        else:
            attrs.update({'unit':'q_A^-1'})
        if mask:
            attrs.update({'mask':mask})
        if dark:
            attrs.update({'dark':dark})        
        if save:
            print('Saving %s data to file: %s\n' % (unit,file))
            attrs.update({'filename':file})

        qI = ai.integrate1d(xrd_map,steps,**attrs)

    else:
        print('pyFAI not imported. Cannot calculate 1D integration.')
        return

    return qI
##########################################################################
def calculate_ai(AI):
    '''
    Builds ai structure using AzimuthalIntegrator from hdf5 parameters
    mkak 2016.08.30
    '''

    if HAS_pyFAI:
        try:
            distance = float(AI.attrs['distance'])
        except:
            distance = 1
     
        ## Optional way to shorten this script... will need to change units of pixels
        ## mkak 2016.08.30   
        #floatattr = ['poni1','poni2','rot1','rot2','rot3','pixel1','pixel2']
        #valueattr = np.empty(7)
        #for f,fattr in enumerate(floatattr):
        #     try:
        #         valueattr[f] = float(AI.attr[fattr])
        #     except:
        #         valueattr[f] =  0
    
        try:
            poni_1 = float(AI.attrs['poni1'])
        except:
            poni_1 = 0
        try:
            poni_2 = float(AI.attrs['poni2'])
        except:
            poni_2 = 0
        
        try:
            rot_1 = float(AI.attrs['rot1'])
        except:
            rot_1 = 0
        try:
            rot_2 = float(AI.attrs['rot2'])
        except:
            rot_2 = 0
        try:
            rot_3 = float(AI.attrs['rot3'])
        except:
            rot_3 = 0

        try:
            pixel_1 = float(AI.attrs['ps1'])
        except:
            pixel_1 = 0
        try:
            pixel_2 = float(AI.attrs['ps2'])
        except:
            pixel_2 = 0

        try:
            spline = AI.attrs['spline']
            if spline == '':
                spline = None
        except:
            spline = None
        
        try:
            detname = AI.attrs['detector']
            if detname == '':
                detname = None
        except:
            detname = None
    
        try:
            xraylambda =float(AI.attrs['wavelength'])
        except:
            xraylambda = None
    else:
        print('pyFAI not imported. Cannot calculate ai for calibration.')
        return

        
    return pyFAI.AzimuthalIntegrator(dist = distance, poni1 = poni_1, poni2 = poni_2,
                                    rot1 = rot_1, rot2 = rot_2, rot3 = rot_3,
                                    pixel1 = pixel_1, pixel2 = pixel_2,
                                    splineFile = spline, detector = detname,
                                    wavelength = xraylambda)
#########################################################################



##########################################################################
##########################################################################
#####          XRAYUTILITIES-DEPENDENT RELATED FUNCTIONS            ######
##########################################################################
##########################################################################

def structurefactor_from_cif(ciffile,wavelength,qmax=10):
    '''
    Calculate structure factor, F from cif
    mkak 2016.09.22
    '''

    ## Calculate the wavelength/energy
    energy = E_from_lambda(wavelength,E_units='eV') ## check to make sure these are the proper units
    
    ## Generate hkl list
    hkllist = generate_hkl()

    try:
        ## Open CIF using xu functions
        cif_strc = xu.materials.Crystal.fromCIF(ciffile)
    except:
        print('xrayutilities failed to read %s' % os.path.split(ciffile)[-1])
        return
        
    ## For each hkl, calculate q and F
    q_cif, F_cif = [],[]
    qlist, Flist = [],[]
    for hkl in hkllist:
        qvec = cif_strc.Q(hkl) ## 
        q = np.linalg.norm(qvec)
        if q < qmax:
            F = cif_strc.StructureFactor(qvec,energy)
            if np.abs(F) > 0.01 and np.linalg.norm(qvec) > 0:
                q_cif += [q,q,q]
                F_cif += [0,np.abs(F),0]
                qlist += [q]
                Flist += [np.abs(F)]

    if F_cif and max(F_cif) > 0:
        q_cif = np.array(q_cif)
    else:
        print('Could not calculate any structure factors.')
        return
    
    return np.array([qlist,Flist]),np.array(q_cif),np.array(F_cif)

#########################################################################
def show_F_depend_on_E(cry_strc,hkl,emin=500,emax=20000,esteps=5000):
    '''
    Dependence of F on E for single hkl for one cif
    mkak 2016.09.22
    '''
    E = np.linspace(emin,emax,esteps)
    F = cry_strc.StructureFactorForEnergy(cry_strc.Q(hkl), E)

    return E,F
#########################################################################


##########################################################################
##########################################################################
#####        DIFFRACTION PEAK FITTING RELATED FUNCTIONS             ######
##########################################################################
##########################################################################
def peaklocater(ipeaks,x,y):
    '''
    Returns x and y for data set corresponding to peak indices solution
    from peakfinder()
    '''
#     xypeaks = []
#     xypeaks += [[x[i],y[i]] for i in ipeaks]
#     xypeaks = zip(*xypeaks)
    xypeaks = np.zeros((2,len(ipeaks)))
    xypeaks[0,:] = [x[i] for i in ipeaks]
    xypeaks[1,:] = [y[i] for i in ipeaks]

    return xypeaks

##########################################################################
def peakfinder(x, y, regions=50, gapthrsh=5):
    '''
    Returns indices for peaks in y from dataset (x,y)
    '''
    ttlpnts = len(x)
    widths = np.arange(1,int(ttlpnts/regions))

    peak_indices = signal.find_peaks_cwt(y, widths, gap_thresh=gapthrsh)
# # scipy.signal.find_peaks_cwt(vector, widths, wavelet=None, max_distances=None, 
# #                   gap_thresh=None, min_length=None, min_snr=1, noise_perc=10)

    return peak_indices
##########################################################################
def data_gaussian_fit(x,y,pknum=0,fittype='single',plot=False):
    '''
    Fits a single or double Gaussian functions.
    '''
    meanx = sum(x)/float(len(x))
    meany = sum(y)/float(len(y))
    sigma = np.sqrt(sum(y*(x-meanx)**2)/float(len(x)))

    try:
        popt,pcov = optimize.curve_fit(gaussian,x,y,p0=[np.max(y),meanx,sigma])
    except:
        popt = [1,1,1]

    if fittype == 'double':
        a,b,c = popt
        popt2,pcov2 = optimize.curve_fit(doublegaussian,x,y,p0=[a,b,c,np.min(y),meanx,sigma])

    rsqu_n1 = 0
    rsqu_n2 = 0
    rsqu_d = 0
    for i in range(x.shape[0]):
        rsqu_n1 = (y[i] - gaussian(x[i],*popt))**2 + rsqu_n1
        if fittype == 'double':
            rsqu_n2 = (y[i] - doublegaussian(x[i],*popt2))**2 + rsqu_n2
        rsqu_d = (y[i] - meany)**2 + rsqu_d

    if plot:
        print('---Single Gaussian')
        print('---Peak @  %0.2f' % (popt[1]))
        print('---FWHM %0.2f' % (abs(2*np.sqrt(2*math.log1p(2))*popt[2])))
        print('Goodness of fit, R^2: %0.4f' % (1-rsqu_n1/rsqu_d))
        if fittype == 'double':
            print('---Double Gaussian')
            print('---Peak @  %0.2f' % (popt2[1]))
            print('---FWHM %0.2f' % (abs(2*np.sqrt(2*math.log1p(2))*popt2[2])))
            print('Goodness of fit, R^2: %0.4f' % (1-rsqu_n2/rsqu_d))

    
    if fittype == 'double':
        pkpos = popt2[1]
        pkfwhm = abs(2*np.sqrt(2*math.log1p(2))*popt2[2])
    else:
        pkpos = popt[1]
        pkfwhm = abs(2*np.sqrt(2*math.log1p(2))*popt[2])

    if plot:
        title_str = 'Gaussian fit for Peak %i' % (pknum+1)
        fit_str =  '2th = %0.2f deg.\nFWHM = %0.4f deg.\nR^2=%0.4f' % (pkpos,pkfwhm,1-rsqu_n2/rsqu_d)
        plx =  0.05*(max(x)-min(x)) + min(x)
        ply = -0.2*(max(y)-min(y)) + max(y)
        
        plt.plot(x,y,'r+',label='Data')
        plt.plot(x,gaussian(x,*popt),'b-',label='Fit: 1 Gaussian')
        if fittype == 'double':
            plt.plot(x,doublegaussian(x,*popt2),'g-',label='Fit: 2 Guassians')
        plt.legend()
        plt.xlabel('2th (deg.)')
        plt.ylabel('Intensity')
        plt.text(plx,ply,fit_str)
        plt.title(title_str)
        plt.show()
    
    return pkpos,pkfwhm
    
##########################################################################
def gaussian(x,a,b,c):
    return a*np.exp(-(x-b)**2/(2*c**2))

##########################################################################
def doublegaussian(x,a1,b1,c1,a2,b2,c2):
    return a1*np.exp(-(x-b1)**2/(2*c1**2))+a2*np.exp(-(x-b2)**2/(2*c2**2))
##########################################################################
def peakfitter(ipeaks,q,I,wavelength=0.6525,verbose=True,halfwidth=40,
               fittype='single'):

    peaktwth = []
    peakFWHM = []
    for j in ipeaks:
        if j > halfwidth and (np.shape(q)-j) > halfwidth:
            minval = int(j - halfwidth)
            maxval = int(j + halfwidth)

            if I[j] > I[minval] and I[j] > I[maxval]:
                
                xdata = q[minval:maxval]
                ydata = I[minval:maxval]

                xdata = twth_from_q(xdata,wavelength)
                try:
                    twth,fwhm = data_gaussian_fit(xdata,ydata,fittype=fittype)
                    peaktwth += [twth]
                    peakFWHM += [fwhm]
                except:
                    pass
        
    return np.array(peaktwth),np.array(peakFWHM)
##########################################################################
def instrumental_fit_uvw(ipeaks,q,I,wavelength=0.6525,halfwidth=40,
                         verbose=True):

    twth,FWHM = peakfitter(ipeaks,q,I,wavelength=wavelength,halfwidth=halfwidth,
                           fittype='double',verbose=verbose)

    tanth = np.tan(np.radians(twth/2))
    sqFWHM  = FWHM**2

    (u,v,w) = data_poly_fit(tanth,sqFWHM,verbose=verbose)
    
    if verbose:
        print '\nInstrumental broadening parameters:'
        print '---  U',u
        print '---  V',v
        print '---  W',w
        print

    return(u,v,w)

##########################################################################
##########################################################################
def poly_func(x,a,b,c):
    return a*x**2 + b*x + c
    
##########################################################################
def data_poly_fit(x,y,plot=False,verbose=False):
    '''
    Fits a set of data with to a second order polynomial function.
    '''

    try:
        popt,pcov = optimize.curve_fit(poly_func,x,y,p0=[1,1,1])
    except:
        print 'WARNING: scipy.optimize.curve_fit was unsuccessful.'
        return [1,1,1]
    
    n = len(x)
    meany = sum(y)/n

    rsqu_n = 0
    rsqu_d = 0
    for i in range(x.shape[0]):
        rsqu_n = (y[i] - poly_func(x[i],*popt))**2 + rsqu_n
        rsqu_d = (y[i] - meany)**2 + rsqu_d

    if verbose:
        print '---Polynomial Fit'
        print '---  U',popt[0]
        print '---  V',popt[1]
        print '---  W',popt[2]
        print 'Goodness of fit, R^2:',1-rsqu_n/rsqu_d
        print
    
    if plot:
        plx =  0.05*(max(x)-min(x)) + min(x)
        ply = -0.25*(max(y)-min(y)) + max(y)
        fit_str = 'B^2 = U [tan(TH)]^2 + V tan(TH) + W\n\nU = %f\nV = %f\nW = %f\n\nR^2 = %0.4f'

        plt.plot(x,y,'r+',label='Data')
        plt.plot(x,poly_func(x,*popt),'b-',label='Poly. Fit')
        plt.legend()
        plt.xlabel('tan(TH)')
        plt.ylabel('FWHM^2 (degrees)')
        plt.text(plx,ply,fit_str % (popt[0],popt[1],popt[2],1-rsqu_n/rsqu_d))
        plt.show()
    
    return popt

##########################################################################



##########################################################################
##########################################################################
#####                   FILE READING FUNCTIONS                      ######
##########################################################################
##########################################################################
def xy_file_reader(xyfile,char=None):
    '''
    Parses (x,y) data from xy text file.

    options:
    char - chararacter separating columns in data file (e.g. ',')
    '''
    with open(xyfile) as f:
        lines = f.readlines()

    x, y = [], []
    for i,line in enumerate(lines):
        if '#' not in line:
            if char:
                fields = re.split(' |%s' % char,lines[i])
            else:
                fields = lines[i].split()
            x += [float(fields[0])]
            y += [float(fields[1])]

    return np.array(x),np.array(y)
##########################################################################
def read_peakfile(peakfile):

    (d,I) = xy_file_reader(peakfile,char=',')
    for i,val in enumerate(d):
        if val <= 0:
            d = np.delete(d,i)
            I = np.delete(I,i)
    q = q_from_d(d)

    pkqlist = [q,I]
   
    qmin = np.min([MINq,np.min(q)])
    qmax = np.max([MAXq,np.max(q)])

    q1 = int((qmax-qmin)/STEPq)+1
    q2 = np.shape(q)[0]
    q3 = q1 + q2
   
    newq   = np.zeros(q3)
    newint = np.zeros(q3)
    
    newq[0]   = qmax
    newint[0] = 0

    j = 0
    for k in range(q3-1):
        if j < q2:
            if newq[k] > q[j]:
                newq[k+1]   = newq[k] - STEPq
                newint[k+1] = 0
            else:
                newq[k+1]   = q[j]
                newint[k+1] = I[j]
                j = j + 1
        else:
            newq[k+1]   = newq[k] - STEPq
            newint[k+1] = 0
            
    return np.array(pkqlist),np.array(newq),np.array(newint)


##########################################################################
##########################################################################
#####                   TO BE EDITED AND SORTED                     ######
##########################################################################
##########################################################################

                                                            ## h^2+k^2+l^2 <= 50
allhkl = [[0,0,1],[0,1,0],[1,0,0],                          ##  1
          [0,1,1],[1,0,1],[1,1,0],                          ##  2
          [1,1,1],                                          ##  3
          [0,0,2],[0,2,0],[2,0,0],                          ##  4
          [2,0,1],[2,1,0],[1,2,0],[1,0,2],[0,2,1],[0,1,2],  ##  5
          [2,1,1],[1,2,1],[1,1,2],                          ##  6
          [2,2,0],[2,0,2],[0,2,2],                          ##  8
          [2,2,1],[2,1,2],[1,2,2],[0,0,3],[0,3,0],[3,0,0],  ##  9
          [3,1,0],[3,0,1],[1,0,3],[1,3,0],[0,1,3],[0,3,1],  ## 10
          [3,1,1],[1,3,1],[1,1,3],                          ## 11
          [2,2,2],                                          ## 12
          [3,2,0],[3,0,2],[2,0,3],[2,3,0],[0,3,2],[0,2,3],  ## 13
          [3,2,1],[3,1,2],[2,1,3],[2,3,1],[1,3,2],[1,2,3],  ## 14
          [0,0,4],[0,4,0],[4,0,0],                          ## 16
          [1,0,4],[1,4,0],[4,0,1],[4,1,0],[0,4,1],[0,1,4],  ## 17
          [2,2,3],[2,3,2],[3,2,2],
          [1,1,4],[1,4,1],[4,1,1],[0,3,3],[3,3,0],[3,0,3],  ## 18
          [3,3,1],[3,1,3],[1,3,3],                          ## 19
          [0,2,4],[0,4,2],[4,2,0],[4,0,2],[2,4,0],[2,0,4],  ## 20
          [1,2,4],[1,4,2],[4,2,1],[4,1,2],[2,4,1],[2,1,4],  ## 21
          [3,3,2],[3,2,3],[2,3,3],                          ## 22
          [2,2,4],[2,4,2],[4,2,2],                          ## 24
          [3,0,4],[3,4,0],[4,0,3],[4,3,0],[0,4,3],[0,3,4],  ## 25
          [0,0,5],[0,5,0],[5,0,0],
          [1,0,5],[1,5,0],[5,0,1],[5,1,0],[0,5,1],[0,1,5],  ## 26
          [3,1,4],[3,4,1],[4,1,3],[4,3,1],[1,4,3],[1,3,4],
          [3,3,3],[1,1,5],[1,5,1],[5,1,1],                  ## 27
          [2,0,5],[2,5,0],[5,0,2],[5,2,0],[0,2,5],[0,5,2],  ## 29
          [3,2,4],[3,4,2],[4,2,3],[4,3,2],[2,4,3],[2,3,4],
          [2,1,5],[2,5,1],[5,1,2],[5,2,1],[1,2,5],[1,5,2],  ## 30
          [4,4,0],[4,0,4],[0,4,4],                          ## 32
          [4,4,1],[4,1,4],[1,4,4],[2,2,5],[2,5,2],[5,2,2],  ## 33
          [3,0,5],[3,5,0],[5,0,3],[5,3,0],[0,3,5],[0,5,3],  ## 34
          [3,3,4],[3,4,3],[4,3,3],
          [3,1,5],[3,5,1],[5,1,3],[5,3,1],[1,3,5],[1,5,3],  ## 35
          [4,4,2],[4,2,4],[2,4,4],[0,0,6],[0,6,0],[6,0,0],  ## 36
          [1,0,6],[0,6,1],[6,1,0],[0,1,6],[1,6,0],[6,0,1],  ## 37
          [3,2,5],[3,5,2],[5,2,3],[5,3,2],[2,5,3],[2,3,5],  ## 38
          [1,1,6],[1,6,1],[6,1,1],
          [6,2,0],[6,0,2],[0,2,6],[0,6,2],[2,0,6],[2,6,0],  ## 40
          [6,2,1],[6,1,2],[1,2,6],[1,6,2],[2,1,6],[2,6,1],  ## 41
          [0,4,5],[0,5,4],[5,4,0],[5,0,4],[4,5,0],[4,0,5],
          [4,4,3],[4,3,4],[3,4,4],
          [1,4,5],[1,5,4],[5,4,1],[5,1,4],[4,5,1],[4,1,5],  ## 42
          [3,3,5],[3,5,3],[5,3,3],                          ## 43
          [2,2,6],[2,6,2],[6,2,2],                          ## 44
          [6,3,0],[6,0,3],[0,3,6],[0,6,3],[3,0,6],[3,6,0],  ## 45
          [2,4,5],[2,5,4],[5,4,2],[5,2,4],[4,5,2],[4,2,5],
          [6,3,1],[6,1,3],[1,3,6],[1,6,3],[3,1,6],[3,6,1],  ## 46
          [4,4,4],                                          ## 48
          [6,3,2],[6,2,3],[2,3,6],[2,6,3],[3,2,6],[3,6,2],  ## 49
          [0,0,7],[0,7,0],[7,0,0],
          [3,4,5],[3,5,4],[5,4,3],[5,3,4],[4,5,3],[4,3,5],  ## 50
          [7,0,1],[7,1,0],[1,0,7],[1,7,0],[0,7,1],[0,1,7],
          [5,5,0],[5,0,5],[0,5,5],
          ]

def generate_hkl(maxval=50,symmetry=None):

    hkllist = []
    for hkl in allhkl:
        if maxval >= (hkl[0]**2 + hkl[1]**2 + hkl[2]**2):
            hkllist += [hkl]
    return hkllist


##########################################################################
def write_rawfile(a,b,filename):

    ##########################################################################
    ## Open .raw file for writing
    ##
    open(filename,'w')

    ##########################################################################
    ## Write values to file
    ##
    for i in range(a.shape[0]):
        f.write('%s %s\n' % (a[i],b[i]))

    ##########################################################################
    ## Close file
    ##    
    f.close()
    print('\nCreated file %s.' % filename)

    return()

##########################################################################
def find_y(x,stdx,stdy):

    len_x   = x.shape[0]
    len_std = stdx.shape[0]
    
    y = np.zeros(len_x)
     
    for i in range(1,len_x):
        for j in range(1,len_std):
            if x[i] > stdx[j] and x[i] < stdx[j-1]:
                y[i] = stdy[j] + ((stdy[j-1]-stdy[j])/(stdx[j-1]-stdx[j]))*(x[i]-stdx[j])
                
    return y

##########################################################################
def trim_range(x,y,xmin,xmax):

    maxi = -1
    mini = 0
    for i,val in enumerate(x):
        mini = i if val < xmin else mini
        maxi = i if val < xmax else maxi
   
    return x[mini:maxi],y[mini:maxi]

##########################################################################
def calc_peak(q1,int1): # inputs: q, intensity

    x = np.arange(-2,2,0.001)
   
    ## Lorentzian 
    b = 1/(1+(x**2))
    
    ## Gaussian
    c = np.exp(-math.log1p(2)*(x**2))
    
    ## VOIGT: Convolve, shift, and scale
    d = np.convolve(b,c,'same')
    d = norm_pattern(d,c)
    shiftx = find_max(x,d)
    newx = x-shiftx
    
    ## Diffraction pattern data.
    ## x,b    - 'Lorentzian'
    ## x,c    - 'Gaussian'
    ## newx,d - 'Voigt'

##########################################################################
def instr_broadening(pkqlist,q,intensity,u,v,w): 

    ## Broadening calculation performed in 2theta - not q
    twthlist = twth_from_q(pkqlist[0],LAMBDA)
    twth = twth_from_q(q,LAMBDA)

    ## TERMS FOR INSTRUMENTAL BROADENING
    Bi = np.zeros(np.shape(pkqlist)[1])
    for i in range(np.shape(pkqlist)[1]):
        thrad = math.radians(twthlist[i]/2)
        Bi[i] = np.sqrt(u*(math.tan(thrad))**2+v*math.tan(thrad)+w)
        
    ## Define intensity array for broadened peaks
    intenB = np.zeros(np.shape(q)[0])
    
    ## Loop through all peaks
    for i in range(np.shape(pkqlist)[1]):

        ## Create Gaussian of correct width
        A = pkqlist[1][i]   ## intensity
        B = twthlist[i]     ## position (in 2theta)
        
        ## FWHM = abs(2*np.sqrt(2*math.log1p(2))*c)
        
        ## INSTRUMENT contribution
        c_i = Bi[i]/abs(2*np.sqrt(2*math.log1p(2)))      
        
        width = Bi[i]

        ## Define 2th axis for calculation
        min2th = B-2*width
        max2th = B+2*width        
        twthG = np.arange(max2th,min2th,-width/200)
        qG = q_from_twth(twthG,LAMBDA)

        ## Calculate peak for corresponding width
        intBi = A*np.exp(-(twthG-B)**2/(2*c_i**2))
        ## Normalize to correct intensity
        intBi = norm_pattern(intBi,A)

        ## Interpolate peak onto q scale and add
        nintensity = find_y(q,qG,intBi)        
        for j in range(np.shape(intenB)[0]):
            intenB[j] = nintensity[j] + intenB[j]
            
    intenB = norm_pattern(intenB,intensity)

    return(intenB)

##########################################################################

##########################################################################
def size_broadening(pkqlist,q,wavelength,u,v,w,nsize,pk_shift=1.00307298): 

    #global LAMBDA
    #pk_shift = 1.00307298
    
    ## Broadening calculation performed in 2theta - not q
    twth = twth_from_q(q,LAMBDA)
##    twthlist = twth_from_q(pkqlist[0],0.3917)
    twthlist = twth_from_q(pkqlist[0],LAMBDA*pk_shift)


    ## TERMS FOR INSTRUMENTAL BROADENING
    Bi = np.zeros(np.shape(pkqlist)[1])
    for i in range(np.shape(pkqlist)[1]):
##    len_list = len(pkqlist[0])
##    Bi = pkqlist[0]
##    for i in range(len_list):
        thrad = math.radians(twthlist[i]/2)
        Bi[i] = np.sqrt(u*(math.tan(thrad))**2+v*math.tan(thrad)+w)


    ## TERMS FOR SIZE BROADENING
    ## FWHM(2th) = (C*LAMBDA)/(D*math.cos(math.radians(twth/2)))
    ## FWHM(q)   = (C*LAMBDA)/D*(1/np.sqrt(1-termB))

    D = nsize/10 # convert size from nm to A
    C = 1.1 # shape factor?
    #C = 1.0 # shape factor (1 for sphere)
    termB = ((LAMBDA*pkqlist[0])/(2*math.pi))**2
    Bs = (C*LAMBDA)/D*(1/np.sqrt(1-termB))
    
        
    ## Define intensity array for broadened peaks
    intenB = np.zeros(np.shape(q)[0])
    
    ## Loop through all peaks
    for i in range(np.shape(pkqlist)[1]):
    
        if pkqlist[0][i] > np.min(q) and pkqlist[0][i] < np.max(q):

            ## Create Gaussian of correct width
            ## FWHM = abs(2*np.sqrt(2*math.log1p(2))*c)
            A = pkqlist[1][i]   ## intensity
            B = twthlist[i]     ## position (in 2theta)
        
            ## INSTRUMENT contribution
            c_i = Bi[i]/abs(2*np.sqrt(2*math.log1p(2)))
            ## SIZE contribution
            c_s = Bs[i]/abs(2*np.sqrt(2*math.log1p(2)))
            
            Bm = np.sqrt(Bi[i]**2+Bs[i]**2)
            c_m = Bm/abs(2*np.sqrt(2*math.log1p(2)))
      
            width1 = np.max(Bs[i],Bi[i])
            width2 = np.min(Bs[i],Bi[i])

            ## Define 2th axis for calculation
            min2th = B-2*width1
            max2th = B+2*width1
            twthG = np.arange(max2th,min2th,-width2/400)

            ## Calculate peak for corresponding width
            intBi = A*np.exp(-(twthG-B)**2/(2*c_i**2))
            intBs = A*np.exp(-(twthG-B)**2/(2*c_s**2))
            intBm = A*np.exp(-(twthG-B)**2/(2*c_m**2))
            
            noplot = 1
            if i < 10 and noplot == 0:
                plt_str = 'inst = %0.6f\nsize = %0.6f\n comb = %0.6f'
                print(plt_str % (Bi[i],Bs[i],Bm))
#    #            plot_diff(twthG,intBi,'instrument') 
#    #            plot_diff(twthG,intBs,'size')
#    #            plot_diff(twthG,intBm,'comb.')
                #plt.legend()
                #plt.show()
            
            new_intensity = np.convolve(intBs,intBi,'same')
            ## Normalize to correct intensity
            new_intensity = norm_pattern(new_intensity,A)
        
            shift2th = find_max(twthG,new_intensity)
            twthG = twthG - (B-shift2th)

            qG = q_from_twth(twthG,LAMBDA)
                        
            nintensity = find_y(q,qG,new_intensity)        
        
            ## Interpolate peak onto q scale and add
            for j in range(np.shape(intenB)[0]):
                intenB[j] = nintensity[j] + intenB[j]


            if i < 10 and noplot == 0:
                print('2theda shift is %0.4f' %(B-shift2th))
#    #            plot_diff(twthG,new_intensity,'conv.')
                plt.legend()
                plt.show()
                
    intenB = scale_100(intenB)
            

    return(intenB)

##########################################################################
def norm_pattern(intensity,scale_int):

    max_int = np.max(intensity)
    scale = np.max(scale_int)
    intensity = intensity/max_int*scale
    
    return(intensity)

##########################################################################
def scale_100(intensity):

    intensity = norm_pattern(intensity,100)
    
    return(intensity)

##########################################################################
def calc_fraction(intensity,fraction):

## THIS NEEDS TO BE INCORPORATED.
    
    return intensity*fraction


##########################################################################
def find_max(q,intensity):

    max_int = np.max(intensity)

    if intensity.shape[0] != intensity.shape[0]:
        raise IOError('Array lengths do not match.')
    for i in range(intensity.shape[0]):
        if intensity[i] == max_int:
            max_q = q[i]
 
    return(max_q)
##########################################################################
def calcRsqu(y,ycalc):
    
    ss_res = 0
    ss_tot = 0
    
    ymean = sum(y)/float(len(y))
    
    for i in range(ycalc.shape[0]):
        ss_res = ss_res + (y[i] - ycalc[i])**2
        ss_tot = ss_tot + (y[i] - ymean)**2
       
    Rsqu = 1 - (ss_res/ss_tot)

    return(Rsqu)

#########################################################################
def remove_kapton(data_q,data_int,kaptfile):

    kapton_q,kapton_int = xy_file_reader(kaptfile)

    ##min_index, min_ value = min(enumerate(kapton_int), key=operator.itemgetter(1))
    max_index, max_value = max(enumerate(kapton_int), key=operator.itemgetter(1))
   
    kapt_int = kapton_int*(data_int[max_index]/kapton_int[max_index])
    data_int = data_int - kapt_int
    data_int = scale_100(data_int)
    
    return data_int
    
##########################################################################    
def patternbroadening(data_q,nsize,pk_shift):

    ## Particle size broadening and instrumental broadening
    if NPsize and PEAKfile:
        calc_int = size_broadening(pkQlist,data_q,instrU,instrV,instrW,nsize,pk_shift)

    ## Instrumental broadening
    elif PEAKfile:
        calc_int = instr_broadening(pkQlist,data_q,DATA_INT,instrU,instrV,instrW)

    return calc_int

##########################################################################    
def background(q,a,b,c):

    return a*q**2 + b*q + c

##########################################################################
def fit_background(my_pars, data_q, data_int):

    a = my_pars['a'].value
    b = my_pars['b'].value
    c = my_pars['c'].value
    
    if ERRORcheck == 1:
        print(a,b,c)
    
    calc_int = background(data_q,a,b,c)

    return calc_int - data_int # minimize difference between data and calculated

##########################################################################
def fit_pattern(my_pars, data_q, data_int):

    nsize = my_pars['nsize'].value
    a = my_pars['a'].value
    b = my_pars['b'].value
    c = my_pars['c'].value
    pk_shift = my_pars['pk_shift'].value
    
    if ERRORcheck == 1:
        print(nsize,a,b,c,pk_shift)
    
    calc_int = patternbroadening(data_q,nsize,pk_shift)+background(data_q,a,b,c)

    return calc_int - data_int # minimize difference between data and calculated

#########################################################################
def fit_with_minimization():

    global bkgdA,bkgdB,bkgdC
    global instrU,instrV,instrW
    global NPsize, PKshift
    
    ## Create a set of Parameters
    my_pars = Parameters()

    ##my_pars.add('nsize', value= NPsize, min= 3.0,  max=100.0)
    my_pars.add('nsize', value= NPsize, min= 3.0,  max=100.0,vary=False)
    my_pars.add('pk_shift',  value=PKshift,  min=0.98, max=1.02,vary=False)
    
    if bkgdA == 0:
        minA = -100
        maxA =  100
    else:
        minA = -1.2*abs(bkgdA)
        maxA =  1.2*abs(bkgdA)

    if bkgdB == 0:
        minB = -100
        maxB =  100        
    else:
        minB = -1.2*abs(bkgdB)
        maxB =  1.2*abs(bkgdB)
    if bkgdC == 0:
        minC = 0
        maxC = max(DATA_INT)
    else:
        minC =  0.8*bkgdC
        maxC =  1.2*bkgdC
        
    print(minA,minB,minC,maxA,maxB,maxC)

    my_pars.add('a', value=bkgdA, min=minA, max=maxA)
    my_pars.add('b', value=bkgdB, min=minB, max=maxB)
    my_pars.add('c', value=bkgdC, min=minC, max=maxC)
    
    print
    # Do fit
    
    ## First, fit background alone:
    result = minimize(fit_background, my_pars, args=(DATA_Q,DATA_INT),method=fitMETHOD)
    
    my_pars.add('a',  value=result.params['a'].value)
    my_pars.add('b',  value=result.params['b'].value)
    my_pars.add('c',  value=result.params['c'].value)
    
    ## Now, include more fitting...    
    result = minimize(fit_pattern, my_pars, args=(DATA_Q,DATA_INT),method=fitMETHOD)

    ## Default: method='leastsq'
    ## method='nelder'
    ## didn't quit, more or less landed on parameters:
    ## 6.43477783086 0.609120604191 -9.76760647538 56.4337260003

#    # write error report
#    report_fit(result)
    
    NPsize = result.params['nsize'].value
    bkgdA  = result.params['a'].value
    bkgdB  = result.params['b'].value
    bkgdC  = result.params['c'].value
    PKshift  = result.params['pk_shift'].value
        
    return



def registerLarchPlugin():
    return ('_diFFit', {})
