#!/usr/bin/env python

#LSF -q suncat
#LSF -W 50:00
#LSF -n 40
#LSF -e err.log
#LSF -N

from ase import io
import os
import numpy as np
import glob
from ase.optimize import FIRE
from ase.neb import NEB
from espresso.multiespresso import multiespresso

# neb options
climb=False
k=[0.3, 0.3, 0.3, 0.3, 0.3, 0.3] #remember to tighten spring constants as you go

# convergence options
smearing='mv'

#these trajectories have to contain total energies and forces besides the coordinates
initial = io.read('neb0.traj')
final = io.read('neb6.traj')

# if this is the first neb, and the neb traj's are not available, the default images are created; otherwise counts the images available:
if os.path.exists('neb1.traj') and os.path.getsize('neb1.traj')!=0:
	nebfiles = glob.glob('neb*.traj')
	intermediate_images = len(nebfiles)-2
	print 'number of images read'
	print str(intermediate_images)
else: 
#	print 'number of images interpolated'
#	print str(intermediate_images)
	intermediate_images = 5
	
# check for restart
for j in range(1,intermediate_images+1):
   if os.path.exists('neb%d.traj' % j) and os.path.getsize('neb%d.traj' % j)!=0:
     restart=True
     print '  neb%d.traj not empty' %j
   else:
     restart=False
     print '  neb%d.traj empty' %j
if restart==True:
   print 'restarting:'
else:
   print 'initial run:'

if climb==True:
   print '  climb mode on'
else:
   print '  no climbing'

#set up multiple espresso calculators
#example shown here: slabs: dipole correction is turned on
m = multiespresso(ncalc=intermediate_images,outdirprefix='ekspressen',
		pw=500.,
		dw=5000.,
		xc='BEEF',
		kpts=[4,4,1],
		spinpol=False,
		smearing=smearing,
		nbands=-10,
		dipole={'status':True}, 
		output = {'avoidio':True,'removewf':True,'wf_collect':False},
		convergence={'energy':1e-4,'mixing':0.1,'nmix':10,'mixing_mode':'local-TF','maxsteps':300, 'diag':'david'}
)

#mag = [0]*len(initial.get_positions())
#initial.set_initial_magnetic_moments(mag)
#final.set_initial_magnetic_moments(mag)

images = [initial]
if not restart:
  for i in range(intermediate_images):
     images.append(initial.copy())

if restart:
   for j in range(1,intermediate_images+1):
     nebimage=io.read('neb%d.traj' % j)	
#     nebimage.set_initial_magnetic_moments(mag)
     images.append(nebimage)
     
images.append(final)

if not climb:
  neb = NEB(images,k=k)
if climb:
  neb = NEB(images,climb=True,k=k)

m.set_neb(neb)

#only for first step, linear interpolation here.
if not restart:
  neb.interpolate()

if not climb:
   qn = FIRE(neb, logfile='qn.log')
if climb:
   qn = FIRE(neb, logfile='qn.log')

for j in range(1,intermediate_images+1):
    traj = io.PickleTrajectory('neb%d.traj' % j, 'a', images[j])
    print 'I am here! neb%d.traj'
    qn.attach(traj)

qn.run(fmax=0.05)
