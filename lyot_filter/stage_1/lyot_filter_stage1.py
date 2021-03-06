from astropy.io import fits
import cv2
from scipy import optimize
import numpy as np
import glob
#import find_ret
#import smooth_numpy
from scipy.signal import argrelextrema
import pickle
import os
from astropy.table import Table
import easygui

def find_tilt(img,angle_range=[1,2]):
    
    angs = np.arange(angle_range[0],angle_range[1],0.001)
    cf = []
    rows,cols = img.shape

    for ang in np.arange(1,2,0.001):
        M = cv2.getRotationMatrix2D((cols/2,rows/2),ang,1)
        dst = cv2.warpAffine(img,M,(cols,rows))
        r1 = np.mean(dst[300:400,:],axis=0)
        r2 = np.mean(dst[900:1000,:],axis=0)
        #cor.append(np.correlate(r1,r2)[0])
        #rm.append(np.var(r1-r2)) 
        cf.append(np.corrcoef(r1,r2)[0,1])
    imax = np.argmax(cf)
    rot_angle = angs[imax]
    return rot_angle


### find tilts

data_folder = easygui.diropenbox(msg="open Directory", title="Open Directory", default="/data/phanindra/Abhilash/Lyott filter tests/first stage of Lyott filter")
if data_folder is None:
    exit(0)

rot_ang_file = glob.glob(data_folder+'/rotation_angles.pkl')
img_files = glob.glob(data_folder + '/*.fits')


if rot_ang_file:
    fid_rot = open(rot_ang_file, 'rb')
    rot_angles = pickle.load(fid_rot)
    vlts = []
    mns = {}
    for img_file in img_files:                                          
        hdus = fits.open(img_file)                      
        print(img_file)                     
        img = hdus[0].data               
        hdus.close()  
        rows,cols = img.shape                      
        vlts.append(float(img_file[-9:-5])/100)
        
        M = cv2.getRotationMatrix2D((cols/2,rows/2),rot_angles[vlts[-1]],1)
        dst = cv2.warpAffine(img,M,(cols,rows))
        #dst = np.fliplr(dst)
        dst = dst[350:1000, :]
        mn = np.mean(dst,axis=0)
        mns[vlts[-1]] = mn

    vlts = np.array(vlts)
    vlts = np.sort(vlts)

else:
    

    vlts=[]
    rot_angles = {}
    mns = {}

    for img_file in img_files:                                          
        hdus = fits.open(img_file)                      
        print(img_file)                     
        img = hdus[0].data               
        hdus.close()  
        rows,cols = img.shape
        vlts.append(float(img_file[-9:-5]) / 100)
        rot_angles[vlts[-1]] = find_tilt(img)
        print(rot_angles[vlts[-1]])
        M = cv2.getRotationMatrix2D((cols/2,rows/2),rot_angles[vlts[-1]],1)
        dst = cv2.warpAffine(img,M,(cols,rows))
        #dst = np.fliplr(dst)
        dst = dst[350:1000,:]
        mn = np.mean(dst,axis=0)
        mns[vlts[-1]] = mn

    vlts = np.array(vlts)
    vlts = np.sort(vlts)

    fid_rot = open(rot_ang_file,'wb')
    pickle.dump(rot_angles,fid_rot)
    fid_rot.close()


### find 45 and 0 degree orientation
# trms = []
# for ds in angles:
#   trms.append(np.sqrt(np.mean(np.square(mns[ds]/max(mns[ds])))))
#
# angle45 = angles[np.argmax(trms)]
# angle0 = angles[np.argmin(trms)]
#
# mn45 = mns[angle45] # flat, no fringes
# mn0 = mns[angle0] # maximum fringes
#
#
# ### find shifts
# shifts = {}
# mns_shifted = {}
#
# for ds in angles:
#   shifts[ds] = int(np.argmax(np.correlate(mn0/np.max(mn0),mns[ds]/np.max(mns[ds]),mode='same'))-cols/2)
#   mns_shifted[ds] = np.roll(mns[ds],shifts[ds])


### filter reading and fit
fl = '/home/abhilash/abhilash/lctf/fixed_ret/codes/datasheets/optifcal_filters/450FS10.csv'


flt_dt = np.loadtxt(fl,skiprows=9,delimiter=',')
wl = flt_dt[:,0]
tx = flt_dt[:,1]


id2wav = lambda a,b,xid: a*xid + b
wav2id = lambda a,b,lam: (lam-b)/a

errfunc = lambda p,i,i_csv,lam: (np.interp(lam,id2wav(p[0],p[1],np.arange(len(i))),i)-p[2])/np.max(np.interp(lam,id2wav(p[0],p[1],np.arange(len(i))),i)-p[2]) - i_csv 


