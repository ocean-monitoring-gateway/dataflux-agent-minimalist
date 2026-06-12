# -*- coding: utf-8 -*-
"""
Created on Mon Jul  4 11:28:08 2022

@author: mjulien
"""

#%%

import os
import csv
import json
import numpy as np
import pandas as pd
import datetime as dt
import struct
from cayennelpp import LppFrame, LppUtil
from datetime import datetime, timedelta


##################### fport : 'decoder function name' #############################################################################
def load_routing_table(csv_file_path):
    user_routing_table = {}
    
    # reading fport_routing_table.csv
    with open(csv_file_path, mode='r') as file:
        reader = csv.DictReader(file)
        
        # iterating over each row
        for row in reader:
            # using 'fport' as the key and 'decoder' as the value
            fport = int(row['fport']) 
            decoder = row['decoder']
            
            # populating the dictionary
            user_routing_table[fport] = decoder
            
    return user_routing_table

fport_routing_table_path = './fport_routing_table.csv'
user_routing_table = load_routing_table(fport_routing_table_path)
###################################################################################################################################

#%% section: class to manage paylod decoders
class PayloadDecoder:
    ######################################
    #
    ######################################
    
    def __init__(self, allowed_fport_range=[1,233]):
        self.allowed_fport_range = allowed_fport_range
        self.route_table_humanreadable = pd.read_csv(fport_routing_table_path)
        self.route_table = None
        self._set_default_config()
        
        # Add new payload decoder to table
        for def_fport in user_routing_table:
            self.update_route_table(def_fport, eval(user_routing_table[def_fport]))
            
    
    # --- callable methods
    def print_route_table(self,internal=False):
        print('--- Payload decoder: route table ---')
        if internal==True:
            print(self.route_table)
        else:
            print(self.route_table_humanreadable)
    
    def update_route_table(self,fport,decoder_func):
        self.route_table[fport] = decoder_func
        
    def get_decoder_func(self,fport):
        func = self.route_table[fport]
        return func
    
    # --- internal methods
    def _set_default_config(self):
        self.route_table = []
        for i in range(0,256):
            self.route_table.append(self._default_payload_decoder)
            
    def _default_payload_decoder(self,hexapayload):
        payload = {'hexval':hexapayload }
        return payload    

#%% section : Info on custom payload decoder

#########################################
### STEP1 (optional): Define data structure (ordered)
#
# --- variable 'bytes_struct':
# key = field name
# nbbyte = number of byte for the fiels
# type = struct type to unpack hex value
#
# --- exemple:
# bytes_struct = {0:{'key':'myval0', 'nbbyte':2, 'type':'>I'},
#                 1:{'key':'myval1', 'nbbyte':2, 'type':'>I'},
#                 ...
#                 N:{'key':'myvalN', 'nbbyte':2, 'type':'>I'}}
#
# --- possible types with struct.pack() struct.unpack():
# 1 bytes:  signed char='b', unsigned char='B' --> (integer in python)
# 2 bytes:  short='h', unsigned short='H'
# 4 bytes:  int='i', unsigned int='I', float='f'
# 8 bytes:  , string=char[]='s', 'double='d'
# X bytes:  , string=char[]='s', 'double='d
# optional: Add '<' (little) or '>' (big) to set endianess
#
# --- usage: to convert hex string 
# payload = parse_unpack_hexstring(hexstr,bytes_struct)
# payload is returned as a dict()
#############################################

#############################################
### STEP2 (mandatory): Define associated decoding function
#
# input = hexa string
# output = payload as 1-level dictionnary with float, int or string values
#############################################


#%% section : define custom decoder functions

#############################################
# generic payload decoder (template)
#############################################
def payload_decoder_generic(hexstr):
    print('Running payload decoder (generic) ...')
    bytes_struct = {0:{'key':'myval0', 'nbbyte':2, 'type':'>I'},
                    }
    payload = dict() 
    ## Decode payload according to data structure.
    ## Save field names and values in dict
    payload = parse_unpack_hexstring(hexstr,bytes_struct)
    return payload

