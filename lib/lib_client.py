# -*- coding: utf-8 -*-
"""
Created on Mon Jul  4 11:28:08 2022

@author: mjulien
"""

import os
import csv
import json
import numpy as np
import datetime as dt
import base64
import paho.mqtt.client as mqtt
import re
import ssl

#%% section : define globals

# Supported network type
supported_network = ['ttn','orange','chirpstack','generic']

# Path to fport routing table
fport_routing_table_path = './fport_routing_table.csv'


#%% section: custom class for data manipulation

def init_formatted_dict():
    ############################################
    # Fields in this dict are mandatory fields defined
    # the dedicated IOT project documentation
    ############################################
    msg = {'devid':''       ,'deveui':''   ,'devadd':''  ,'appid':'',
           'fcnt':0         ,'fport':0     ,'gwid':''    ,'gweui':'',
           'timestamp':''   ,'rssi':0.0    ,'snr':0.0    ,
           'gwlat':0.0      ,'gwlng':0.0   ,'frmpayload':'','payload':''}
    return msg

def force_type_formatted_dict(msg):
    ############################################
    # Force type in pre-formatted message
    # --> data have to be be type DataContainer
    ############################################
    print('[info] Casting entries to predifined types')
    msg['fcnt']  = 0.0 if msg['fcnt']=='' else int(msg['fcnt'])
    msg['fport'] = 0.0 if msg['fport']=='' else int(msg['fport'])
    msg['rssi']  = 0.0 if msg['rssi']=='' else float(msg['rssi'])
    msg['snr']   = 0.0 if msg['snr']=='' else float(msg['snr'])
    msg['gwlat'] = 0.0 if msg['gwlat']=='' else float(msg['gwlat'])
    msg['gwlng'] = 0.0 if msg['gwlng']=='' else float(msg['gwlng'])
    return msg

