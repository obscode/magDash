'''Query functions to get data:
  - SQL queries form CSP/POISE databases
  - Image query of LCO sky
  - HTML queris form sam.lco.cl for telescope info
    (requires VPN)
'''

import pymysql
from bokeh.models import ColumnDataSource
from astropy.coordinates import SkyCoord
from astropy import units as u
from astroplan import Observer, FixedTarget
from astropy.time import Time
import numpy as np
from OptStandards import addStandards
from functools import cache
import datetime
import os
import requests
from bs4 import BeautifulSoup
import re

from PIL import Image

HOST='csp-nas.lco.cl'
USER='csp'
PASS='Hnot=75.0!'
if 'CSPpasswd' in os.environ:
   PASS = os.environ['CSPpasswd']

DB='Phot'

target_pat = re.compile(r'target:"([^"]+)"')

def airmass(h):
   '''Computer airmass from Pickering (2002) given altitude angle h'''
   nh = np.where(h > 0, h, 0.001)
   arg = nh + 244./(165. + 47.*np.power(nh, 1.1))
   return np.power(np.sin(arg*np.pi/180), -1) 

Q_query = '''
select t0.*,t2.mag,t2.night,t2.jd,t4.UT
  from SNList t0 left join (
    select t1.field as field,t1.night as night,t1.mag as mag, t1.jd as jd
    from (
      select field,night,mag,jd,ROW_NUMBER() OVER (PARTITION BY field 
         ORDER BY jd DESC) as rank from MAGSN where filt="r" and obj<1) as t1
      WHERE t1.rank=1 ) t2 
      ON (t0.SN=t2.field or t0.NAME_CSP=t2.field or t0.NAME_IAU=t2.field or 
        t0.NAME_PSN=t2.field) left join (
          select t3.SN as field,max(t3.UT) as UT
          from (
             select * from obs_log where MD="{}"
          ) as t3 group by field
        ) t4 on (t2.field=t4.field)
WHERE {} = "1" {} ORDER BY RA'''

priority_query = '''
select text from comments 
where sn_id=%s and type="priority" 
order by time desc limit 1'''

cad_query = '''
SELECT UT FROM obs_log WHERE SN=%s and MD=%s
ORDER BY UT DESC LIMIT 1'''


Q_names = ['SNID','SN','type','RA','DE','zc','zcmb','zvrb','dmag','host',
   'offew','offns','gtype','comm','survey','active','camp','agerdate',
   'datemeans','name_iau','name_psn','guider','nstd','qswo','qfire','qrc',
   'qwfccd','name_csp','qc0','inot','qalfosc','qnotcam','qlcogt','qfsu',
   'qlmc','mag','night','jd','utobs']

CAMPS = ['2004/2005','2005/2006','2006/2007','2007/2008','2008/2009',
         '2011/2012','2012/2013','2013/2014','2014/2015','2015/2016',
         '2016/2017','2017/2018','2018/2019','2019/2020']

# obs_log entries for each queue
OBS_Names = {'QSWO':"Opt",
             'QWFCCD':"Spe",
             'QFIRE':"Isp"}
WHERES = {"QSWO":'and ACTIVE = "1" ',
          "QWFCCD":'',
          "QFIRE":''}

def camp_str(camp):
   '''Convert campaign integer into campaign string'''
   idx = camp-1   # database counts from 1
   if idx > len(CAMPS)-1:
      year = 2014+idx//2
      semester = ["A","B"][idx%2]
      return "{:d}{:s}".format(year,semester)
   else:
      return CAMPS[idx]


def qData(queue='QSWO'):
   db = pymysql.connect(host=HOST, user=USER, passwd=PASS, db=DB)
   c = db.cursor()
   #print(Q_query.format(OBS_Names[queue],queue,WHERES[queue]))
   N = c.execute(Q_query.format(OBS_Names[queue],queue,WHERES[queue]))
   rows = c.fetchall()
   data = {}.fromkeys(Q_names)
   for i,name in enumerate(Q_names):
      data[name] = [row[i] for row in rows]

   # Rename SN to Name, for for generic tool
   data['Name'] = data['SN']*1
   if queue=='QWFCCD':
      data['ID'] = ["1{:02d}".format(i) for i in range(1,N+1)]
   elif queue=='QFIRE':
      data['ID'] = ["0{:02d}".format(i) for i in range(1,N+1)]
   else:
      data['ID'] = [str(i) for i in range(1,N+1)]
   data['comm'] = [typ if typ else "unknown" for typ in data['type']]
   # Convert to strings
   data['camp'] = [camp_str(camp) for camp in data['camp']]

   priorities = []
   jdcads = []
   mags = []
   for SN in data['SNID']:
      NN = c.execute(priority_query, (SN,))
      if NN == 1:
         priorities.append(c.fetchone()[0])
      else:
         priorities.append("Unknown")
   data['priority'] = priorities
   for name in data['SN']: 
      MD = 'Opt'
      if queue=='QWFCCD': MD='Spe'
      if queue=='FIRE': MD='Isp'
      NN = c.execute(cad_query, (name,MD))
      if NN == 1:
         ut = c.fetchone()[0]
         jd = Time(ut).jd
         jdcads.append(jd)
      else:
         jdcads.append(-1)
   data['jdcad'] = jdcads

   if queue=='QWFCCD' or queue=='QSWO':
      addStandards(data, queue)
   # Handle cases where not observed yet or is a standard
   data['utobs'] = [ut if ut else '2000-01-01' for ut in data['utobs']]
   db.close()
   data['N'] = N

   return data

def getLCOsky(format='bokeh'):
   '''Retrieve the LCO all-sky image and return as image arrays
      formats:  'bokeh' for inclusion in Bokeh plots
                'numpy' for NxNx4 np arrays'''
   im = Image.open(requests.get('https://weather.lco.cl/casca/latestred.png', 
                                stream=True).raw)
   arr = np.array(im.getdata()).reshape(im.size[0],im.size[1],4)
   if format=='numpy':  return arr

   # Boheh weird RGBA format
   img = np.empty((im.size[0],im.size[1]), dtype=np.uint32)
   view = img.view(dtype=np.uint8).reshape((im.size[0],im.size[1],4))
   view[:,:,0] = arr[::-1,::,0]
   view[:,:,1] = arr[::-1,::,1]
   view[:,:,2] = arr[::-1,::,2]
   view[:,:,3] = arr[::-1,::,3]
   return img

def getMagPointing(tel='BAADE'):
   '''If sam.lco.cl is available, get the current poining of BAADE or CLAY'''
   try:
      page = requests.get('http://sam.lco.cl/TOPS/pointing/pointing.php?magtel=CLAY')
   except:
      # Failed to connect, so likely sam.lco.cl is not accessible
      return None,None
   soup = BeautifulSoup(page.content, features='html.parser')
   scripts = soup.find_all('script')
   s = scripts[-1]
   res = target_pat.search(s.contents[0])
   if res is None: return None,None
   return(res.group(1).split())