#############################################
# cayenne LPP payload decoder (wrapper for pycayennelpp package)
#############################################
def payload_decoder_cayennelpp(hexstr):
    print('Running payload decoder (cayenne lpp) ...')
    payload = dict()
    # build cayenne lpp frame from hexstr
    frame = LppFrame().from_bytes(bytearray.fromhex(hexstr))
    print(frame)
    # dump frame in json format into payload variable
    frame = json.dumps(frame, default=LppUtil.json_encode_type_int)
    frame = json.loads(frame)
    print(frame)
    # convert back to dict
    ref_key = { 0:{'name':'digital_input','count':0},
                1:{'name':'digital_output','count':0},
                2:{'name':'analog_input','count':0},
                3:{'name':'analog_output','count':0},
                101:{'name':'lum_sensor','count':0},
                102:{'name':'pres_sensor','count':0},
                103:{'name':'temp_sensor','count':0},
                104:{'name':'humid_sensor','count':0},
                113:{'name':['acc_x','acc_y','acc_z'],'count':0},
                115:{'name':'baro_sensor','count':0},
                134:{'name':['gyro_x','gyro_y','gyro_z'],'count':0},
                136:{'name':['gps_lat','gps_lng','gps_alt'],'count':0},
               }
    for field in frame:
        # ref_key[field['type']]['count'] = ref_key[field['type']]['count'] +1
        suffix = '_' + '{:02d}'.format(field['channel'])
        if (field['type']==113) or (field['type']==134) or (field['type']==136): # Correspond to GPS data (divided in 3, lat/lng/alt)
            payload[ref_key[field['type']]['name'][0]+suffix] = field['value'][0]
            payload[ref_key[field['type']]['name'][1]+suffix] = field['value'][1]
            payload[ref_key[field['type']]['name'][2]+suffix] = field['value'][2]
        else:
            payload[ref_key[field['type']]['name']+suffix] = field['value'][0]
    return payload


#############################################
# turtle tag payload decoder (from IOT 1)
# version with minimal processing
#############################################
def payload_decoder_turtle_tag_minimal(hexstr):
    print('Running payload decoder (turtle_tag_minimal) ...')
    bytes_struct = {0:{'key':'version', 'nbbyte':2, 'type':'<H'},
                    1:{'key':'dive_id', 'nbbyte':2, 'type':'<H'},
                    2:{'key':'dive_histo', 'nbbyte':2*5, 'type':'s'},
                    3:{'key':'latitude', 'nbbyte':4, 'type':'<i'},
                    4:{'key':'longitude', 'nbbyte':4, 'type':'<i'},
                    5:{'key':'ehpe', 'nbbyte':4, 'type':'<I'},
                    6:{'key':'ttf', 'nbbyte':4, 'type':'<I'},
                    7:{'key':'surfacetime_s', 'nbbyte':4, 'type':'<I'},
                    8:{'key':'surfsensor_usetime', 'nbbyte':4, 'type':'<I'},
                    9:{'key':'gnss_usetime', 'nbbyte':2, 'type':'<H'},
                    10:{'key':'gnss_nofix', 'nbbyte':1, 'type':'<B'},
                    11:{'key':'gnss_timeoutzerosat', 'nbbyte':1, 'type':'<B'},
                    12:{'key':'gnss_nbsat', 'nbbyte':1, 'type':'<B'},
                    13:{'key':'gnss_nbsatpow', 'nbbyte':1, 'type':'<B'},
                    14:{'key':'dive_profile', 'nbbyte':20, 'type':'s'},
                    15:{'key':'temperature', 'nbbyte':2, 'type':'<H'},
                    16:{'key':'battery_mv', 'nbbyte':2, 'type':'<H'},
                    }
    payload = dict() 
    ## Decode payload according to data structure.
    ## Save field names and values in dict
    payload = parse_unpack_hexstring(hexstr,bytes_struct)
    return payload

