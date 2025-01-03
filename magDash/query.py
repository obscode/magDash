'''Query functions to get data.'''
import pymysql
from bokeh.models import ColumnDataSource
from astropy.coordinates import SkyCoord
from astropy import units as u
from astroplan import Observer, FixedTarget
from astropy.time import Time
import numpy as np
from functools import cache
import datetime

HOST='sql.obs.carnegiescience.edu'
USER='CSP'
PASS='H!=75.0'
DB='CSP'

def airmass(h):
   '''Computer airmass from Pickering (2002) given altitude angle h'''
   nh = np.where(h > 0, h, 0.001)
   arg = nh + 244./(165. + 47.*np.power(nh, 1.1))
   return np.power(np.sin(arg*np.pi/180), -1) 

Q_query = '''
select t0.*,t2.mag,t2.night,t2.jd 
  from SNList t0 left join (
    select t1.field as field,t1.night as night,t1.mag as mag, max(t1.jd) as jd
    from (
      select * from MAGSN where filt="r" and obj<1 order by night desc
    ) as t1 group by field
  ) t2 on (t0.SN=t2.field or t0.NAME_CSP=t2.field or t0.NAME_IAU=t2.field or 
           t0.NAME_PSN=t2.field) 
WHERE ACTIVE = "1" and {} = "1" ORDER BY RA'''

Q_names = ['ID','SN','type','RA','DE','zc','zcmb','zvrb','dmag','host',
   'offew','offns','gtype','comm','survey','active','camp','agerdate',
   'datemeans','name_iau','name_psn','guider','nstd','qswo','qfire','qrc',
   'qwfccd','name_csp','qc0','inot','qalfosc','qnotcam','qlcogt','qfsu',
   'qlmc','mag','night','jd']

@cache
def qData(queue='QSWO'):
   db = pymysql.connect(host=HOST, user=USER, passwd=PASS, db=DB)
   c = db.cursor()
   N = c.execute(Q_query.format(queue))
   rows = c.fetchall()
   data = {}.fromkeys(Q_names)
   for i,name in enumerate(Q_names):
      data[name] = [row[i] for row in rows]

   # Rename SN to Name, for for generic tool
   data['Name'] = data['SN']*1
   db.close()
   if queue=='QWFCCD':
      data['ID'] = ["1{:02d}".format(i) for i in range(1,N+1)]
   elif queue=='QFIRE':
      data['ID'] = ["0{:02d}".format(i) for i in range(1,N+1)]
   else:
      data['ID'] = [str(i) for i in range(1,N+1)]
   data['Tags'] = ["Science" for i in range(1,N+1)]
   return data

@cache
def makeTimeRange(year, month, day, location='LCO', deltat=5*u.minute):
   '''Given a time, find the previous sunset, next sunrise and grid the
   time with N intervals.'''
   obs = Observer.at_site(location)
   dt = datetime.datetime(year, month, day, 3, 0, 0)   # 3AM UTC
   date = Time(dt, scale='utc')

   midnight = obs.midnight(date)
   sunset = obs.sun_set_time(midnight)   # do at midnight to avoid rise < set
   sunrise = obs.sun_rise_time(midnight)
   twilight_begin = obs.twilight_morning_astronomical(midnight)
   twilight_end = obs.twilight_evening_astronomical(midnight)
   times = [sunset]
   while times[-1] < sunrise:
      times.append(times[-1] + deltat)
   data = dict(sr=sunrise, ss=sunset, tb=twilight_begin, te=twilight_end,
               times=times)
   return data
   
def compute(data, date=None, location='LCO'):
   '''Take the data from target list and derive quantities needed for
   the dashboard.'''

   obs = Observer.at_site(location)
   if date is None:
      date = Time.now()
   else:
      date = Time(date)

   # Now some derived quantities
   c = SkyCoord(data['RA'], data['DE'], unit=(u.hourangle, u.degree))
   t = FixedTarget(c)
   aa = obs.altaz(date, t)
   data['HA'] = (t.ra.to('hourangle') - obs.local_sidereal_time(date)).\
                 to('hourangle').value
   data['alt'] = aa.alt.to('degree').value
   data['AM'] = airmass(aa.alt.to('degree').value)

   return ColumnDataSource(data=data)