class DataContainer:
    ######################################
    # Data Container object to uniform and ease 
    # data formatting and maniupulation
    ######################################
    
    def __init__(self, rawmsg, client_id, nwk_type, bypass_decoder=False):        
        
        ## Check if raw message have the rigth type. Have convert or generate error
        # --> Raw message have to be saved as dict
        self.rawmsg_valid = False
        if type(rawmsg) == dict:
            self.rawmsg_valid = True
        else:
            print('[error] Initialisation of data container failed. Raw msg is not of correct type')
        
        ## Initialize container
        self.rawmsg = rawmsg
        # Initialise final dict structure
        self.msg = init_formatted_dict()
        ## def general params
        self.client_id = client_id
        self.nwk_type = nwk_type
        ## def variables used in flow toward client bucket
        self.client_influx_bucket = None
        self.client_influx_meas = None
        ## def variables used in flow toward device bucket
        self.is_uplink = False
        self.bypass_decoder = bypass_decoder
        self.influx_bucket = None
        self.influx_meas = None
        self.fport_table = None
        ## load routing table at init
        self._load_fport_routing_table(fport_routing_table_path)
        
        ## def methods callbacks for payload decoder
        # depends on device (fport). will be auto filled
        self.payload_decoder = self._default_payload_decoder
        
        ## def methods callbacks for uplink formatter 
        # depends on network. filled at init below
        # --- for TTNv3
        if self.nwk_type == 'ttn':
            self.uplink_formatter = ttn_uplink_formatter
        # --- for Orange Live Object
        elif self.nwk_type == 'orange':
            self.uplink_formatter = orange_uplink_formatter
        # --- for Orange Live Object
        elif self.nwk_type == 'chirpstack':
            self.uplink_formatter = chirpstack_uplink_formatter
        # --- for generic source
        elif self.nwk_type == 'generic':
            self.uplink_formatter = generic_uplink_formatter
        else:
            self.uplink_formatter = self._default_uplink_formatter # does nothing
             
         
    # --- callable methods ----------------------------------------------------
    
    def print_info(self):
        print('--- Container info ---')
        print('client_influx_bucket',self.client_influx_bucket)
        print('client_influx_meas',self.client_influx_meas)
        print('influx_bucket',self.influx_bucket)
        print('influx_meas',self.influx_meas)
        print('--------------------------')
    
    def print_raw_msg(self):
        print('--- Stored raw message ---')
        print('client id:',self.client_id)
        print('raw msg:',self.rawmsg)
        print('--------------------------')
        
    def print_msg(self):
        print('--- Stored message ---')
        print('client id:',self.client_id)
        print('is uplink msg ? :',self.is_uplink)
        print('current msg:',self.msg)
        print('--------------------------')
    
    def get_msg_fport(self):
        current_fport = self.msg['fport']
        return current_fport
    
    def format_raw_msg(self):
        if self.is_rawmsg_valid() == True:
            # check if network type is well defined
            # and call functions dedicated to target (ttn,orange,...)
            self.uplink_formatter(self)
            self.msg = force_type_formatted_dict(self.msg)
            # save local copy for test purposes (à garder pour backup ?)
            # self.save_local_copy()
    
    def set_bypass_decoder(self,boolval):
        self.bypass_decoder = boolval
    
    def is_rawmsg_valid(self):
        rawmsg_valid = False
        if type(self.rawmsg) == dict:
            rawmsg_valid = True
        return rawmsg_valid
    
    def is_fport_valid(self):
        # check and set flag for valid fport
        valid = False
        # Soft check --> if in allowed range in LoRa spec
        if (self.msg['fport'] > 0) and (self.msg['fport'] <= 233):
            # Strong check --> if declared in fport routing table
            if np.sum(self.fport_table == str(self.msg['fport'])) == True:
                valid = True
        return valid
        
    def is_payload_valid(self):
        # check and set flag for valid fport
        valid = False
        if type(self.msg['payload']) == str: 
            if len(self.msg['payload']) >= 2:
                valid = True
        return valid
        
    def save_local_copy(self):
        print('saving local copy ...')
        filepath = './temp/'
        if not os.path.exists(filepath):
            os.makedirs(filepath)
        filename = 'msg_from_'+self.client_id+'_'+ dt.datetime.now().strftime('%y-%m-%d_%H-%M-%S')
        with open(filepath+filename, "w") as write_file:
            json.dump(self.msg, write_file, indent=4)
    
    def update_decoder_func(self,decoder_func):
        print('Updating payload decoder function ...')
        # check if the decoder passed is actually a callable and declared function
        if callable(decoder_func) == True:
            self.payload_decoder = decoder_func
            print('payload decoder updated. Curent msg.fport =',self.msg['fport'])
            print(self.payload_decoder)
        else:
            print('[warning] No payload decoder set, using default ... ')
            self.update_decoder_func(self._default_payload_decoder)
            
        
    def decode_hexapayload(self):
        if self.bypass_decoder == True:
            print('[info] Payload decoder internally bypassed. No payload decoding ...')
        else:
            if self.is_payload_valid() == True:
                print('Decoding hexa payload ...')
                # Backup hexapayload in a new field
                self.msg['hexapayload'] = self.msg['payload']
                # Compute payload fields and values from hexa payload
                self.msg['payload'] = self.payload_decoder(self.msg['payload'])
                # Copy field in payload dict to main message and clean col
                self.msg.update(self.msg['payload'])
                self.msg.pop('payload')
            else:
                print('[error] found invalid hexapayload. No payload decoding')
        
    def update_device_bucket_info(self):
        print('Updating device bucket info ...')
        tab = self.fport_table
        if self.is_fport_valid() == True:
            self.influx_bucket  = tab[tab[:,0] == str(self.msg['fport'])][0,1]
            self.influx_meas    = tab[tab[:,0] == str(self.msg['fport'])][0,2]
        else:
            print('[error] current msg fport not valid. Target influxdb bucket not updated')
            self.influx_bucket  = None
            self.influx_meas    = None
        
    def update_client_bucket_info(self,influx_bucket,influx_meas):
        print('Updating client bucket info ...')
        self.client_influx_bucket  = influx_bucket
        self.client_influx_meas    = influx_meas
        
    # --- internal methods ----------------------------------------------------
    
    def _load_fport_routing_table(self,filepath):
        with open(filepath, "r") as read_file:
            print('[info] loading fport routing table at path:',filepath)
            # self.fport_table = pd.read_csv(read_file)
            self.fport_table = np.genfromtxt(fport_routing_table_path,delimiter=',',dtype=str)
            self.fport_table = self.fport_table[1:]
            print('fport routing rules :',self.fport_table)
            
    def _default_payload_decoder(self,hexapayload):
        payload = {'hexval':hexapayload }
        print('[warning] Using default payload decoder, does nothing ...')
        return payload
    
    def _default_uplink_formatter(self,args):
        ############################################
        # Convert ttn uplink message to formatted dict
        #
        ############################################
        self.is_uplink = False
        print('[warning] Using default uplink formatter, does nothing ...')
   
   
