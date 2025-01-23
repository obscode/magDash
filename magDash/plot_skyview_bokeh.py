#!/usr/bin/env python

'''Plot a skymap using the Bokeh plotting package. Bokeh has the big 
advantage of embedding directly into the HTML canvas with a given size,
making it easier to place than a matplotlib-generated image. Intractions
are also much much better.'''

import os
from . import polar
from bokeh.plotting import ColumnDataSource
from bokeh.embed import components
from bokeh.resources import CDN
from bokeh.models import HoverTool, OpenURL, TapTool, CustomJS
from numpy import *
from .models import genMWO
import pickle
try:
   import ephem3 as ephem
except:
   import ephem
import pickle

from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.units import degree
from astropy.time import Time
import time



# The constellation data.
conlines = os.path.join(os.path.dirname(__file__), 'Conlines3.pkl')
with open(conlines, 'rb') as f:
   ra1s,ra2s,dec1s,dec2s = pickle.load(f)

MWO = EarthLocation.of_site('mwo')

# How to plot different types. The dictionary is keyed by object type. the value
# is a list of plotting instructions. Some objects are plotted with multiple
# elements, so each member of the list is a plotting element composed of a 
# 2-tuple:  the plotting element and the options controlling the size etc.
# Note that some elements (like oval and text) currently dont' work with the
# Tap tool, so we add invisible circle elements to trigger this event.
symbols = {
      'GC':[('scatter',{'marker':'circle_cross','fill_color':None,'size':10,'name':'obj'})],
      'SS':[('circle',{'size':10,'fill_color':'yellow','line_color':'black',
                       'name':'obj'}),
            ('circle',{'size':1, 'fill_color':'black'})],
      'PN':[('circle', {'size':5, 'line_color':'blue', 'name':'obj'})],
      'OC':[('circle', {'size':20, 'line_color':'blue','line_dash':'4 4',
         'name':'obj', 'fill_color':None})],
      'QSO':[('circle', {'size':10, 'line_color':'red','name':'obj'})]}
texts = {
      'Double':':',
      'Triple':':.'}
for name in ['E/RN','EN','EN-OC','E/DN','RN','SNR']:
   symbols[name] = [('square', {'size':10, 'line_color':'black','name':'obj'})]

def osymb(s):
   '''returns an appropriate symbol to use based on object type.'''
   if s[0:2] == 'G-':
      # galaxy
      return [('ellipse', {'width':15, 'height':7, 'angle':45, 
         'line_color':'black','fill_color':None, 'width_units':'screen',
         'height_units':'screen'}),
              ('circle', {'size':5, 'line_color':'white', 'fill_color':None,
                          'name':'obj'})]
   if s in symbols:
      return symbols[s]
   if s in texts:
      return [('text', {'text':'text',"text_align":"center","text_baseline":"middle"}),
            ('circle',{"size":5, "line_color":None, "fill_color":None,
                       "name":"obj"})]
   # default:
   return [('asterisk', {'size':6,'name':'obj'})]

def RAhDecd2AltAz(RA,DEC,utctime):
   '''Given an RA/DEC of a constallation vertex, return alt/Az on the sky.
   We let polar.py deal with converting to x,y on the screen. If the vertex
   is below the horizon, set clip=True'''
   radec = SkyCoord(RA, DEC, frame='icrs', unit=degree)
   altaz = radec.transform_to(AltAz(obstime=utctime, location=MWO))
   clip=less(altaz.alt, 0)
   return (90. - altaz.alt.value, altaz.az.value*pi/180.0, clip)


def plot_sky_map(objs, date=None, new_window=False, airmass_high=None,
      tel_alt=90, tel_az=45, imsize=500, crop=90):
   '''Plots the objects for a given night for the given objects (expected to
   be of type Objects).  Returns two strings:  the <script> element that should
   be placed in the header, and the <div> that should be placed where you want
   the graph to show up.'''
   t1 = time.time()
   if date is None:
      date = ephem.now()
   else:
      date = ephem.Date(date)

   MWO = genMWO(date)

   # Setup the graph
   hover = HoverTool()
   hover.tooltips = [("Name", "@label"),
                     ("Type","@type"),("Alt","@alt")]
   #tap = TapTool(callback=OpenURL(url="/navigator/@pk/"), names=['obj'])

   fig = polar.PolarPlot(height=imsize, width=imsize, rmax=90,
         tools=["pan","wheel_zoom","box_zoom","reset",hover], theta0=pi/2,
         clockwise=True)
   
   sources = {}
   xs = []; ys = []
   pks = []
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

   # Try some constellations
   x1s,y1s,clip1 = RAhDecd2AltAz(ra1s, dec1s, 
                 Time(date+2415020, format='jd'))
   x2s,y2s,clip2 = RAhDecd2AltAz(ra2s, dec2s, 
                 Time(date+2415020, format='jd'))
   gids = ~clip1 & ~clip2

   x1s = x1s[gids]; x2s = x2s[gids]; y1s = y1s[gids]; y2s = y2s[gids]
   fig.segment(x1s,y1s,x2s,y2s, line_color='gray', line_width=0.5)

   hover.renderers = renderers

   fig.grid()
   fig.taxis_label()
   script,div = components(fig.figure, CDN)
   t2 = time.time()

   return(script,div)

