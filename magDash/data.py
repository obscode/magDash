'''Data.py:  Module for loading, preparing, and filtering data'''

from . import query
from bokeh.models import (RangeSlider, Slider, Select, CheckboxButtonGroup,
                          MultiChoice, ColumnDataSource, FileInput,
                          TableColumn, NumberFormatter, DataTable,
                          HTMLTemplateFormatter,CDSView,PasswordInput,Button,
                          Div)
from bokeh.models.filters import BooleanFilter,AllIndices
import base64
from astropy.coordinates import SkyCoord
from astropy import units as u
from astropy.time import Time
from .compute import computeCurrentQuantities,computeNightQuantities
import numpy as np
import traceback

def readMagCat(input):
   fields = ['ID','Name','RA','DE','equinox','pmRA','pmDEC','rotoff','rotmode',
             'gp1RA','gp1DEC','gp1equ','gp2RA','gp2DEC','gp2equ','obsEpoch',
             'comm']

   data = {}.fromkeys(fields)
   for field in fields:  data[field] = []
   lines = input.split(b'\n')
   N = 0
   for line in lines:
      line = line.decode("utf-8")
      if len(line) == 0 or line[0] == "#": continue
      
      N += 1
      # check of end comment (which may have spaces)
      fs = line.split('#')
      if len(fs) == 1:
         data['comm'].append('')
      elif len(fs) == 2:
         data['comm'].append(fs[1].strip())
      else:
         # '#' includded in comment
         data['comm'].append('#'.join(fs[1:]))

      fs = fs[0].split()
      if len(fs) > 16:
         # Treat end fields as comments. This is not the stndard, but whatevs
         data['comm'][-1] += " ".join(fs[16:])
         fs = fs[:16]

      for i in range(len(fs)):
         field = fields[i]
         if field in ['equinox','pmRA','pmDEC','rotoff','gp1equ','gp2equ',
                      'obsEpoch']:
            data[field].append(float(fs[i]))
         else:
            data[field].append(fs[i])
      if i < 15:
         # Missing data
         for i in range(i+1,16):
            field = fields[i]
            if field in ['equinox','pmRA','pmDEC','rotoff','gp1equ','gp2equ',
                         'obsEpoch']:
               data[field].append(0)
            else:
               data[field].append('')

      coord = SkyCoord(data['RA'][-1],data['DE'][-1], 
                       unit=(u.hourangle,u.degree))
      data['RA'][-1] = coord.ra.to('hourangle').value
      data['DE'][-1] = coord.dec.to('degree').value
      if len(fs) == 15:    # No epoch given... assume 0.0
         data['obsEpoch'].append(0.0)
   data['N'] = N
      
   return data


