import numpy as np
from bokeh.plotting import figure,output_file,show
from bokeh.models import CustomJSTransform
from bokeh.transform import transform

xtransJS = '''
const res = new Array(xs.length)
const r = s.data.%s
const t = s.data.%s
let th = 0
for (let i = 0 ; i < xs.length ; ++i) {
   th = fac*(t[i] - t0)
   if ( th < 0 ) th += 2*Math.PI
   if ( th > 2*Math.PI) th -= 2*Math.PI
   res[i] = r[i]*Math.cos(th)/rmax
}
return res
'''

ytransJS = '''
const res = new Array(xs.length)
const r = s.data.%s
const t = s.data.%s
let th = 0
for (let i = 0 ; i < xs.length ; ++i) {
   th = fac*(t[i] - t0)
   if ( th < 0 ) th += 2*Math.PI
   if ( th > 2*Math.PI) th -= 2*Math.PI
   res[i] = r[i]*Math.sin(th)/rmax
}
return res
'''

class PolarPlot:

   def __init__(self, theta0=0, rmax=1.0, clockwise=True, ntgrid=12, nrgrid=4, 
                **kwargs):

      kwargs['x_axis_label'] = None
      kwargs['y_axis_label'] = None
      kwargs['x_axis_type'] = 'linear'
      kwargs['y_axis_type'] = 'linear'
      kwargs['x_range'] = (-1.1,1.1)
      kwargs['y_range'] = (-1.1,1.1)
      self.figure = figure(**kwargs)

      # Now some arguments specific to this class
      self.theta0 = theta0   # theta0 is angle on horizontal
      self.rmax = rmax       # maximum radius
      self.clockwise = clockwise
      self.nrgrid = nrgrid   # number of angle grid lines
      self.ntgrid = ntgrid   # number of radial grid lines

      self.figure.xgrid.grid_line_color = None
      self.figure.ygrid.grid_line_color = None

      # Draw the outer boundary. Putting it on the annotation level will ensure
      # it masks out data (glyph layer).
      self.figure.circle([0],[0], fill_color=None, line_color="#37435E",
                         line_width=1.5, radius=1.01)
      self.figure.annulus([0],[0],1.01, 2.0, level='annotation',
            fill_color=self.figure.background_fill_color)

      self.figure.yaxis.bounds = (0, 0)
      self.figure.xaxis.bounds = (0, 0)

   def rt2xy(self, r, theta):
      '''Convert input radius, angle coordinates to x,y coordinates on
      the screen.'''
      r = np.asarray(r);  theta = np.asarray(theta)
      t = self.theta2t(theta)
      x = r*np.cos(t)/self.rmax
      y = r*np.sin(t)/self.rmax
      return (x,y)

   def theta2t(self, theta):
      '''Transform theta based on zero-point and clockwise setting.'''
      f = [1.0, -1.0][self.clockwise]
      t = f*(theta - self.theta0)
      t = np.where(t < 0, 2*np.pi+t, t)
      t = np.where(t > 2*np.pi, t-2*np.pi, t)
      return t

   def grid(self, **kwargs):
      '''Draw radial grid. kwargs are sent to p.circle()'''
      radii = (np.arange(self.nrgrid)+1)*1.0/(self.nrgrid+1)
      zeros = np.zeros((4,))
      line_dash=kwargs.get('line_dash', "4 4")
      line_color=kwargs.get('line_color', "gray")
      line_width=kwargs.get('line_width', 0.5)
      self.figure.circle(zeros, zeros, fill_color=None, line_dash=line_dash,
            line_color=line_color, line_width=line_width, radius=radii,
            level='annotation',**kwargs)

      angles_spokes = np.arange(0,self.ntgrid)*np.pi*2/self.ntgrid
      self.figure.ray([0]*self.ntgrid, [0]*self.ntgrid, [1]*self.ntgrid, 
            angles_spokes, line_color=line_color, line_dash=line_dash, 
            line_width=line_width, level='annotation', **kwargs)

   def taxis_label(self, **kwargs):
      '''Label the angular axes. kwargs are sent to p.text()'''
      angles_spokes = np.arange(0,self.ntgrid)*np.pi*2/self.ntgrid
      angle_labels = [str(int(round(a*180./np.pi))) for a in angles_spokes]
      t_spokes = self.theta2t(angles_spokes)
      x_labels,y_labels = self.rt2xy(angles_spokes*0+self.rmax*1.03, 
                                     angles_spokes)
      self.figure.text(x_labels, y_labels, angle_labels, angle=-np.pi/2+t_spokes,
         text_font_size="11pt", text_align="center", text_baseline="bottom",
         text_color="gray", level='annotation')

   
   def bind_bokeh(self, name):
      def bfunc(r, t, *args, **kwargs):
         f = getattr(self.figure, name, None)
         if f is None:
            raise AttributeError(name)
         source = kwargs.get('source', None)
         if source is not None:
            # A source is being used, so convert it at the ColumnSource level
            #x,y = self.rt2xy(source.data[r], source.data[t])
            #source.add(x, '_x')
            #source.add(y, '_y')
            xtrans = CustomJSTransform(args=dict(s=source,rmax=self.rmax,t0=self.theta0,
                                       fac=[1,-1][self.clockwise]), v_func=xtransJS % (r,t))
            ytrans = CustomJSTransform(args=dict(s=source,rmax=self.rmax,t0=self.theta0,
                                       fac=[1,-1][self.clockwise]),v_func=ytransJS % (r,t))
            #return f(*(('_x','_y')+args), **kwargs)
            return f(*((transform(r,xtrans),transform(t,ytrans))+args), **kwargs)
         else:
            return f(*(self.rt2xy(r,t)+args), **kwargs)
      return bfunc

   def bind_bokeh2(self, name):
      # Special version that has two x's and two y's (e.g., segment)
      def bfunc(r0, r1, t0, t1, *args, **kwargs):
         f = getattr(self.figure, name, None)
         if f is None:
            raise AttributeError(name)
         source = kwargs.get('source', None)
         if source is not None:
            xtrans0 = CustomJSTransform(args=dict(s=source,rmax=self.rmax,t0=self.theta0,
                                       fac=[1,-1][self.clockwise]), v_func=xtransJS % (r0,t0))
            xtrans1 = CustomJSTransform(args=dict(s=source,rmax=self.rmax,t0=self.theta0,
                                       fac=[1,-1][self.clockwise]), v_func=xtransJS % (r1,t1))
            ytrans0 = CustomJSTransform(args=dict(s=source,rmax=self.rmax,t0=self.theta0,
                                       fac=[1,-1][self.clockwise]), v_func=ytransJS % (r0,t0))
            ytrans1 = CustomJSTransform(args=dict(s=source,rmax=self.rmax,t0=self.theta0,
                                       fac=[1,-1][self.clockwise]), v_func=ytransJS % (r1,t1))
            return f(*((transform(r0,xtrans0),transform(t0,ytrans0),
                        transform(r1,xtrans1),transform(t1,ytrans1))+args), **kwargs)
         else:
            return f(*(self.rt2xy(r0,t0)+self.rt2xy(r1,r1)+args), **kwargs)
      return bfunc

   def __getattr__(self, key):
      if key in self.__dict__:
         return self.__dict__[key]
      elif key in ['annular_wedge','annulus','arc','asterisk',
            'circle','circle_cross','circle_x','cross','diamond',
            'diamond_cross','ellipse','inverted_triangle','line',
            'multi_line','oval','patch','patches','ray','rect',
            'scatter','square','square_cross','square_x','text',
            'triangle','wedge','x']:
         return self.bind_bokeh(key)
      elif key in ['segment']:
         return self.bind_bokeh2(key)
      elif key in self.figure.__dict__:
         return self.figure.__dict__[key]
      raise AttributeError(key)

if __name__ == '__main__':
    from bokeh.plotting import ColumnDataSource
    from bokeh.models import HoverTool
    from bokeh.models import ImageURL
    from PIL import Image
    import pickle
    import numpy as np

    f = open('Conlines3.pkl','rb')
    d = pickle.load(f)
    output_file("polar.html")

    angles = np.random.uniform(0,2*np.pi, size=100)
    r = np.random.uniform(0,1, size=100)
    size = np.random.uniform(1,5, size=100)
    marker = ['circle']*50 + ['square']*50
    source = ColumnDataSource(data=dict(r=r, angles=angles, size=size))
    hover = HoverTool()
    hover.tooltips=[("(R,T)", "(@r,@angles)")]
    p = PolarPlot(width=500, height=500, min_border=0, clockwise=True,
          theta0=np.pi, rmax=1, tools=[hover])
    p.grid()
    p.taxis_label()
    plot= p.scatter('r', 'angles', size='size', color='teal', source=source,
          name='stars')
    hover.renderers=[plot]

    show(p.figure)
