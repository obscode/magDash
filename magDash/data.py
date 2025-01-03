'''Data.py:  Module for loading, preparing, and filtering data'''

from .query import qData
from bokeh.models import (RangeSlider, Slider, Select, CheckboxButtonGroup,
                          MultiChoice, ColumnDataSource, FileInput)
from bokeh.models.filters import BooleanFilter
import base64
from astropy.coordinates import SkyCoord
from astropy import units as u
from .compute import computeCurrentQuantities,computeNightQuantities


def readMagCat(input):
   fields = ['ID','Name','RA','DE','equinox','pmRA','pmDEC','rotoff','rotmode',
             'gp1RA','gp1DEC','gp1equ','gp2RA','gp2DEC','gp2equ','obsEpoch',
             'comm']

   data = {}.fromkeys(fields)
   for field in fields:  data[field] = []
   lines = input.split(b'\n')
   for line in lines:
      line = line.decode("utf-8")
      if len(line) == 0 or line[0] == "#": continue
      fs = line.split()
      for i in range(len(fs)):
         field = fields[i]
         if field in ['equinox','pmRA','pmDEC','rotoff','gp1equ','gp2equ',
                      'obsEpoch']:
            data[field].append(float(fs[i]))
         else:
            data[field].append(fs[i])
      coord = SkyCoord(data['RA'][-1],data['DE'][-1], 
                       unit=(u.hourangle,u.degree))
      data['RA'][-1] = coord.ra.to('hourangle').value
      data['DE'][-1] = coord.dec.to('degree').value
      if len(fs) == 15:    # No epoch given... assume 0.0
         data['obsEpoch'].append(0.0)
      
      # If anything is left after a '#', add as a comment
      fs = line.split('#')
      if len(fs) > 1:
         data['comm'].append('#'.join(fs[1:]))
      else:
         data['comm'].append('')

   return data


class ObjectData:

   DS_OPTIONS = ['Magellan Catalog','POISE:Swope','POISE:IMACS','POISE:FIRE']
   QSTRS = {'POISE:Swope':"QSWO",
            'POISE:IMACS':"QWFCCD",
            'POISE:FIRE':"QFIRE"}
   
   def __init__(self):

      # ---------------- Data source and Filters ----------------------
      self.dataSource = Select(title='Data Source', value='Magellan Catalog', 
                               options=self.DS_OPTIONS)
      self.dataSource.on_change('value', self.updateDataSource)
      self.magellanCatalog = FileInput(title="Upload Catalog:")
      self.magellanCatalog.on_change('value', self.uploadCatalog)

      self.filter = BooleanFilter(booleans=[])
      
      # ------------------ FILTERS
      self.RArange = RangeSlider(start=0, end=24, value=(0,24), step=0.25, 
                                 title='RA')
      self.RArange.on_change('value_throttled',self.updateFilterRA)
      self.DECrange = RangeSlider(start=-90, end=90, value=(-90,90), step=0.5, 
                                  title='DEC')
      self.DECrange.on_change('value_throttled', self.updateFilter)
      self.minAirmass = Slider(start=1, end=5, step=0.1, value=5,
                               title="Minimum Airmass")
      self.tagSelector = MultiChoice(value=[], options=[], title="Tags",
                                     visible=False)
      self.minAirmass.on_change('value_throttled', self.updateFilter)
      self.ageSlider = RangeSlider(start=0, end=100, value=(0,100), step=1., 
                                   title="Age", visible=False)
      self.ageSlider.on_change('value_throttled', self.updateFilter)
      CAMP_OPTIONS = ['2024A','2024B','2025A']
      self.campSelect = MultiChoice(value=[], options=CAMP_OPTIONS, 
                                    title='Campaigns', visible=False)
      self.campSelect.on_change('value', self.updateFilter)
      PRIORITY_OPTIONS = ['Raw-High','High','Medium','Med-rare','Low','Monthly',
                          'Calib','Template']
      self.prioritySelect = CheckboxButtonGroup(active=[], 
                                                labels=PRIORITY_OPTIONS,
                                                visible=False)
      self.prioritySelect.on_change('active', self.updateFilter)

      # -----  The initial DataColumnSource with no objects
      self.data = dict(
         RA = [],
         DE = [],
         ID = [],
         Name = [],
         comm = []
      )
      self.data = computeNightQuantities(self.data)
      self.now = computeCurrentQuantities(self.data['targets'])
      self.makeDataSource()

   def updateDataSource(self, attr, old, new):
      if new in self.QSTRS:
         # POSIE data from SQL and has more filters
         self.magellanCatalog.visible = False
         self.ageSlider.visible = True
         self.campSelect.visible = True
         self.prioritySelect.visible = True
         self.data = qData(self.QSTRS[new])
         print(self.data)
         self.data = computeNightQuantities(self.data)
         self.now = computeCurrentQuantities(self.data['targets']) 
         self.makeDataSource()
      else:
         self.magellanCatalog.visible = True
         self.ageSlider.visible = False
         self.campSelect.visible = False
         self.prioritySelect.visible = False

   def updateFilterRA(self, attr, old, new):
      RAs = self.source.data['RA']
      bools = []
      for i,RA in enumerate(RAs):
         bools.append(self.filter.booleans[i] and (\
            self.RArange.value[0] <= RA <= self.RArange.value[1])
         )
      self.filter.booleans = bools

   def updateFilter(self, attr, old, new):
      pass

   def makeDataSource(self):
      '''Given the current data, create the ColumnDataSource'''
      if self.data is None:
         return
      dts = [t.datetime for t in self.data['times']]
      self.source = ColumnDataSource(dict(
         times=[dts for x in self.data['AM']],
         AMs = [list(x) for x in self.data['AM']],
         alts = [list(x) for x in self.data['alt']],
         Name = self.data['Name'],
         RA = self.data['RA'],
         DE = self.data['DE'],
         HA = self.now['HA'],
         Tags = self.data['comm']
      ))
      tags = list(set([tag for tag in self.data['comm'] if tag]))
      if len(tags) > 0:
         self.tagSelector.options = tags
         self.tagSelector.visible = True
      else:
         self.tagSelector.visible = False

   def uploadCatalog(self, attr, old, new):
      self.data = readMagCat(base64.b64decode(new))
      self.data = computeNightQuantities(self.data)
      self.now = computeCurrentQuantities(self.data['targets'])
      self.makeDataSource()

