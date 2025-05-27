from bokeh.layouts import layout,column
from bokeh.plotting import figure,curdoc
from .query import qData, getLCOsky
from .data import ObjectData
from .compute import computeCurrentQuantities,computeTimes
from .plot_skyview_bokeh import SkyMap
from bokeh.plotting import figure
from bokeh.models import Range1d, Button, LinearAxis, Span,\
                         HoverTool, TabPanel, Tabs, CustomJS,\
                         TapTool,ColumnDataSource, CustomJSHover
from bokeh.models.css import InlineStyleSheet
from bokeh.models.tickers import FixedTicker
import numpy as np

# Global settings
SERVERLOC="local"

infoBtn_css = InlineStyleSheet(css=\
'''
.bk-btn {
font-size: large;
background: grey;
color: #41d849;
}
.bk-btn:hover {
background: grey;
color:41d849 
}
'''
)

data = ObjectData()

def Update1s():
   # stuff to do each second
   global UT,ST,LT

   ut,lt,st = computeTimes()
   UT.label = "UT: "+ut
   ST.label = "ST: "+st
   LT.label = "LT: "+lt


def Update1m():
   # stuff to do every minute
   global data, AMvline, LCOsky, skyplot
   data.now = computeCurrentQuantities(data.data['targets'])
   data.source.data['HA'] = data.now['HA']
   data.source.data['AM'] = data.now['AM']
   data.source.data['zang'] = data.now['zang']
   data.source.data['az'] = data.now['az']*np.pi/180
   data.source.data['alt'] = data.now['alt']
   #print(data.now['now'].datetime)
   AMvline.location = data.now['now'].datetime
   img = getLCOsky()
   LCOsky.data['image'] = [img]
   skyplot.computeConAltAz()


def FilterCallback():
   global data
   newbools = np.array([i in data.source.selected.indices for i in \
                        range(len(data.source.data['Name']))])
   if not np.any(newbools): return
   data.view.filter.booleans = data.view.filter.booleans & newbools

def FilterReset():
   data.source.selected.indices = []
   data.updateViewFilter("","","")


# ---------------- STATUS FIELDS
#UT = Div(text="{}".format(now['UT']), height=50)
LT = Button(label="LT: "+data.now['LT'], stylesheets=[infoBtn_css])
UT = Button(label="UT: "+data.now['UT'], stylesheets=[infoBtn_css])
ST = Button(label="ST: "+data.now['ST'], stylesheets=[infoBtn_css])

table = data.makeTable()

# ---------------- AIRMASS PLOT
AMtoolTips = [("Name","@Name"),("AM","$y{custom}"),("Time","$x{%H:%M}")]
formatter = {'$x': 'datetime',
             '$y': CustomJSHover(code="return (1.0/Math.cos(Math.PI*(90 - value)/180)).toFixed(2)")}

AMfig = figure(width=500, height=400, x_axis_type='datetime',
               x_axis_label='UTC', y_axis_label="Altitude")
AMfig.toolbar.logo = None
AMfig.toolbar_location = None
AMhvr = HoverTool(tooltips=AMtoolTips,formatters=formatter )
AMfig.add_tools(AMhvr)
AMfig.extra_y_ranges = {"AM": Range1d(start=10, end=90)}
AMfig.varea(x=[data.data['t0'],data.data['ss'].datetime],y1=[0,0], y2=[100,100],
            fill_color="black", fill_alpha=0.5)
AMfig.varea(x=[data.data['ss'].datetime,data.data['te'].datetime],y1=[0,0], 
            y2=[100,100], fill_color="black", fill_alpha=0.25)
AMfig.varea(x=[data.data['tb'].datetime,data.data['sr'].datetime],y1=[0,0], 
            y2=[100,100], fill_color="black", fill_alpha=0.25)
AMfig.varea(x=[data.data['sr'].datetime,data.data['t1']],y1=[0,0], y2=[100,100],
            fill_color="black", fill_alpha=0.5)
AMfig.y_range = Range1d(10,90)
print(data.data['t0'],data.data['t1'])
AMfig.x_range = Range1d(data.data['t0'],data.data['t1'])
tickloc = list(range(10,100,10))
ax2 = LinearAxis(y_range_name="AM", ticker=FixedTicker(ticks=tickloc),
                 axis_label='Airmass')
ax2.major_label_overrides = {10:"5.76", 20:"2.92", 30:"2.20", 40:"1.56", 
        50:"1.31", 60:"1.15", 70:"1.06", 80:"1.02", 90:"1.00"}
AMfig.add_layout(ax2, 'right')
AMml = AMfig.multi_line(xs="times", ys="alts", source=data.source, 
                        hover_color='red', line_color='color', view=data.view)


AMvline = Span(location=data.now['now'].datetime, dimension='height', 
        line_color='red', line_width=3)
AMfig.add_layout(AMvline)
AMhvr.renderers = [AMml]

skyplot = SkyMap(imsize=500)
skyplot.conLines()
# Plot zenith-angle, since that's how polar plots work
skyplot.plotTargets(data.source, 'zang', 'az', view=data.view,
                    marker='star', size=10, color='grey',fill_color='color')
img = getLCOsky()
LCOsky = ColumnDataSource(dict(image=[img]))
skyplot.fig.figure.image_rgba(image='image',source=LCOsky, x=-1.033, y=-1.028, dw=2.06, dh=2.06,
                              level='image')
#skyplot.plotTargets(data.source, 'alt','az')
tt = skyplot.fig.figure.select(type=TapTool)
tt.renderers = skyplot.hover.renderers
tt.callback = CustomJS(args=dict(source=data.source), code='''
var index = source.selected.indices[0];
var data = source.data;
var name = data['Name'][index];
source.selected.indices = [];
window.open("https://csp.lco.cl/sn/sn.php?sn="+name,"_SN");
''')


tabs = Tabs(tabs=[
   TabPanel(child=AMfig, title='Airmass'),
   TabPanel(child=skyplot.fig.figure, title='Sky')
])

FilterButton = Button(label='Filter Selected')
FilterButton.on_click(FilterCallback)
FilterResetButton = Button(label='Reset')
FilterResetButton.on_click(FilterReset)

curdoc().add_root(layout(
   [[data.dataSource,data.magellanCatalog,data.CSPpasswd,data.CSPSubmit,
        data.dataSourceMessage],
    [LT,UT,ST],
    [table,tabs,column(
      data.RArange,data.DECrange,data.minAirmass,data.ageSlider,
      data.cadSlider, data.tagSelector,
      data.campSelect,data.prioritySelect, data.observeSelector)
      #data.ageSlider,data.campSelect,data.prioritySelect)
    ],
    [FilterButton,FilterResetButton]
   ]
))
curdoc().add_periodic_callback(Update1s, 1000)
curdoc().add_periodic_callback(Update1m, 60000)
