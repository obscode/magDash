'''Compute.py:  compute the astronomical data based on queued data'''
from functools import cache
from astroplan import Observer,FixedTarget,moon_illumination
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

def makeTimeRange(date, location='LCO', deltat=5*u.minute):
   '''Given a time, find the previous sunset, next sunrise and grid the
   time with N intervals.
   
   Args:
      date (astropy.Time):  Current UTC time
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
   #dt = date.datetime
   #dt = datetime.datetime(dt.year, dt.month, dt.day, 3, 0, 0)   # 3AM UTC
   #date = Time(dt, scale='utc')

   # Logic here is to check for previous sunset and next sunrise (assume that
   #  we're currently observing at night. But if not, the previous sunset may
   #  be in the past (the day before), so check for that
   sunset = obs.sun_set_time(date, which="previous")  
   sunrise = obs.sun_rise_time(date, which="next")
   if sunrise.jd - sunset.jd > 1:
      # we're at daytime, so we want next sunset
      sunset = obs.sun_set_time(date, which="next")
   twilight_end = obs.twilight_evening_astronomical(sunset, which="next")
   twilight_begin = obs.twilight_morning_astronomical(twilight_end, 
           which="next")
   sunrise = obs.sun_rise_time(twilight_begin, which="next")
   times = [sunset - 1*u.hour]
   while times[-1] < sunrise + 1*u.hour:
      times.append(times[-1] + deltat)
   data = dict(sr=sunrise, ss=sunset, tb=twilight_begin, te=twilight_end,
               times=times)
   #print(data)
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
   res = makeTimeRange(date, location, deltat)
   for key in res:
      data[key] = res[key]

   aa = obs.altaz(res['times'], t, grid_times_targets=True)
   data['alts'] = aa.alt.to('degree').value
   data['az'] = aa.az.to('degree').value
   data['AM'] = airmass(aa.alt.to('degree').value)
   data['transit'] = obs.target_meridian_transit_time(date, t)
   data['targets'] = t
   data['t0'] = res['times'][0].datetime
   data['t1'] = res['times'][-1].datetime

   return data

def computeTimes(date=None, location='LCO'):
   " compute the current times (local, sidereal, utc)"
   obs = Observer.at_site(location)
   if date is None:
      date = Time.now()
   else:
      date = Time(date)
   dt = date.datetime.replace(tzinfo=utc_tz)
   dt2 = dt.astimezone(loc_tz)
   UT = dt.strftime("%H:%M:%S")
   LT = dt2.strftime("%H:%M:%S")
   ST = obs.local_sidereal_time(date).to_string(precision=0, sep=':')
   return(UT,LT,ST)


def computeCurrentQuantities(targets, date=None, location='LCO'):
   if date is None:
      date = Time.now()
   else:
      date = Time(date)
   obs = Observer.at_site(location)
   res = {}
   
   aa = obs.altaz(date, targets)
   res['alt'] = aa.alt.to('degree').value
   res['az'] = aa.az.to('degree').value
   res['zang'] = 90 - res['alt']  # zenith angle
   res['AM'] = airmass(aa.alt.to('degree').value)
   res['HA'] = (targets.ra - obs.local_sidereal_time(date)).to('hourangle').value
   UT,LT,ST = computeTimes(date, location)
   res['UT'] = UT
   res['LT'] = LT
   res['ST'] = ST
   res['now'] = date
   return(res)

def LSTtoStr(lst):
    hour = int(lst.hour)
    minute = int((lst.hour-hour)*60)
    sec = int((lst.hour-hour-minute/60)*60)
    return "{:02d}:{:02d}:{:02d}".format(hour,minute,sec)


def computeNightParams(date=None, location='LCO'):
   if date is None:
      date = Time.now()
   else:
      date = Time(date)
   obs = Observer.at_site(location)

   data = dict(
           label=['Sunset','Twilight end','Mid point','Twilight begin',
                  'Sunrise', 'LST @ Sunset','LST @ Mid point', 'LST @ Sunrise',
                  'Night Duration', 'Moon Phase'])
   times = makeTimeRange(date, location)
   mid = (times['te'].jd + times['tb'].jd)/2
   mid = Time(mid, format='jd')
   moon = moon_illumination(mid)
   duration = (times['sr'].jd-times['ss'].jd)*24
   lstset = obs.local_sidereal_time(times['ss'])
   lstmid = obs.local_sidereal_time(mid)
   lstrise = obs.local_sidereal_time(times['sr'])
   tformat = "%H:%M:%S"
   data['value'] = [times['ss'].strftime(tformat),
                    times['te'].strftime(tformat),
                    mid.strftime(tformat),
                    times['tb'].strftime(tformat),
                    times['sr'].strftime(tformat),
                    #lstset.strftime(tformat),
                    #lstmid.strftime(tformat),
                    #lstrise.strftime(tformat),
                    LSTtoStr(lstset),LSTtoStr(lstmid),LSTtoStr(lstrise),
                    "{:.1f} hours".format(duration),
                    "{:.1f} %".format(moon*100)]
   return data

