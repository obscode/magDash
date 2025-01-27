'''Compute.py:  compute the astronomical data based on queued data'''
from functools import cache
from astroplan import Observer,FixedTarget
from astropy.time import Time
from astropy import units as u
from astropy.coordinates import SkyCoord
import datetime
import numpy as np
from zoneinfo import ZoneInfo

utc_tz = ZoneInfo("UTC")
loc_tz = ZoneInfo("America/Santiago")

def airmass(h):
   '''Compute airmass from Pickering (2002) given altitude angle h
   
   Args:
      h(float/array):  the altitude (degrees above horizon)
      
   Returns:
      airmass(float/array)
      
   Note:
      where altitude is < 0, it is set to arbitrarily 0 (am~38)'''

   nh = np.where(h > 0, h, 0.001)
   arg = nh + 244./(165. + 47.*np.power(nh, 1.1))
   return np.power(np.sin(arg*np.pi/180), -1) 

@cache
def makeTimeRange(year, month, day, location='LCO', deltat=5*u.minute):
   '''Given a time, find the previous sunset, next sunrise and grid the
   time with N intervals.
   
   Args:
      year (int):  year (YYYY)
      month (int):  month (MM)
      day (int):  day (DD)
      location(string):  observer's location (Observer.at_site())
      deltat (float*time unit):  the time interval between for time range
      
   Returns:
      dict:  'sr':  sunrise
             'ss':  sunset
             'tb':  twilight begins (end of night)
             'te':  twilight ends (beginning of night)
             'times': the time values
   '''
   obs = Observer.at_site(location)
   dt = datetime.datetime(year, month, day, 3, 0, 0)   # 3AM UTC
   date = Time(dt, scale='utc')

   midnight = obs.midnight(date)
   sunset = obs.sun_set_time(midnight)   # do at midnight to avoid rise < set
   sunrise = obs.sun_rise_time(midnight)
   twilight_begin = obs.twilight_morning_astronomical(midnight)
   twilight_end = obs.twilight_evening_astronomical(midnight)
   times = [sunset - 1*u.hour]
   while times[-1] < sunrise + 1*u.hour:
      times.append(times[-1] + deltat)
   data = dict(sr=sunrise, ss=sunset, tb=twilight_begin, te=twilight_end,
               times=times)
   return data

def computeNightQuantities(data, date=None, location='LCO', deltat=5*u.minute):
   '''Take the data from target list and derive quantities needed for
   the dashboard than span the night (ie., only need to compute once/night/list).
   
   Args:
      data(dict):  data for objects. Must have RA(hours) and DE(degrees)
                   at minimum
      date(misc):  the date of the observing night. Can be anything that
                   astropy.time.Time() understands. Default:  now
      location(string):  observer location (astropy.Observer.at_site)
      deltat(time unit):  time interval for timerange of HA, airmass, etc
   
   Returns:
      dict with keys:
            'alt':  altitude (decimal degrees) for all objects
            'az':  azimuth (decimal degrees) for all objects
            'AM':   Airmass for all objects
            'transit': Meridian transit time (astropy.time.Time)'''

   obs = Observer.at_site(location)
   if date is None:
      date = Time.now()
   else:
      date = Time(date)
   dt = date.datetime

   # Now some derived quantities
   c = SkyCoord(data['RA'], data['DE'], unit=(u.hourangle, u.degree))
   t = FixedTarget(c)
   res = makeTimeRange(dt.year, dt.month, dt.day, location, deltat)
   for key in res:
      data[key] = res[key]

   aa = obs.altaz(res['times'], t, grid_times_targets=True)
   data['alt'] = aa.alt.to('degree').value
   data['az'] = aa.az.to('degree').value
   data['AM'] = airmass(aa.alt.to('degree').value)
   data['transit'] = obs.target_meridian_transit_time(date, t)
   data['targets'] = t
   data['t0'] = res['times'][0].datetime
   data['t1'] = res['times'][-1].datetime

   return data

def computeCurrentQuantities(targets, date=None, location='LCO'):
   obs = Observer.at_site(location)
   if date is None:
      date = Time.now()
   else:
      date = Time(date)
   res = {}
   
   aa = obs.altaz(date, targets)
   res['alt'] = aa.alt.to('degree').value
   res['az'] = aa.az.to('degree').value
   res['AM'] = airmass(aa.alt.to('degree').value)
   res['HA'] = (targets.ra - obs.local_sidereal_time(date)).to('hourangle').value
   dt = date.datetime.replace(tzinfo=utc_tz)
   dt2 = dt.astimezone(loc_tz)
   res['UT'] = dt.strftime("%H:%M:%S")
   res['LT'] = dt2.strftime("%H:%M:%S")
   res['ST'] = obs.local_sidereal_time(date).to_string(precision=0, sep=':')
   res['now'] = date
   return(res)
