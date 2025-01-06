'''Optical Standards for use with IMACS'''

from astropy.coordinates import SkyCoord
from astropy import units as u
from datetime import date
import numpy as np

raw = [
("201","LTTT377","00:41:46.6","-33:39:10"),
("202","LTT1020","01:54:49.7","-27:28:29"),
("203","EG21","03:10:30.4","-68:36:05"),
("204","LTT1788","03:48:22.2","-39:08:35"),
("205","LTT2415","05:56:24.2","-27:51:26"),
("206","Hilt600","06:45:13.5","+02:08:15"),
("207","L745-46A","07:40:20.9","-17:24:42"),
("208","LTT3218","08:41:33.6","-32:56:55"),
("209","LTT3864","10:32:13.8","-35:37:42"),
("210","LTT4364","11:45:50.0","-64:50:30"),
("211","Feige56","12:06:39.7","+11:40:39"),
("212","LTT4816","12:38:50.7","-49:47:58"),
("213","CD-32","14:11:46.3","-33:03:15"),
("214","LTT6248","15:38:59.8","-28:35:34"),
("215","EG274","16:23:33.7","-39:13:48"),
("216","LTT7379","18:36:26.2","-44:18:37"),
("217","LTT7987","20:10:57.1","-30:13:03"),
("218","LTT9239","22:52:40.9","-20:35:27"),
("219","Feige110","23:19:58.3","-05:09:56"),
("220","LTT9491","23:19:35.2","-17:05:28")]

def addStandards(data):
   '''Add standards to the data dictionary'''
   for (id,name,ra,dec) in raw:
      coord = SkyCoord(ra,dec, unit=(u.hourangle, u.degree))
      RA = coord.ra.to('hourangle').value
      DE = coord.dec.to('degree').value
      idx = np.searchsorted(data['RA'], RA)

      for key in data:
         if key == 'RA':
            data[key].insert(idx, RA)
         elif key == 'DEC':
            data[key].insert(idx, DE)
         elif key == 'ID':
            data[key].insert(idx,id)
         elif key == "Name":
            data[key].insert(idx, name)
         elif key == "comm":
            data[key].insert(idx,"Standard")
         else:
            if data[key][-1] is None:
               data[key].insert(idx, None)
            elif isinstance(data[key][-1], date):
               data[key].insert(idx,date(2024,1,1))
            else:
               data[key].insert(idx,data[key][-1]*0)


