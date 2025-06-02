# -*- coding: utf-8 -*-
"""
Created on Wed Jul  6 21:40:50 2022

@author: mjulien
"""

import os
import platform
import socket
import csv
import json
import numpy as np
import datetime as dt
import time
import base64
import paho.mqtt.client as mqtt
from threading import Thread, Lock
import queue
import logging

from .lib_client import *
from .lib_decoder import *
from .lib_influxdb import *

#%%

supported_client_protocol = ['mqtt','http','ssh','debug','manual']
mutex = Lock()

class MainApp:
    ######################################
    #
    ######################################
    
    def __init__(self, nwkinfo):
        self.nwkinfo = nwkinfo
        self.client_protocol = self.nwkinfo['protocol']
        self.client = None
        self.queue = queue.Queue()
        self.msgcounter = {'raw_msg':0,'client_bucket_msg':0,'device_bucket_msg':0}
        # self.mutex = Lock()
        self.delay_process_loop = 5 #sec
        self.delay_status_msg = 30 #sec
        self.process_thread = Thread(target = self._ThreadProcessData, args = (self.queue,))
        
        if self.client_protocol not in supported_client_protocol:
            self.client_protocol = None
            print('[error] Unsupported client protocol. Starting default client thread')
            self.client_thread = Thread(target=self._ThreadDefaultClient, args = (self.queue,))
        else:
            print('[info] Used protocol:',self.client_protocol )
            if   self.client_protocol == 'mqtt':
                self.client_thread = Thread(target=self._ThreadMqttClient, args = (self.queue,))
            elif self.client_protocol == 'http':    
                self.client_thread = Thread(target=self._ThreadDefaultClient, args = (self.queue,))
            elif self.client_protocol == 'ssh':   
                self.client_thread = Thread(target=self._ThreadDefaultClient, args = (self.queue,))
            elif self.client_protocol == 'debug':   
                self.client_thread = Thread(target=self._ThreadDummyClient, args = (self.queue,))
            else:
                self.client_thread = Thread(target=self._ThreadDefaultClient, args = (self.queue,))
    
    #--- Callable methods -----------------------------------------------------  
    
    def run_app(self):
        ## start main threads
        self.client_thread.start()
        self.process_thread.start()
        self.client_thread.join()
        self.process_thread.join()
        
    def run_process_thread(self):
        ## start main thread
        self.process_thread.start()
        self.process_thread.join()
        
    def set_processloop_delay(self, delay_sec=5):
        self.delay_process_loop = delay_sec
        
    #--- Internal methods -----------------------------------------------------
        
    def _ThreadDefaultClient(self,queue):
        #######################
        # Run Default client
        #######################
        print('Starting thread : ThreadDefaultClient')
        print('[warning] Default client thread loaded. Doing nothing ...')
        print('Ending thread : ThreadDefaultClient')
    
    def _ThreadDummyClient(self,queue):
        #######################
        # Run Dummy client
        #######################
        print('Starting thread : ThreadDummyClient')
        
        ## build new Dummy client
        self.client = DummyClient(self.nwkinfo['server'], self.nwkinfo['port'], self.nwkinfo['apikey'], 
                                  self.nwkinfo['username'], topic=self.nwkinfo['topic'],
                                  client_id=self.nwkinfo['client_id'], nwk_type=self.nwkinfo['nwk_type'])
        
        print('Ending thread : ThreadDummyClient')
            
    def _ThreadMqttClient(self,queue):
        #######################
        # Run MQTT client
        #######################
        print('Starting thread : ThreadMqttClient')
        
        # Define on message actions --> store new message in databuf as dict()
        def on_message_mqtt_client(client, userdata, msg):
            #######################
            # Callback for when a PUBLISH message is received
            #######################
            print(client.client_id,': new message on topic', msg.topic)
            print('[debug] content of msg.paylod at on_message callback:')
            print(type(msg.payload))
            print(msg.payload)
            # add new msg to global fifo
            try:
                # self.databuf.append(json.loads(msg.payload))
                # print('global buffer size:',len(self.databuf))
                self.queue.put(json.loads(msg.payload))
                print('global buffer size:',self.queue.qsize())
            except Exception as Argument:
                logging.exception('[error] Can not add new msg to queue on MQTT client on_message callback ')
                
        # build new MQTT client for TTN
        self.client = MqttClient(self.nwkinfo['server'], self.nwkinfo['port'], self.nwkinfo['apikey'], 
                                 self.nwkinfo['username'], topic=self.nwkinfo['topic'],
                                 client_id=self.nwkinfo['client_id'], nwk_type=self.nwkinfo['nwk_type'],
                                 clean_session=True, use_tls=self.nwkinfo['use_tls'],
                                 protocol=mqtt.MQTTv31)
        # define on message callback
        self.client.on_message = on_message_mqtt_client
        print('Starting client: ',self.client.client_id, "--> connected:",self.client.is_connected())
        # Start and run client forever ("loop_forever" func handles reconnect try)
        self.client.connect()
        self.client.loop_forever()

            
    def _ThreadProcessData(self,queue):
        #######################
        # Read global fifo, format data and store on influxdb
        # --> not done yet
        #####################
        
        print('Starting thread : ThreadProcessData')

        # declare managers for payload decoders and influxdb API
        decoder_manager  = PayloadDecoder()
        influxdb_manager = InfluxdbManager()
        
        # -----------------------------------------------------------------
        # Send status message : "STARTING"
        # -----------------------------------------------------------------
        time.sleep(2)
        mytag = {'status':'STARTING',
                 'client_id':self.nwkinfo['client_id'],
                 'nwk_type':self.nwkinfo['nwk_type'],
                 'protocol':self.nwkinfo['protocol'],
                 'hostname':socket.gethostname(),
                 'hostversion':platform.platform(),
                 }
        mydict = self.msgcounter
        try:
            influxdb_manager.write_dict_to_bucket(self.nwkinfo['influx_bucket'], 'status',mytag, mydict)
        except Exception as Argument:
            logging.exception('[exec error] Not writing status msg on influxdb (try block)')
        # -----------------------------------------------------------------
        
        # -----------------------------------------------------------------
        # Send routing table in dedicated bucket
        # -----------------------------------------------------------------
        time.sleep(2)
        mytag = {'client_id':self.nwkinfo['client_id'],
                 'nwk_type':self.nwkinfo['nwk_type'],
                 }
        data = decoder_manager.route_table_humanreadable
        data = data.set_index('fport')
        data = data.to_dict(orient='index')
        mydict = {'routing_table_json':str(data)}
        try:
            influxdb_manager.write_dict_to_bucket(self.nwkinfo['influx_bucket'], 'routing-rules',mytag, mydict)
        except Exception as Argument:
            logging.exception('[exec error] Not writing current routing table on influxdb (try block)')
        # -----------------------------------------------------------------

        # Infinite loop to continously deal with new incomming data (in databuf)  
        # Process all message in the global buffer at once 
        # and then sleep before looping again.
        tic = time.time()
        toc = tic
        while True:
            print('Going to sleep for',self.delay_process_loop,'seconds ...')
            time.sleep(self.delay_process_loop)
            
            # -----------------------------------------------------------------
            # Send status message periodically
            # -----------------------------------------------------------------
            toc = time.time()
            if toc-tic > self.delay_status_msg:
                print('Sending status message to client bucket')
                tic = toc
                mytag = {'status':'ON',
                         'client_id':self.nwkinfo['client_id'],
                         'nwk_type':self.nwkinfo['nwk_type'],
                         'protocol':self.nwkinfo['protocol'],
                         'hostname':socket.gethostname(),
                         'hostversion':platform.platform(),
                         }
                mydict = self.msgcounter
                try:
                    influxdb_manager.write_dict_to_bucket(self.nwkinfo['influx_bucket'], 'status',mytag, mydict)
                except Exception as Argument:
                    logging.exception('[exec error] Not writing status msg on influxdb (try block)')
            # -----------------------------------------------------------------
                    
            # Process while buffer not empty
            # while(len(self.databuf) > 0):
            while(self.queue.qsize() > 0):
                ##################################
                ### Main sequence:
                # format and send data to influxdb
                ##################################
                time.sleep(0.1)
                ###################################
                ### STEP1:
                # - build data container from current raw msg
                # - check if rawmsg is valid
                # - Process raw entry to defined msg structure (save local copy)
                # - Write to influxdb (client bucket)
                ###################################
                # print('[exec info] Locking mutex')
                # global mutex
                # mutex.acquire()
                # self.mutex.acquire()
                msgbuf=None
                try:
                    msgbuf=self.queue.get()
                except Exception as Argument:
                    logging.exception('[exec error] Cannot load FIFO data, ressource locked. will retry (try block)')
                    
                
                texec = dt.datetime.now()
                if msgbuf != None:
                    try:
                        data = DataContainer(rawmsg=msgbuf, #self.databuf[0],
                                             client_id=self.nwkinfo['client_id'], nwk_type=self.nwkinfo['nwk_type']) 
                        
                        print('Processing new messages ...')
                        self.msgcounter['raw_msg'] = self.msgcounter['raw_msg']  + 1
                    
                        if data.is_rawmsg_valid() == True:
                            data.format_raw_msg()
                            data.print_msg()
                            data.update_client_bucket_info(self.nwkinfo['influx_bucket'], self.nwkinfo['influx_meas'])
                            data.print_info()
                            influxdb_manager.write_data_container_to_client_bucket(data)
                            self.msgcounter['client_bucket_msg'] = self.msgcounter['client_bucket_msg']  + 1
                        ###################################
                        ### STEP2:
                        # - Check if fport valid and payload not empty
                        # - Select which payload decoder to use according to fport
                        # - Decode hexa paylaod and add new fields to data
                        # - Write to influxdb (device bucket)
                        ###################################         
                            if (data.is_fport_valid()) == True:
                                msg_fport = data.get_msg_fport()
                                data.update_decoder_func(decoder_manager.get_decoder_func(msg_fport))
                                data.decode_hexapayload()
                                data.print_msg()
                                data.update_device_bucket_info()
                                data.print_info()
                                influxdb_manager.write_data_container_to_device_bucket(data)
                                self.msgcounter['device_bucket_msg'] = self.msgcounter['device_bucket_msg']  + 1
                            else:
                                print('[warning] Wrong fport. Can not select payload decoder or device bucket ...')
                                print(data.is_fport_valid(),data.is_payload_valid())
                                print('[warning] Message will not be written in device buckets ...')
                        else:
                            print('[error] Can not read raw message from client. Discarding current data...')
        
                        ###################################
                        ### STEP3:
                        ###################################
                                
                        ##################################
                    except Exception as Argument:
                        logging.exception('[exec error] Error during message processing')
                
                texec = dt.datetime.now() - texec
                print('gobal buffer size:',self.queue.qsize())
                print('Done ... process took', texec)

                
                
    def print_console_header(self):
        print("""
██████╗  █████╗ ████████╗ █████╗ ███████╗██╗     ██╗   ██╗██╗  ██╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔════╝██║     ██║   ██║╚██╗██╔╝
██║  ██║███████║   ██║   ███████║█████╗  ██║     ██║   ██║ ╚███╔╝ 
██║  ██║██╔══██║   ██║   ██╔══██║██╔══╝  ██║     ██║   ██║ ██╔██╗ 
██████╔╝██║  ██║   ██║   ██║  ██║██║     ███████╗╚██████╔╝██╔╝ ██╗
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝
        """)