mn = mn45   #/np.max(mn45)
tx = tx/np.max(tx)
p0 = [1/45,520,90] # for 550
#p0 = [0.0129,434.3,90] # for 450
#p0 = [1/58,581,90] # for 600
#p0 = [3/370,690,100] # for 700
p1_wav, success = optimize.leastsq(errfunc, p0[:], args=(mn,tx,wl))


#mn_sm = lowess(mn,xid,frac=0.06)
#mn_sm = mn_sm[:,1]
#p1, success = optimize.leastsq(errfunc, p0[:], args=(mn_sm,tx,wl))

start_id = 1000
end_id = 1500
step_id =1 

ret = {}

for ids in np.arange(start_id,end_id,step_id):
    mn_id = []
    for ds in angles:
        mn_id.append(np.mean(mns_shifted[ds][ids:ids+step_id]))

    mn_id = np.array(mn_id)
    mn_id = (mn_id - p1_wav[2])/np.max(mn_id - p1_wav[2])

    p1_ret = find_ret.find_retardance(mn_id,angles)
    wav_tmp = id2wav(p1_wav[0],p1_wav[1],ids+step_id/2)
    ret[wav_tmp] = p1_ret[0]


rr = []
ww = []

for k in ret.keys():
    ww.append(k)
    rr.append(ret[k]*180/np.pi)

ww = np.array(ww)
rr = np.array(rr)
np.savetxt('retardance_vs_wavelength.dat',np.vstack([ww,rr]).T,fmt='%f')




# mn0_smooth = smooth_numpy.smooth(mn0)
# mn0_smooth = mn0_smooth[5:-5]

# imaxes = argrelextrema(mn0_smooth, np.greater)[0]

# imaxes = imaxes[(imaxes>1000) & (imaxes<1500)]



# ww_max = []
# rr_max = []

# for imax in imaxes:
#    mn_id = []
#    for ds in angles:
#        mn_id.append(mns_shifted[ds][imax])#(np.mean(mns_shifted[ds][int(imax-step_id/2):int(imax+step_id/2)]))

#    mn_id = np.array(mn_id)
#    mn_id = (mn_id - p1_wav[2])/np.max(mn_id - p1_wav[2])

#    p1_ret = find_ret.find_retardance(mn_id,angles)
#    wav_tmp = id2wav(p1_wav[0],p1_wav[1],imax)
#    ww_max.append(wav_tmp)
#    rr_max.append(p1_ret[0]*180/np.pi)

   
# ww_max = np.array(ww_max)
# rr_max = np.array(rr_max)

# # find the thickness


# def n_c(lam,A,B,C,D,F):
#    n = A + B*lam**2/(lam**2 - C) + D*lam**2/(lam**2 -F)
#    n = np.sqrt(n)
#    return n


# def no_c(lam):
#    Ao = 1.73358749
#    Bo = 0.96464345
#    Co = 1.94325203 * 10**(-2)
#    Do = 1.82831454
#    Fo = 120
#    no = n_c(lam,Ao,Bo,Co,Do,Fo)
#    return no

# def ne_c(lam):
#    Ae = 1.35859695
#    Be = 0.82427830
#    Ce = 1.06689543*10**(-2)
#    De = 0.14429128
#    Fe = 120
#    ne = n_c(lam,Ae,Be,Ce,De,Fe)
#    return ne



# #ne = n_c(ww/1000,Ae,Be,Ce,De,Fe)
# #no = n_c(ww/1000,Ao,Bo,Co,Do,Fo)


# retardance = lambda t,lam: (2*np.pi * t*10**6 * (no_c(lam/1000) - ne_c(lam/1000))/lam) % (2*np.pi)  # t in mm, lam in nm

# errfunc_thick = lambda p,ret_obs,lam: ret_obs - retardance(p[0],lam) # lam in nm

# p0_thick = [2.5]

# p1_thick,success = optimize.leastsq(errfunc_thick, p0_thick[:], args=(rr*np.pi/180,ww))


###### copied from simulation_multi_reflaction ########

def output_its(theta,ret):
    """
    Given theta and retartdance value, gives intensity. theta and ret in radians
    """
    its = (1 + (np.cos(2*theta))**2 + ((np.sin(2*theta))**2)*np.cos(ret))/2
    return its

def n_c(lam,A,B,C,D,F):
    lam = lam/1000
    n = A + B*lam**2/(lam**2 - C) + D*lam**2/(lam**2 -F)
    n = np.sqrt(n)
    return n