#%% section: custom class for various clients (mqtt, http, ssh, ...)

class MqttClient(mqtt.Client):
    ######################################
    # Class for TTN client
    ######################################
    
    def __init__(self, server, port, apikey, username="undef", topic='#',
                 client_id="", nwk_type='undef',
                 clean_session=True, userdata=None, use_tls=False, 
                 protocol=mqtt.MQTTv31):
        mqtt.Client.__init__(self)
        self.server = server
        self.port = port
        self.apikey = apikey
        self.username = username
        self.topic = topic
        self.client_id = client_id
        self.nwk_type = nwk_type
        self._subTopics = {}
        # Authentification with API keys
        mqtt.Client.username_pw_set(self, username=self.username, password=self.apikey)
        if use_tls == True:
            mqtt.Client.tls_set(self, ca_certs=None, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
                                tls_version=ssl.PROTOCOL_TLS, ciphers=None)
    
    #--- Callable methods -----------------------------------------------------
    
    def connect(self):
        print("MQTT connect "+str(self.server)+" "+str(self.port))
        return mqtt.Client.connect(self, self.server, self.port)
    
    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        # Subscribing in on_connect()
        print('Subscribing to topic:',self.topic)
        client.subscribe(topic=self.topic)
    
    def unsubscribe(self, topic):
        (error, mid) = mqtt.Client.unsubscribe(self, topic)
        if error == mqtt.MQTT_ERR_SUCCESS and topic in self._subTopics:
            del self._subTopics[topic]
        return (error, mid)
    
    def subscribe(self, topic, qos=10, callback=None, callbackArg=None ):
        (error, mid) = mqtt.Client.subscribe(self, topic, qos=0)
        if error == mqtt.MQTT_ERR_SUCCESS:
            self._subTopics[topic] = {
                "request_qos":qos,
                "subMID":mid,
                "callback":callback,
                "callbackArg":callbackArg,
                "regex": re.compile(topic.replace("+", "[^/]+")),
            }
        return (error, mid)