#############################################
# turtle tag payload decoder (from IOT 1)
# version with dive profile processing
#############################################
def payload_decoder_turtle_tag(hexstr):
    print('Running payload decoder (turtle_tag) ...')
    bytes_struct = {0:{'key':'version', 'nbbyte':2, 'type':'<H'},
                    1:{'key':'dive_id', 'nbbyte':2, 'type':'<H'},
                    2:{'key':'dive_histo', 'nbbyte':2*5, 'type':'s'},
                    3:{'key':'latitude', 'nbbyte':4, 'type':'<i'},
                    4:{'key':'longitude', 'nbbyte':4, 'type':'<i'},
                    5:{'key':'ehpe', 'nbbyte':4, 'type':'<I'},
                    6:{'key':'ttf', 'nbbyte':4, 'type':'<I'},
                    7:{'key':'surfacetime_s', 'nbbyte':4, 'type':'<I'},
                    8:{'key':'surfsensor_usetime', 'nbbyte':4, 'type':'<I'},
                    9:{'key':'gnss_usetime', 'nbbyte':2, 'type':'<H'},
                    10:{'key':'gnss_nofix', 'nbbyte':1, 'type':'<B'},
                    11:{'key':'gnss_timeoutzerosat', 'nbbyte':1, 'type':'<B'},
                    12:{'key':'gnss_nbsat', 'nbbyte':1, 'type':'<B'},
                    13:{'key':'gnss_nbsatpow', 'nbbyte':1, 'type':'<B'},
                    14:{'key':'dive_profile', 'nbbyte':20, 'type':'s'},
                    15:{'key':'temperature', 'nbbyte':2, 'type':'<H'},
                    16:{'key':'battery_mv', 'nbbyte':2, 'type':'<H'},
                    }
    payload = dict() 

    ## Decode payload according to data structure.
    ## Save field names and values in dict
    payload = parse_unpack_hexstring(hexstr,bytes_struct)

    ## Adjuts units 
    payload['latitude'] = float(payload['latitude']/1e7)
    payload['longitude'] = float(payload['longitude']/1e7)
    payload['ehpe'] = float(payload['ehpe']/1e3)
    payload['temperature'] = float(payload['temperature']/1e2)

    ## Rebuild histo and dive profile
    # --> dive histo
    tab_size = 5
    cell_size = 4
    x = payload['dive_histo']
    data = list()
    # convert hex str in list of int16
    for i in range(0,tab_size):
        data.append(int(swapbytesHexstr(x[cell_size*i:cell_size*i+cell_size]),16))
    # serialize to chain with "process_dive_profiles()"
    payload['dive_histo'] = str(data).replace(',', '')
    
    # --> dive profile
    tab_size = 20
    cell_size = 2
    x = payload['dive_profile']
    data = list()
    # convert hex str in list of int16
    for i in range(0,tab_size):
        data.append(int(swapbytesHexstr(x[cell_size*i:cell_size*i+cell_size]),16))
    # serialize to chain with "process_dive_profiles()"
    payload['dive_profile'] = str(data).replace(',', '')

    ## Process true dive profile
    dftmp = pd.DataFrame(payload,index=[0])
    dftmp = process_dive_profiles(dftmp)
    payload = dftmp.to_dict('records')[0]

    return payload

#############################################
### Low-level function to convert hexadecimal string to decimal value
#############################################
def hex2dec(payload_string):
    dec = int(payload_string, 16)
    return dec

#############################################
## Low-level function to slice a string
#############################################
def slice_string(input_string, start_index, substring_length):
    # Checking if the start index is within the bounds of the string
    if start_index < 0 or start_index >= len(input_string):
        return "Invalid start index"

    # Using string slicing to get the substring
    substring = input_string[start_index:start_index + substring_length]
    return substring

#############################################
### Low-level function to parse hexa payload using hex2dec and slice_string
### according to 'payload_struct' passed
# input is an hexa string
# output is a 1-level dictionnary of int
#############################################
def parse_hexstring(hexstr, payload_struct):
    res = dict()
    for field in payload_struct:
        if payload_struct[field]['decode'] == 'y':
            buf = hex2dec(slice_string(hexstr, 0, payload_struct[field]['nbchars']))
        else:
            buf = slice_string(hexstr, 0, payload_struct[field]['nbchars'])
        res[payload_struct[field]['key']] = buf
        hexstr = hexstr[(payload_struct[field]['nbchars']):]
    return res

#############################################
### Low-level function to parse hexa payload
### according to 'bytes_struct ' passed (should not be deited)
#
# input is an hexa string
# output is a 1-level dictionnary of float, int, string , datetime (and ??)
#############################################
def parse_unpack_hexstring(hexstr,bytes_struct):
    res = dict() 
    for field in bytes_struct:
        # load first field values (N bytes = 2*N chars in hex string)
        buf = hexstr[0:(2*bytes_struct[field]['nbbyte'])]
        # pad with zero to have a 4 bytes representation. needed by struct.unpack()
        print(bytes_struct[field],buf)
        # while len(buf) < 8: # 
        #     buf = '0'+buf
        # unpack value according to field type
        if bytes_struct[field]['type'][-1] != 's':
            buf =  struct.unpack(bytes_struct[field]['type'], bytes.fromhex(buf))[0]
        else:
            buf = str(buf)
        res[bytes_struct[field]['key']] = buf
        # Remove field read before looping again
        hexstr = hexstr[(2*bytes_struct[field]['nbbyte']):]
    return res

