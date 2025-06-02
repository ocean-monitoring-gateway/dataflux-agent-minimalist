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
import datetime as dt
import requests

import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

#%% declare influxdbcloud info

influx_org = "org.name@email.com"
influx_url = "https://eu-central-1-1.aws.cloud2.influxdata.com"

authbuckets_file = './influxdb_authbuckets.json'
with open(authbuckets_file) as json_file:
    token_dict = json.load(json_file)

#%% section: influxdb api manger

class InfluxdbManager:
    ######################################
    #
    ######################################
    
    def __init__(self):
        self.org = influx_org
        self.url = influx_url
        self.bucket = None
        self.token = None
        self.measurement = None
        self.client = None
        self.point = None
    
    # --- callable methods
    
    def write_data_container_to_client_bucket(self,data):
        
        if (data.client_influx_bucket!=None)and(data.client_influx_meas!=None):
            print('writing data from container to client bucket')        
            self.bucket      = data.client_influx_bucket
            self.token       = token_dict[self.bucket]
            self.measurement = data.client_influx_meas
            ## Connection to bucket
            self._connect_to_bucket()
            ## build influxdb entry using API
            p = influxdb_client.Point(self.measurement)        
            p.tag('client_id',data.client_id)        
            p.tag('deveui',data.msg['deveui'])        
            p.tag('name',data.msg['devid'])    
            for item in data.msg:
                p.field(item,data.msg[item])
            self.point = p
            ## write current point
            self._write_current_point()
            self._close_client()
        else:
            print('[error] client bucket info not initialized in data container. Not send ...')
        
    def write_data_container_to_device_bucket(self,data):
        
        if (data.influx_bucket!=None)and(data.influx_meas!=None):
            print('writing data from container to device bucket')        
            self.bucket      = data.influx_bucket
            self.token       = token_dict[self.bucket]
            self.measurement = data.influx_meas
            ## Connection to bucket
            self._connect_to_bucket()
            ## build influxdb entry using API
            p = influxdb_client.Point(self.measurement)      
            p.tag('client_id',data.client_id)        
            p.tag('deveui',data.msg['deveui'])        
            p.tag('name',data.msg['devid'])    
            for item in data.msg:
                p.field(item,data.msg[item])
            self.point = p
            ## write current point
            self._write_current_point()
            self._close_client()
        else:
            print('[error] client bucket info not initialized in data container. Not send ...')
    
    def write_dict_to_bucket(self,mybucket,mymeasurement,mytagdict,mydatadict):
        print('writing dict to bucket')        
        self.bucket      = mybucket
        self.token       = token_dict[self.bucket]
        self.measurement = mymeasurement
        ## Connection to bucket
        self._connect_to_bucket()
        ## build influxdb entry using API
        p = influxdb_client.Point(self.measurement)    
        for item in mytagdict:
            p.tag(item,mytagdict[item])      
        for item in mydatadict:
            p.field(item,mydatadict[item])
        self.point = p
        ## write current point
        self._write_current_point()
        self._close_client()
    
    # --- internal methods
    
    def _connect_to_bucket(self):
        print('connecting to influxdb bucket')
        # Conect to influxdb instance
        self.client = influxdb_client.InfluxDBClient(url = self.url, 
                                                     org = self.org,
                                                     token = self.token,
                                                     debug=True) # --- internal methods
    def _close_client(self):
        print('Closing influxdb client')
        # Conect to influxdb instance
        self.client.close()
            
    def _write_current_point(self):
        print('--- current influxdb point ---')
        print(self.point)
        # write entry to influx db bucket
        write_api = self.client.write_api(write_options=SYNCHRONOUS)
        write_api.write(self.bucket, self.org, self.point)
        print('--------------------')
        print('writing current point done ...')


    def _query_data(self,measurement,bucket,fluxrequest):
               
        self.bucket      = bucket
        self.token       = token_dict[self.bucket]
        self.measurement = measurement
        ## Connection to bucket
        self._connect_to_bucket()
        ## build query and run query
        query_api = self.client.query_api()
        # df = query_api.query_data_frame(fluxrequest)
        tables = query_api.query(fluxrequest)
        buf=[]
        for table in tables:
            for record in table.records:
                buf.append(record.values)
        # df = pd.DataFrame.from_dict(buf, orient='columns')
        # print(df)
        return buf