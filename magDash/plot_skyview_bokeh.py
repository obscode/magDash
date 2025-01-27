#!/usr/bin/env python

'''Plot a skymap using the Bokeh plotting package. Bokeh has the big 
advantage of embedding directly into the HTML canvas with a given size,
making it easier to place than a matplotlib-generated image. Intractions
are also much much better.'''

import os
from . import polar
from bokeh.plotting import ColumnDataSource
from bokeh.models import HoverTool, CustomJS, CDSView
from bokeh.models.filters import BooleanFilter,AllIndices
import numpy as np
import pickle

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.units import degree
from astropy.time import Time
import time
from astroplan import Observer,FixedTarget



# The constellation data.
conlines = os.path.join(os.path.dirname(__file__), 'Conlines3.pkl')
with open(conlines, 'rb') as f:
   ra1s,ra2s,dec1s,dec2s = pickle.load(f)
conCDS = ColumnDataSource(dict(
   RA1=ra1s,
   RA2=ra2s,
   DEC1=dec1s,
   DEC2=dec2s
))


class SkyMap:

   def __init__(self, location='LCO', date=None, imsize=400):

      self.obs = Observer.at_site(location)
      if date is None:
         self.date = Time.now()
      else:
         self.date = Time(date)
      self.imsize = imsize
      self._setup()

      self.conCDS = ColumnDataSource(dict(
         RA1=ra1s,
         RA2=ra2s,
         DEC1=dec1s,
         DEC2=dec2s
      ))
      # Initial filtered view
      self.conView = CDSView(filter=AllIndices())
                
   def _setup(self):
      # Setup the graph
      self.hover = HoverTool()
      self.hover.tooltips = [("Name", "@label"),
                        ("Type","@type"),("Alt","@alt")]
      self.hover.renderers = []
      #tap = TapTool(callback=OpenURL(url="/navigator/@pk/"), names=['obj'])
     
      self.rmax = 90
      self.fig = polar.PolarPlot(height=self.imsize, width=int(self.imsize*1.1), rmax=self.rmax,
            tools=["pan","wheel_zoom","box_zoom","reset",self.hover], theta0=np.pi/2,
            clockwise=True)
      self.fig.grid()
      self.fig.taxis_label()


   def RAhDecd2AltAz(self,RA,DEC):
      '''Given an RA/DEC of a constallation vertex, return alt/Az on the sky.
      We let polar.py deal with converting to x,y on the screen. If the vertex
      is below the horizon, set clip=True'''
      radec = SkyCoord(RA, DEC, frame='icrs', unit=degree)
      t = FixedTarget(radec)
      altaz = self.obs.altaz(self.date, t)
      return (90. - altaz.alt.to('degree').value, 
              altaz.az.to('degree').value*np.pi/180.0)

   def computeConAltAz(self):
      alt1s,az1s = self.RAhDecd2AltAz(ra1s, dec1s)
      alt2s,az2s = self.RAhDecd2AltAz(ra2s, dec2s,)
      self.conCDS.data['alt1'] = alt1s
      self.conCDS.data['alt2'] = alt2s
      self.conCDS.data['az1'] = az1s
      self.conCDS.data['az2'] = az2s
      booleans = np.less(alt1s,self.rmax) & np.less(alt2s,self.rmax)
      self.conView.filter = BooleanFilter(booleans=booleans)

   def conLines(self):
      '''Plot the constellation lines'''

      self.computeConAltAz()
      self.fig.segment('alt1','alt2','az1','az2', source=self.conCDS, 
                  view=self.conView, line_color='gray', line_width=0.5)
     

   def plotTargets(self, source, alt, az):
      '''Plots the objects for a given night for the given objects located in
      the CDS source. alt and az must correspond to altitude and azimuth'''

      booleans=np.less(source.data[alt], self.rmax)
      self.targetView = CDSView(filter=BooleanFilter(booleans=booleans))
      scat = self.fig.scatter(alt,az, source=source, view=self.targetView,
                       marker='circle')
      self.hover.renderers = [scat]
      
      # Now need to keep track of all the things the hovertool needs to show