class DummyClient():
    ######################################
    # Class for Dummy client
    ######################################
    
    def __init__(self, server, port, apikey, username="undef", topic='#',
                 client_id="", nwk_type='undef'):
        ## Def params. Same has other client
        self.server = server
        self.port = port
        self.apikey = apikey
        self.username = username
        self.topic = topic
        self.client_id = client_id
        self.nwk_type = nwk_type
        ## def specific params
        self.internal_fcnt = 0
        self.devid = ''
        self.fport = 0
        self.next_msg = {}
        self.tab_frmpay = ['']
        self.cnt_tab_frmpay = 0
        
    #--- Callable methods -----------------------------------------------------
    
    def set_device_info(self,devid,fport,fcnt=0):
        self.devid = devid
        self.fport = fport
        self.internal_fcnt = fcnt
        
    def load_frmpayload_linearseq(self,tabsize,nbbytes,startval=0,delta=1):
        buf = []
        for i in range(0,tabsize):
            val = startval + i*delta
            hexval = hex(val)[2:] # remove the 'Ox' prefix with [2:]
            while len(hexval) < 2*nbbytes:
                hexval = '0'+hexval
            frmval = base64.b64encode(bytearray.fromhex(hexval))
            frmval = str(frmval)[2:-1]
            buf.append(frmval)
        self.tab_frmpay = buf
        print('[info]', self.tab_frmpay, 'sequential frm payload(s) loaded ...')
        
    def load_frmpayload(self,frmpayload):
        buf = [] 
        if type(frmpayload)==list:
            for entry in frmpayload:
                if type(entry)==str:
                    buf.append(frmpayload)
        if type(frmpayload)==str:
                buf = [frmpayload]
        self.tab_frmpay = buf
        print('[info]', self.tab_frmpay, 'frm payload(s) loaded ...')
    
    def emulate_data_as_uplink(self):
        # load current payload in tab
        frmpay = self.tab_frmpay[self.cnt_tab_frmpay]
        # increase counter or reset if more than length of payload tab
        self.cnt_tab_frmpay = self.cnt_tab_frmpay + 1
        if self.cnt_tab_frmpay >= len(self.tab_frmpay):
            self.cnt_tab_frmpay = 0
        # build dummy message
        upmsg=dict()
        if self.nwk_type == 'ttn':
            print('building ttn msg')
            upmsg = self._build_ttn_message(frmpay)
        elif self.nwk_type == 'generic':
            print('building generic msg')
            upmsg = self._build_generic_message(frmpay)
        else:
            upmsg = self._build_generic_message(frmpay)
            
        # Add +1 to virtual device fcnt 
        self._increase_internal_fcnt()
        return upmsg
    
    # --- internal methods ----------------------------------------------------
    
    def _build_generic_message(self,frmpayload):
        gen_msg = {'devid':self.devid, 'deveui':'', 'devadd':'',
                   'appid':self.username, 'fcnt':self.internal_fcnt,
                   'fport':self.fport, 'gwid':'nogateway', 'gweui':'',
                   'timestamp':'notime', 'rssi':0.0, 'snr':0.0,
                   'gwlat':-21.098662,'gwlng':55.480264,
                   'frmpayload':frmpayload, 'payload':''}
        return gen_msg
        
    def _build_ttn_message(self,frmpayload):
        # Copy from TTN console
        # print('building ttn msg')
        ttn_msg = { # end device information
                    "end_device_ids":{"device_id" : self.devid,                   
                                      "application_ids" : {"application_id" : self.username },
                                      "dev_eui"  : "",          
                                      "join_eui" : "",         
                                      "dev_addr" : ""},
                    # uplink content
                    "uplink_message":{"f_cnt": self.internal_fcnt,                              
                                      "f_port": self.fport,                             
                                      "frm_payload": frmpayload,
                                      "rx_metadata": [{ "gateway_ids":{"gateway_id": "nogateway",
                                                                       "eui": ""},
                                                        "time": "notime",    
                                                        "timestamp": 0,               
                                                        "rssi": 0.0,                           
                                                        "channel_rssi": 0.0,                   
                                                        "snr": 0.0,                   
                                                        "location": { "latitude": -21.098662,       
                                                                      "longitude": 55.480264,      
                                                                      "altitude": 3000.0} # piton des neiges
                                                    }],
                                      
                                      },
                    }
        return ttn_msg
        
    #--- Callable methods -----------------------------------------------------
    
    def _increase_internal_fcnt(self):
        self.internal_fcnt = self.internal_fcnt + 1
        if self.internal_fcnt >= (2**32-1):
            self.internal_fcnt = 0
   
#%% section: specific uplink formatter for each network we want to connect
   
def generic_uplink_formatter(data):
    ############################################
    ## Convert generic uplink message to formatted dict
    #
    # input variable 'data' have to be of type DataContainer
    #
    # Raw message are dict(). Previously converted with json.loads()
    # - parse first level of dict and add or overwrite date
    # - convert other level to string if possible, discard otherwise
    #
    ############################################  
    data.is_uplink = True
    for entry in data.rawmsg:
        val = str(data.rawmsg[entry])
        data.msg[entry] = val
        if len(data.msg['frmpayload'])>0:
            data.msg['payload']   = base64.b64decode(data.msg['frmpayload']).hex()
     