def no_c(lam):
    Ao = 1.73358749
    Bo = 0.96464345
    Co = 1.94325203 * 10**(-2)
    Do = 1.82831454
    Fo = 120
    no = n_c(lam,Ao,Bo,Co,Do,Fo)
    return no

def ne_c(lam):
    Ae = 1.35859695
    Be = 0.82427830
    Ce = 1.06689543*10**(-2)
    De = 0.14429128
    Fe = 120
    ne = n_c(lam,Ae,Be,Ce,De,Fe)
    return ne

retardance = lambda thick,lam: (2*np.pi * thick*10**6 * (no_c(lam/1000) - ne_c(lam/1000))/lam) % (np.pi)  # t in mm, lam in nm

def transmittance(n,thick,lam): #n - ri,thick in mm, lam in nm
    delta = 2*np.pi * thick * 10**6 * n/lam
    t = 8*n**2/(1 + n**4 + 6*n**2 - (n**2 -1)**2*np.cos(2*delta))
    return t

def modified_retardance(n,thick,lam): #n - ri,thick in mm, lam in nm
    delta = 2*np.pi * thick * 10**6 * n/lam
    tan_phi = (n**2 + 1)/(2*n) * np.tan(delta)
    phi = np.arctan(tan_phi)
    return phi


start_id = 1000
end_id = 1500
step_id =1 

ret = {}

obs_its_wrt_angles = []
lams = []
modified_angles = []


for ids in np.arange(start_id,end_id,step_id):
    mn_id = []
    for ds in angles:
        mn_id.append(np.mean(mns_shifted[ds][ids:ids+step_id]))

    mn_id = np.array(mn_id)
    mn_id = (mn_id - p1_wav[2])/np.max(mn_id - p1_wav[2])
    obs_its_wrt_angles.append(mn_id)    

    p1_ret = find_ret.find_retardance(mn_id,angles,p0=[np.pi/2,0,1.05])
    wav_tmp = id2wav(p1_wav[0],p1_wav[1],ids+step_id/2)
    lams.append(wav_tmp)
    modified_angles.append(angles*p1_ret[2] + p1_ret[1]*180/np.pi)
    ret[wav_tmp] = p1_ret[0]

lams = np.array(lams)

mesh_lams,mesh_angles = np.meshgrid(lams,angles)
img_obs_its = np.zeros([len(angles),len(lams)])


for i in range(len(lams)):
    for j in range(len(modified_angles[i])):
        mesh_angles[j,i] = modified_angles[i][j]
        img_obs_its[j,i] = obs_its_wrt_angles[i][j]

A = np.zeros([len(angles),len(lams),3])
A[:,:,0] = mesh_lams
A[:,:,1] = mesh_angles/180*np.pi
A[:,:,2] = img_obs_its

A = A.reshape(len(lams)*len(angles),3)

if not os.path.isfile('image.fits'):
    hdu_img = fits.PrimaryHDU(img_obs_its) 
    t = Table(A[:,:2],names=('Wavelength','Angles'))
    hdu_table = fits.BinTableHDU(t) 

    hdul = fits.HDUList([hdu_img,hdu_table])
    hdul.writeto('image.fits')


def modified_output_its(xdata,thick): #thick in mm, lam in nm
    lam = xdata[:,0]
    theta = xdata[:,1]
    ne = ne_c(lam)
    no = no_c(lam)
    phi_e = modified_retardance(ne,thick,lam)
    phi_o = modified_retardance(no,thick,lam)
    phi = phi_e - phi_o

    te = transmittance(ne,thick,lam)
    to = transmittance(no,thick,lam)
    its_tmp = te*np.cos(theta)**4 + to*np.sin(theta)**4 + 2*(te*to)**(1/2)*np.sin(theta)**2*np.cos(theta)**2*np.cos(phi)
    its =  its_tmp/np.max(its_tmp)
    return its

#optimize.curve_fit(modified_output_its, A[:,:2], A[:,2], [1.1])

# wavelength resolution

def gauss_kern(sigma,size=None):
    if size == None:
        size = int(sigma)
    #size = int(size)
    x = np.arange(-size,size+1)
    g = np.exp(-(x**2/sigma))
    g = g/np.sum(g)
    return g

guess_thickness = 4 #mm

sim_img = modified_output_its(A[:,:2],guess_thickness).reshape(len(angles),len(lams))
gs = gauss_kern(5,100)

sim_img_smooth = np.zeros([len(angles),len(lams)])

for i in range(len(angles)):
    sim_img_smooth[i,:] = np.convolve(sim_img[i,:],gs)[100:-100]