class ObjectData:

   DS_OPTIONS = ['Magellan Catalog','POISE:Swope','POISE:IMACS','POISE:FIRE']
   PRIORITY_OPTIONS = ['Raw-High','High','Medium','Med-rare','Low','Monthly',
                          'Calib','Template']
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
      # Initially invisible, since default is Magellan catalog
      self.CSPpasswd = PasswordInput(title='CSP passwd:', value="", 
                                 visible=False)
      self.CSPSubmit = Button(label="Get Data", visible=False,
                              margin=(25,5,5,5))
      self.CSPSubmit.on_click(self.fetchQueue)
      self.dataSourceMessage = Div(text="N/A", width=200, margin=(25,5,5,5),
                                   visible=False)

      self.filter = BooleanFilter(booleans=[])
      
      # ------------------ FILTERS
      self.RArange = RangeSlider(start=0, end=24, value=(0,24), step=0.25, 
                                 title='RA')
      self.RArange.on_change('value_throttled',self.updateViewFilter)
      self.DECrange = RangeSlider(start=-90, end=90, value=(-90,90), step=0.5, 
                                  title='DEC')
      self.DECrange.on_change('value_throttled', self.updateViewFilter)
      self.minAirmass = Slider(start=1, end=3, step=0.02, value=3,
                               title="Minimum Airmass")
      self.tagSelector = MultiChoice(value=[], options=[], title="Tags",
                                     visible=False, min_width=200)
      self.tagSelector.on_change('value', self.updateViewFilter)
      self.minAirmass.on_change('value_throttled', self.updateViewFilter)
      self.ageSlider = RangeSlider(start=0, end=100, value=(0,100), step=1., 
                                   title="Age", visible=False)
      self.ageSlider.on_change('value_throttled', self.updateViewFilter)
      self.cadSlider = RangeSlider(start=0, end=100, value=(0,100), step=1., 
                                   title="Cadence", visible=False)
      self.cadSlider.on_change('value_throttled', self.updateViewFilter)
      self.campSelect = MultiChoice(value=[], options=[], 
                                    title='Campaigns', visible=False)
      self.campSelect.on_change('value', self.updateViewFilter)
      self.prioritySelect = CheckboxButtonGroup(active=[], 
         labels = self.PRIORITY_OPTIONS, visible=False)
      self.prioritySelect.on_change('active', self.updateViewFilter)

      # -----  The initial DataColumnSource with no objects
      self.data = dict(
         RA = np.array([]),
         DE = np.array([]),
         alts = np.array([]),
         alt = np.array([]),
         az = np.array([]),
         ID = [],
         AM = np.array([]),
         Name = [],
         comm = []
      )
      self.data = computeNightQuantities(self.data)
      self.now = computeCurrentQuantities(self.data['targets'])
      self.source = None
      self.view = None
      self.makeDataSource()
      self.Nameformatter = HTMLTemplateFormatter(template=\
         '<strong> <%= value %> </strong>')
      #self.view = CDSView(filter=AllIndices())

      self.table = None
      self.AMfig = None

   def updateDataSource(self, attr, old, new):
      self.dataSourceMessage.visible = False # reset
      if new in self.QSTRS:
         # POISE data from SQL and has more filters
         self.CSPpasswd.visible = True
         self.CSPSubmit.visible = True
         self.magellanCatalog.visible = False
         if query.PASS:
            self.CSPpasswd.value = query.PASS
            self.fetchQueue()
      else:
         self.CSPpasswd.visible = False
         self.CSPSubmit.visible = False
         self.magellanCatalog.visible = True
         self.ageSlider.visible = False
         self.cadSlider.visible = False
         self.campSelect.visible = False
         self.prioritySelect.visible = False
         self.table.columns[1].formatter = HTMLTemplateFormatter(template=\
         '<strong> <%= value %> </strong>')

   def updateViewFilter(self, attr, old, new):
      data = self.source.data
      bools = (data['RA'] >= self.RArange.value[0]) & \
         (data['RA'] <= self.RArange.value[1])
      bools &= ((data['DE'] >= self.DECrange.value[0]) & \
         (data['DE'] <= self.DECrange.value[1]))
      if self.minAirmass.value < 3:
         bools &= np.array([AMs.min() < self.minAirmass.value \
                            for AMs in data['AMs']]) 
      if self.ageSlider.visible:
         bools &= ((data['age'] >= self.ageSlider.value[0]) &\
                   (data['age'] <= self.ageSlider.value[1]))
      if self.cadSlider.visible:
         bools &= (np.isnan(data['cad']) | ((data['cad'] >= self.cadSlider.value[0]) &\
                   (data['cad'] <= self.cadSlider.value[1])))
      if self.tagSelector.value:
         bools &= np.array([tag in self.tagSelector.value \
                         for tag in data['Tags']])
      if self.campSelect.visible and self.campSelect.value:
         bools &= np.array([tag in self.campSelect.value \
                            for tag in data['camp']])
      if self.prioritySelect.visible and self.prioritySelect.active:
         selected_priorities = [self.prioritySelect.labels[idx] \
                                for idx in self.prioritySelect.active]
         bools &= np.array([tag in selected_priorities \
                            for tag in data['priority']])
      
      self.view.filter = BooleanFilter(booleans=bools)

   def makeDataSource(self):
      '''Given the current data, create the ColumnDataSource'''
      if self.data is None:
         return
      dts = [t.datetime for t in self.data['times']]
      d = dict(times=[dts for x in self.data['AM']],
               AMs = [np.array(x) for x in self.data['AM']],
               AM = np.array(self.data['AM']),
               alts = [np.array(x) for x in self.data['alts']],
               Name = self.data['Name'],
               RA = np.array(self.data['RA']),
               DE = np.array(self.data['DE']),
               alt = np.array(self.now['alt']),
               zang = np.array(self.now['zang']),         # Should be in degrees
               az = np.array(self.now['az'])*np.pi/180,   # Make sure in radians
               ID = self.data['ID'],
               HA = np.array(self.now['HA']),
               Tags = self.data['comm']
         )

      # Some CSP-specific data
      if 'camp' in self.data:
         d['camp'] = self.data['camp']      
         self.campSelect.options = list(set(self.data['camp']))
      if 'priority' in self.data:
         d['priority'] = self.data['priority']
         self.prioritySelect.labels = [priority \
                                       for priority in self.PRIORITY_OPTIONS \
                                       if priority in self.data['priority']]
      if 'agerdate' in self.data:
         epoch = np.array(self.data['agerdate'])
         d['age'] = np.where(epoch > 1.0, self.now['now'].jd - epoch, 0.0)
         self.ageSlider.start = d['age'].min()-1
         self.ageSlider.end = d['age'].max()+1
         self.ageSlider.step = (self.ageSlider.end-self.ageSlider.start)/100
         self.ageSlider.value = (self.ageSlider.start, self.ageSlider.end)
      if 'utobs' in self.data:
         # UT date of last observation
         print(self.data['utobs'])
         UTs = Time(self.data['utobs'])
         deltat = self.now['now'].jd - UTs.jd
         d['cad'] = np.where(deltat < 9000, deltat, np.nan)
         self.cadSlider.start = d['cad'][~np.isnan(d['cad'])].min()-1
         self.cadSlider.end = d['cad'][~np.isnan(d['cad'])].max()+1
         self.cadSlider.step = (self.cadSlider.end-self.cadSlider.start)/100
         self.cadSlider.value = (self.cadSlider.start, self.cadSlider.end)
         
      if self.source is not None:
         self.source.data = d
      else:
         self.source = ColumnDataSource(d)

      booleans = np.ones((len(d['Name'])), dtype=bool)
      if self.view is not None:
         self.view.filter.booleans = booleans
      else:
         self.view = CDSView(filter=BooleanFilter(booleans=booleans))

      tags = list(set([tag for tag in self.data['comm'] if tag]))
      if len(tags) > 0:
         self.tagSelector.options = tags
         self.tagSelector.visible = True
      else:
         self.tagSelector.visible = False

   def fetchQueue(self):
      query.PASS= self.CSPpasswd.value
      try:
         self.data = query.qData(self.QSTRS[self.dataSource.value])
         self.dataSourceMessage.text = "<font color='darkgreen'>"\
            "Retreived {} targets</font>".format(self.data['N'])
         self.dataSourceMessage.visible = True
      except:
         self.dataSourceMessage.text = "<font color='red'>Query failed</font>"
         self.dataSourceMessage.visible = True
         print(traceback.format_exc())
         return

      self.ageSlider.visible = True
      self.cadSlider.visible = True
      self.campSelect.visible = True
      self.prioritySelect.visible = True
      self.data = computeNightQuantities(self.data)
      self.now = computeCurrentQuantities(self.data['targets']) 
      self.makeDataSource()
      self.table.columns[1].formatter = HTMLTemplateFormatter(template=\
         '<a href="https://csp.lco.cl/sn/sn.php?sn=<%= value %>" '\
         'target="_SN"><%= value %></a>')
      self.table.columns[-1].visible=True

   def uploadCatalog(self, attr, old, new):
      try:
         self.data = readMagCat(base64.b64decode(new))
         self.dataSourceMessage.text = "<font color='darkgreen'>"\
            "Uploaded {} targets</font>".format(self.data['N'])
         self.dataSourceMessage.visible = True
      except:
         self.dataSourceMessage.text = "<font color='red'>Upload failed</font>"
         self.dataSourceMessage.visible = True
         return
      self.data = computeNightQuantities(self.data)
      self.now = computeCurrentQuantities(self.data['targets'])
      self.makeDataSource()
      self.table.source = self.source

   def makeTable(self):

      columns = [
      TableColumn(field="ID", title="ID", width=10),
      TableColumn(field="Name", title="Name", formatter=self.Nameformatter),
      TableColumn(field="HA", title="HA", 
               formatter=NumberFormatter(format='0.00'), width=100),
      TableColumn(field="RA", title="RA", 
               formatter=NumberFormatter(format='0.00000'),
               visible=False),
      TableColumn(field="DE", title="DEC", 
               formatter=NumberFormatter(format='0.00000'), visible=False),
      TableColumn(field="AM", title="Airm", 
               formatter=NumberFormatter(format='0.00'),width=100),
      TableColumn(field="age", title="Age", 
                     formatter=NumberFormatter(format="0.0"), visible=False)]
      TableColumn(field="cad", title="Cad", 
                     formatter=NumberFormatter(format="0.0"), visible=False)]
      self.table = DataTable(source=self.source, view=self.view,
                  columns=columns, selectable="checkbox",width=400, height=500,
                  index_position=None, scroll_to_selection=False)
      return(self.table)