#############################################
### Low-level function to swap byte in hex string
#############################################
def swapbytesHexstr(hexstr):
    sres = ''
    #s = '1A2B3C4D'
    s = hexstr
    nbbyte = int(len(s)/2) #2 hex digits per byte
    #print(nbbyte)
    for i in range(0,nbbyte+1):
        sres = s[2*i:2*i+2] + sres    
    return sres

#############################################
### Low-level function to process dive profile of turtle tag
#############################################
def find_nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return array[idx]
    
def process_dive_profiles(df,dynamic_profile_scale=False):
    if "dive_histo" in df.columns:
        # >>> Compute dive time
        print('Processing dive time ...')
        # calc of dive time from histo data (columns diveDeepHisto)
        # dive time is the sum of all duration in each depth range
        tdive = []
        for val in df.dive_histo:
            buf = [float(x) for x in val[1:-1].split(' ')]
            buf = np.sum(buf)
            tdive.append(buf)
        df['tdive_s'] = tdive

    # >>> Compute true dive profile and associated carac

    print('Processing true dive profile ...')
    # calc the time steps of the dive profile
    # see doc : IoT- Application Tag.odt on Seafile (https://seafile.lirmm.fr/smart-link/8e8b3de4-fd00-4dca-ba92-b2ce21e60a9e/)
    p_m = 120 # table size for averaging
    p_n = 20 # output table size
    p_ti = 15 # initial time step for encoding
    p_ds = 0.1 # depth step size in meter (fixed at 0.1 or equals to 1/dive_profile_scale if dynamic_profile_scale == True)
    p_dn = 256 # depth numebr of steps --> if step = 1dm and number of step = 255, max depth = 25.5m

    profile_tstep_s = []
    for tdive in df.tdive_s:
        tmeas = tdive/p_m
        arr = 15*np.array([1,2,4,8,16,32,64,128,256,512,1024])
        tmeas = find_nearest(arr,tmeas)
        realnbpt = tdive/tmeas
        decim_coeff = np.ceil(realnbpt/p_n)
        tstep = tmeas*decim_coeff
        profile_tstep_s.append(tstep)
    df['profile_tstep_s'] = profile_tstep_s

    # calc of max and mean dive depth from dive profile (columns profile)
    # compute new histo dive time from true dive profile
    # --> We know the true profile time step (=see above) and depth step (=0.1m, fixed in tag code)
    # --> "profile_histotime_s" is a table of 256 values, one for each 0.1m; containing time spend at this depth
    profile_histotime_s = []
    profile_histodepth_m = []
    profile_m = []
    maxdepth_m = []
    avgdepth_m = []
    for index, row in df.iterrows():
        # print(row)
        if dynamic_profile_scale == True:
            if row.dive_profile_scale != 0:
                p_ds = 1/row.dive_profile_scale
        histodepth = p_ds*np.arange(0,256,1)
        histotime = np.zeros(p_dn)
        dive_profile = [int(x) for x in row.dive_profile[1:-1].split(' ')]
        # print(buf)
        for val in dive_profile:
            histotime[val] = histotime[val] + row.profile_tstep_s
        histotime[0] = 0
        # print(buf)
        dive_profile = np.array(dive_profile)*p_ds
        maxdepth_m.append(np.max(dive_profile))
        if np.sum(dive_profile)==0:
            avgdepth_m.append(0.0)
        else:
            avgdepth_m.append(np.mean(dive_profile[dive_profile > 0]))
        profile_m.append(dive_profile)
        profile_histotime_s.append(histotime)
        profile_histodepth_m.append(histodepth)

    df['maxdepth_m'] = maxdepth_m
    df['avgdepth_m'] = avgdepth_m
    df['profile_m'] = str(profile_m[0].tolist()).replace(',', '')
    df['profile_histotime_s'] = str(profile_histotime_s[0].tolist()).replace(',', '')
    df['profile_histodepth_m'] = str(profile_histodepth_m[0].tolist()).replace(',', '')

    print('Done processing data set')
    
    return df