def ttn_uplink_formatter(data):
    ############################################
    # Convert ttn uplink message to formatted dict
    #
    # input variable 'data' have to be of type DataContainer
    #
    # Raw message are dict(). Previously converted with json.loads()
    # Avalaible fields are documented at:
    #       - https://www.thethingsindustries.com/docs/reference/data-formats/#uplink-messages
    #
    ############################################
                
    # Check if message type is actually "uplink" and if valid
    if 'uplink_message' in data.rawmsg:
        data.is_uplink = True
        # fill msg dict with data in raw message
        data.msg['devid']         = data.rawmsg['end_device_ids']['device_id']
        data.msg['appid']         = data.rawmsg['end_device_ids']['application_ids']['application_id']
        data.msg['deveui']        = data.rawmsg['end_device_ids']['dev_eui']
        data.msg['devadd']        = data.rawmsg['end_device_ids']['dev_addr']
        data.msg['fcnt']          = data.rawmsg['uplink_message']['f_cnt']
        data.msg['fport']         = data.rawmsg['uplink_message']['f_port']
        data.msg['frmpayload']    = data.rawmsg['uplink_message']['frm_payload']
        # new add : gwcount
        data.msg['gwcnt']         = len(data.rawmsg['uplink_message']['rx_metadata'])
        print('DEBUG >>> GATEWAY COUNT TTN = ',data.msg['gwcnt'] )
        data.msg['gwid']          = data.rawmsg['uplink_message']['rx_metadata'][0]['gateway_ids']['gateway_id']
        data.msg['gweui']         = data.rawmsg['uplink_message']['rx_metadata'][0]['gateway_ids']['eui']
        
        data.msg['rssi']          = data.rawmsg['uplink_message']['rx_metadata'][0]['rssi']
        data.msg['snr']           = data.rawmsg['uplink_message']['rx_metadata'][0]['snr']
        data.msg['channel_rssi']           = data.rawmsg['uplink_message']['rx_metadata'][0]['channel_rssi']

        data.msg['bandwidth']     = data.rawmsg['uplink_message']['settings']['data_rate']['lora']['bandwidth']
        data.msg['spreading_factor'] = data.rawmsg['uplink_message']['settings']['data_rate']['lora']['spreading_factor']

        # if gateway time avalaible
        if 'time' in data.rawmsg['uplink_message']['rx_metadata'][0]:
            data.msg['timestamp']     = data.rawmsg['uplink_message']['rx_metadata'][0]['time']
        # else use TTN server time
        else:
            data.msg['timestamp']     = data.rawmsg['received_at']
        # if gateway location valaible
        if 'location' in data.rawmsg['uplink_message']['rx_metadata'][0]:
            data.msg['gwlat']         = data.rawmsg['uplink_message']['rx_metadata'][0]['location']['latitude']
            data.msg['gwlng']         = data.rawmsg['uplink_message']['rx_metadata'][0]['location']['longitude']
            data.msg['gwalt']         = data.rawmsg['uplink_message']['rx_metadata'][0]['location']['altitude']
        else:
            print('no gateway location found in current message')
        # convert frm paylaod to hexadecimal format
        data.msg['payload']   = base64.b64decode(data.msg['frmpayload']).hex()
        
        # add gateway json fields to handle multiple gateways
        rx_meta_list = data.rawmsg['uplink_message']['rx_metadata']
        nbgw = len(rx_meta_list)
        gw_json = dict()
        for i in range(nbgw):
            gwid = rx_meta_list[i]['gateway_ids']['gateway_id']
            # add eui and rssi
            gw_json[gwid]=dict(gweui = rx_meta_list[i]['gateway_ids']['eui'],
                                                                       rssi = rx_meta_list[i]['rssi'],
                                                                       channel_rssi = rx_meta_list[i]['channel_rssi'],
                                                                       snr = rx_meta_list[i]['snr']
                                                                       )
            # add time if available
            if 'time' in rx_meta_list[i]:
                gw_json[gwid]['time'] = rx_meta_list[i]['time']
            
            # add location if available
            if 'location' in rx_meta_list[i]:
                gw_json[gwid]['gwlat'] = rx_meta_list[i]['location']['latitude']
                gw_json[gwid]['gwlng'] = rx_meta_list[i]['location']['longitude']
                if 'altitude' in rx_meta_list[i]['location']: # altitude value can be missing in rx_meta_list[i]['location']
                    gw_json[gwid]['gwalt'] = rx_meta_list[i]['location']['altitude']  
        # save dict into json str
        data.msg['gw_json'] = str(gw_json)
                
    else:
        print('[warning] Not a valid type. Will be Discard ...')
        data.is_uplink = False
        
