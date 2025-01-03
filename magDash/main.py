from bokeh.layouts import layout,column
from bokeh.plotting import figure,curdoc
from .query import qData
from .data import ObjectData
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

data = ObjectData()

def Update():
   global UT,ST,AMvline,now,data

   data.now = computeCurrentQuantities(data.data['targets'])
   UT.label = "UT: "+data.now['UT']
   ST.label = "ST: "+data.now['ST']
   data.source.data['HA'] = data.now['HA']

   AMvline.location = data.now['now'].datetime

def updateDataSource(attr,old,new):
   '''Update the data source based on currently-defined filters'''
   global RArange,DECrange,campSelect,ageSlider,source


# ---------------- STATUS FIELDS
#UT = Div(text="{}".format(now['UT']), height=50)
UT = Button(label="UT: "+data.now['UT'], stylesheets=[infoBtn_css])
ST = Button(label="ST: "+data.now['ST'], stylesheets=[infoBtn_css])

columns = [
   TableColumn(field="Name", title="Name"),
   TableColumn(field="HA", title="Hour Ang", 
               formatter=NumberFormatter(format='0.00')),
   TableColumn(field="RA", title="RA", 
               formatter=NumberFormatter(format='0.00000')),
   TableColumn(field="DE", title="DEC", 
               formatter=NumberFormatter(format='0.00000'))
]
table = DataTable(source=data.source, columns=columns, 
                  selectable="checkbox",width=400)

# ---------------- AIRMASS PLOT
AMtoolTips = [("SN","@SN")]

AMfig = figure(width=500, height=400, x_axis_type='datetime',
               x_axis_label='UTC', y_axis_label="Altitude")
AMfig.toolbar.logo = None
AMfig.toolbar_location = None
AMhvr = HoverTool(tooltips=AMtoolTips)
AMfig.add_tools(AMhvr)
AMfig.extra_y_ranges = {"AM": Range1d(start=10, end=90)}
AMfig.varea(x=[data.data['t0'],data.data['ss'].datetime],y1=[0,0], y2=[100,100], 
            fill_color="black", fill_alpha=0.5)
print(data.data['t0'],data.data['ss'].datetime,data.data['te'].datetime)
print(data.data['tb'].datetime,data.data['sr'].datetime,data.data['t1'])
AMfig.varea(x=[data.data['ss'].datetime,data.data['te'].datetime],y1=[0,0], 
            y2=[100,100], fill_color="black", fill_alpha=0.25)
AMfig.varea(x=[data.data['tb'].datetime,data.data['sr'].datetime],y1=[0,0], 
            y2=[100,100], fill_color="black", fill_alpha=0.25)
AMfig.varea(x=[data.data['sr'].datetime,data.data['t1']],y1=[0,0], y2=[100,100], 
            fill_color="black", fill_alpha=0.5)
AMfig.y_range = Range1d(10,90)
AMfig.x_range = Range1d(data.data['t0'],data.data['t1'])
tickloc = list(range(10,100,10))
ax2 = LinearAxis(y_range_name="AM", ticker=FixedTicker(ticks=tickloc),
                 axis_label='Airmass')
ax2.major_label_overrides = {10:"5.76", 20:"2.92", 30:"2.20", 40:"1.56", 50:"1.31",
                             60:"1.15", 70:"1.06", 80:"1.02", 90:"1.00"}
AMfig.add_layout(ax2, 'right')
AMml = AMfig.multi_line(xs="times", ys="alts", source=data.source, hover_color='red')
AMvline = Span(location=data.now['now'].datetime, dimension='height', line_color='red', 
             line_width=3)
AMfig.add_layout(AMvline)
AMhvr.renderers = [AMml]



curdoc().add_root(layout(
   [[data.dataSource,data.magellanCatalog],
    [UT,ST],
    [table,AMfig,column(
      data.RArange,data.DECrange,data.minAirmass,
      data.ageSlider,data.campSelect,data.prioritySelect)
    ]
   ]
))
curdoc().add_periodic_callback(Update, 1000)