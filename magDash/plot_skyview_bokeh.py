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

   def __init__(self, location='LCO', date=None):

      self.obs = Observer.at_site(location)
      if date is None:
         self.date = Time.now()
      else:
         self.date = Time(date)
      self._setup()

      self.conCDS = ColumnDataSource(dict(
         RA1=ra1s,
         RA2=ra2s,
         DEC1=dec1s,
         DEC2=dec2s
      ))
      # Initial filtered view
      self.view = CDSView(filter=AllIndices())
                
                
                
   def _setup(self):
      # Setup the graph
      hover = HoverTool()
      hover.tooltips = [("Name", "@label"),
                        ("Type","@type"),("Alt","@alt")]
      #tap = TapTool(callback=OpenURL(url="/navigator/@pk/"), names=['obj'])
     
      self.fig = polar.PolarPlot(height=imsize, width=imsize, rmax=90,
            tools=["pan","wheel_zoom","box_zoom","reset",hover], theta0=pi/2,
            clockwise=True)


   def RAhDecd2AltAz(self,RA,DEC):
      '''Given an RA/DEC of a constallation vertex, return alt/Az on the sky.
      We let polar.py deal with converting to x,y on the screen. If the vertex
      is below the horizon, set clip=True'''
      radec = SkyCoord(RA, DEC, frame='icrs', unit=degree)
      t = FixedTarget(radec)
      altaz = self.obs.altaz(self.date, t)
      clip=np.less(altaz.alt, 0)
      return (90. - altaz.alt.to('degree').value, 
              altaz.az.to('degree').value*np.pi/180.0, clip)

   def conLines(self):
      '''Plot the constellation lines'''

      # Try some constellations
      x1s,y1s,clip1 = self.RAhDecd2AltAz(ra1s, dec1s)
      x2s,y2s,clip2 = self.RAhDecd2AltAz(ra2s, dec2s,)
      gids = ~clip1 & ~clip2
      self.conCDS.data['alt1'] = x1s
      self.conCDS.data['alt2'] = x2s
      self.conCDS.data['az1'] = y1s
      self.conCDS.data['az2'] = y2s
      self.conView.filter = BooleanFilter(booleans=gids)
     
      self.fig.segment('alt1','alt2','az1','az2', source=self.conCDS, 
                  view=self.conView line_color='gray', line_width=0.5)
     

   def plotTargets(source, RA=None, DEC=None, alt=None, az=None):
      '''Plots the objects for a given night for the given objects located in
      the CDS source. Either RA/DEC or alt/az coordinates must be given.'''

      if not ((RA is not None and DEC is not None) or \
              (alt is not None and az is not None)):
         raise ValueError("Error, either RA/DEC or alt/az must be specified")
      
      if RA is not None and DEC is not None:
         # Covert from RA/DEC to alt/az
         

      for obj in objs:
         obj.epoch = date
         theta = obj.azimuth()*pi/180
         rho = 90 - obj.altitude()
         #maxrho = max(rho, maxrho)
         #x = rho*sin(theta)
         #y = rho*cos(theta)
         if obj.objtype == 'PARK': continue
         if obj.objtype not in sources:
            sources[obj.objtype] = {'rho':[], 'theta':[], 'label':[],
                  'text':[], "type":[], "alt":[]}
         #tobj = ax.text(x, y, osymb(obj.objtype), va='center', ha='center')
         sources[obj.objtype]['rho'].append(rho)
         sources[obj.objtype]['theta'].append(theta)
         sources[obj.objtype]['label'].append(obj.name+"*"*obj.rating)
         sources[obj.objtype]['alt'].append(90.0-rho)
         sources[obj.objtype]['type'].append(obj.objtype)
         x,y = fig.rt2xy(rho,theta)
         xs.append(x)
         ys.append(y)
         pks.append("%d" % (obj.pk))
         if obj.objtype in texts:
            sources[obj.objtype]['text'].append(texts[obj.objtype])
         else:
            sources[obj.objtype]['text'].append("")
     
      xypk = ColumnDataSource(dict(x=xs, y=ys, pk=pks))
      if new_window:
         js_redirect = 'window.open("/navigator/"+pk+"/basic", "detailFrame");'
      else:
         js_redirect = 'window.location = "/navigator/"+pk+"/";'
     
      callback = CustomJS(args=dict(source=xypk), code="""
      var mindist = 1000;
      var dist = 0;
      var pk = -1;
      var data = source.data;
      for (var i=0; i < data['x'].length; i++) {
         dist = (cb_obj['x']-data['x'][i])*(cb_obj['x']-data['x'][i]) +
                (cb_obj['y']-data['y'][i])*(cb_obj['y']-data['y'][i]);
         if ( dist < mindist ) { 
            mindist = dist;
            pk = data['pk'][i];
         }
      }   
      if (mindist < 0.001) {
         %s
      }
      """ % js_redirect)
      fig.figure.js_on_event('tap', callback)
      
      # Now need to keep track of all the things the hovertool needs to show
      renderers = []
      for key in sources:
         sources[key]['rho'] = array(sources[key]['rho'])
         sources[key]['theta'] = array(sources[key]['theta'])
         sources[key]['alt'] = array(sources[key]['alt'])
     
         sources[key] = ColumnDataSource(sources[key])
     
         elements = osymb(key)
         for (func,args) in elements:
            f = getattr(fig, func)
            renderers.append(f('rho','theta',source=sources[key], **args))
               
      # Telescope pos
      theta = float(tel_az)*pi/180
      rho = 90 - float(tel_alt)
      fig.annulus([rho], [theta], 7, 8, inner_radius_units='screen',
            outer_radius_units='screen', fill_color='red')
     
      hover.renderers = renderers
     
      fig.grid()
      fig.taxis_label()
      script,div = components(fig.figure, CDN)
      t2 = time.time()
     
      return(script,div)