def orange_uplink_formatter(data):
    ############################################
    # Convert Orange Live Object uplink message to formatted dict
    #
    # input variable 'data' have to be of type DataContainer
    #
    # Raw message are dict(). Previously converted with json.loads()
    # Avalaible fields are documented at:
    #       - https://liveobjects.orange-business.com/doc/html/lo_manual_v2.html#DATAMODEL
    #       - https://liveobjects.orange-business.com/cms/app/uploads/Manuel-utilisateur-Live-Objects-1.pdf
    #
    ############################################    

    # Check if message type is actually "uplink" and if valid
    if data.rawmsg['metadata']['network']['lora']['messageType'] == 'UNCONFIRMED_DATA_UP':
        data.is_uplink = True
        
        # fill msg dict with data in raw message
        data.msg['devid']         = data.rawmsg['metadata']['network']['lora']['devEUI'] # no name with orange, set devid=deveui
        data.msg['appid']         = data.rawmsg['metadata']['group']['path']
        data.msg['deveui']        = data.rawmsg['metadata']['network']['lora']['devEUI']
        data.msg['devadd']        = ''
        data.msg['fcnt']          = data.rawmsg['metadata']['network']['lora']['fcnt']
        data.msg['fport']         = data.rawmsg['metadata']['network']['lora']['port']
        data.msg['frmpayload']    = ''
        data.msg['gwid']          = 'orange-gateway' # No gateway id with orange but add new fields gateway count
        data.msg['gweui']         = '' # No gateway id with orange but add new fields gateway count
        data.msg['gwcnt']         = data.rawmsg['metadata']['network']['lora']['gatewayCnt']
        data.msg['timestamp']     = data.rawmsg['timestamp']
        data.msg['rssi']          = data.rawmsg['metadata']['network']['lora']['rssi']
        data.msg['snr']           = data.rawmsg['metadata']['network']['lora']['snr']
        data.msg['spreading_factor'] = data.rawmsg['metadata']['network']['lora']['sf']
        
        # if device location valaible (from orange solver) --> NOT USED ANYMORE BY ORANGE (2024)
        # if 'location' in data.rawmsg['metadata']['network']['lora']:
        #     data.msg['lat_orangesolver']         = data.rawmsg['metadata']['network']['lora']['location']['lat']
        #     data.msg['lng_orangesolver']         = data.rawmsg['metadata']['network']['lora']['location']['lon']
        # else:
        #     print('no gateway location found in current message')

        # convert frm paylaod to hexadecimal format
        data.msg['payload']   = data.rawmsg['value']['payload']
        # add gateway json fields to handle multiple gateways
        gw_json = dict()
        gw_json[data.msg['gwid'] ] = 'no data'
        data.msg['gw_json'] = str( gw_json )
                
    else:
        print('[warning] Not a valid type. Will be Discard ...')
        data.is_uplink = False
    
def chirpstack_uplink_formatter(data):
    ############################################
    # Convert local json files to formatted dict
    #
    # input variable 'data' have to be of type DataContainer
    #
    # Raw message are dict(). Previously converted with json.loads()
    # Avalaible fields are documented at:
    #       - ????
    #
    ############################################
    
    # Check if message type is actually "uplink" and if valid
    if 'uplinkID' in data.rawmsg['rxInfo'][0]:
        data.is_uplink = True
        
        # fill msg dict with data in raw message
        data.msg['devid']         = data.rawmsg['deviceName']
        data.msg['appid']         = data.rawmsg['applicationName']
        data.msg['deveui']        = data.rawmsg['devEUI']
        data.msg['devadd']        = ''
        data.msg['fcnt']          = data.rawmsg['fCnt']
        data.msg['fport']         = data.rawmsg['fPort']
        data.msg['frmpayload']    = data.rawmsg['data']
        data.msg['gwid']          = data.rawmsg['rxInfo'][0]['name' ]
        data.msg['gweui']         = data.rawmsg['rxInfo'][0]['gatewayID']
        if 'time' in data.rawmsg['rxInfo'][0]:
            data.msg['timestamp']     = data.rawmsg['rxInfo'][0]['time']
        else:
            data.msg['timestamp']     = 'notime'         
                                                
        data.msg['rssi']          = data.rawmsg['rxInfo'][0]['rssi']
        data.msg['snr']           = data.rawmsg['rxInfo'][0]['loRaSNR']
        
            
        # if gateway location valaible
        if 'location' in data.rawmsg['rxInfo'][0]:
            data.msg['gwlat']         = data.rawmsg['rxInfo'][0]['location']['latitude']
            data.msg['gwlng']         = data.rawmsg['rxInfo'][0]['location']['longitude']
        else:
            print('no gateway location found in current message')
        # convert frm paylaod to hexadecimal format
        data.msg['payload']   = base64.b64decode(data.msg['frmpayload']).hex()
        
        # add gateway json fields to handle multiple gateways
        gw_json = dict()
        gw_json['gwid'] = 'no data'
        
    else:
        print('[warning] Not a valid type. Will be Discard ...')
        data.is_uplink = False
