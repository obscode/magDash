from bokeh.layouts import layout,column
from bokeh.plotting import figure,curdoc
from .query import qData
from .compute import computeNightQuantities,computeCurrentQuantities
from bokeh.plotting import figure
from bokeh.models import DataTable, Range1d, TableColumn, NumberFormatter,\
                         ColumnDataSource, Button, Div, LinearAxis, Span,\
                         HoverTool, MultiChoice, RangeSlider, CheckboxButtonGroup
from bokeh.models.css import InlineStyleSheet
from bokeh.models.tickers import FixedTicker

infoBtn_css = InlineStyleSheet(css=\
'''
.bk-btn {
font-size: large;
background: grey;
color: #41d849;
}
'''
)

def Update():
   global UT,ST,AMvline,now,data,source

   now = computeCurrentQuantities(data['targets'])
   UT.label = "UT: "+now['UT']
   ST.label = "ST: "+now['ST']
   source.data['HA'] = now['HA']

   AMvline.location = now['now'].datetime

def updateDataSource(attr,old,new):
   '''Update the data source based on currently-defined filters'''
   global RArange,DECrange,campSelect,ageSlider

   print(attr,old,new)

data = qData('QSWO')
data = computeNightQuantities(data)
  
now = computeCurrentQuantities(data['targets'])
  
dts = [t.datetime for t in data['times']]
source = ColumnDataSource(dict(
   times=[dts for x in data['AM']],
   AMs = [list(x) for x in data['AM']],
   alts = [list(x) for x in data['alt']],
   SN = data['SN'],
   RA = data['RA'],
   DE = data['DE'],
   HA = now['HA']
))

  
# ---------------- STATUS FIELDS
#UT = Div(text="{}".format(now['UT']), height=50)
UT = Button(label="UT: "+now['UT'], stylesheets=[infoBtn_css])
ST = Button(label="ST: "+now['ST'], stylesheets=[infoBtn_css])

columns = [
   TableColumn(field="SN", title="SN"),
   TableColumn(field="HA", title="Hour Ang", 
               formatter=NumberFormatter(format='0.00')),
   TableColumn(field="RA", title="RA", 
               formatter=NumberFormatter(format='0.00000')),
   TableColumn(field="DE", title="DEC", 
               formatter=NumberFormatter(format='0.00000'))
]
table = DataTable(source=source, columns=columns, selectable="checkbox",width=400)

# ---------------- AIRMASS PLOT
AMtoolTips = [("SN","@SN")]

AMfig = figure(width=500, height=400, x_axis_type='datetime',
               x_axis_label='UTC', y_axis_label="Altitude")
AMfig.toolbar.logo = None
AMfig.toolbar_location = None
AMhvr = HoverTool(tooltips=AMtoolTips)
AMfig.add_tools(AMhvr)
AMfig.extra_y_ranges = {"AM": Range1d(start=10, end=90)}
AMfig.varea(x=[dts[0],data['ss'].datetime],y1=[0,0], y2=[100,100], fill_color="black",
            fill_alpha=0.5)
AMfig.varea(x=[data['ss'].datetime,data['te'].datetime],y1=[0,0], y2=[100,100], 
            fill_color="black", fill_alpha=0.25)
AMfig.varea(x=[data['tb'].datetime,data['sr'].datetime],y1=[0,0], y2=[100,100], 
            fill_color="black", fill_alpha=0.25)
AMfig.varea(x=[data['sr'].datetime,dts[-1]],y1=[0,0], y2=[100,100], fill_color="black",
            fill_alpha=0.5)
AMfig.y_range = Range1d(10,90)
AMfig.x_range = Range1d(dts[0],dts[-1])
tickloc = list(range(10,100,10))
ax2 = LinearAxis(y_range_name="AM", ticker=FixedTicker(ticks=tickloc),
                 axis_label='Airmass')
ax2.major_label_overrides = {10:"5.76", 20:"2.92", 30:"2.20", 40:"1.56", 50:"1.31",
                             60:"1.15", 70:"1.06", 80:"1.02", 90:"1.00"}
AMfig.add_layout(ax2, 'right')
AMml = AMfig.multi_line(xs="times", ys="alts", source=source, hover_color='red')
AMvline = Span(location=now['now'].datetime, dimension='height', line_color='red', 
             line_width=3)
AMfig.add_layout(AMvline)
AMhvr.renderers = [AMml]

# ------------------ FILTERS
RArange = RangeSlider(start=0, end=24, value=(0,24), step=0.25, title='RA')
RArange.on_change('value',updateDataSource)
DECrange = RangeSlider(start=-90, end=90, value=(-90,90), step=0.5, title='DEC')
ageSlider = RangeSlider(start=0, end=100, value=(0,100), step=1., title="Age")
CAMP_OPTIONS = ['2024A','2024B','2025A']
campSelect = MultiChoice(value=[], options=CAMP_OPTIONS, title='Campaigns')
PRIORITY_OPTIONS = ['Raw-High','High','Medium','Med-rare','Low','Monthly','Calib',
                    'Template']
prioritySelect = CheckboxButtonGroup(active=[], labels=PRIORITY_OPTIONS)


curdoc().add_root(layout([[UT,ST],[table,AMfig,column(
   RArange,DECrange,ageSlider,campSelect,prioritySelect)]]))
curdoc().add_periodic_callback(Update, 1000)