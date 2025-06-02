# -*- coding: utf-8 -*-
"""
██████╗  █████╗ ████████╗ █████╗ ███████╗██╗     ██╗   ██╗██╗  ██╗
██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔════╝██║     ██║   ██║╚██╗██╔╝
██║  ██║███████║   ██║   ███████║█████╗  ██║     ██║   ██║ ╚███╔╝ 
██║  ██║██╔══██║   ██║   ██╔══██║██╔══╝  ██║     ██║   ██║ ██╔██╗ 
██████╔╝██║  ██║   ██║   ██║  ██║██║     ███████╗╚██████╔╝██╔╝ ██╗
╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝
                                                                   
 [MAIN APP]
 Scripts to continously read, process and store 
 new data comming from various LoRa servers

 Version: v1.1

 Usage:
 - create dedicated flow file (.json) to configure the script
 - run script in console with flow file as arguments
 - ex: $python dataflux.py --flow ./flow/flow_myfile.json
     
"""

import os
# os.chdir('.')
import csv
import json
import numpy as np
import datetime as dt
import time
import base64
import paho.mqtt.client as mqtt
from threading import Thread, Lock
import argparse

# Lockal package
from lib.lib_client import *
from lib.lib_decoder import *
from lib.lib_influxdb import *
from lib.lib_app import *

#%% section: server info
#############################################################################
#
#############################################################################

parser = argparse.ArgumentParser(description="Dataflux - Manage dataflow from LoRa server to Influxdb database")

parser.add_argument('--flow', action="store", required=False, type=str, 
                    help="specify flow file path (.json)")
parser.add_argument('--delayloop', action="store", required=False, type=str, 
                    help="fix the wake up delay of the process thread")
args = parser.parse_args()

# flow_config_file = './flow/flow_dummy.json'
# flow_config_file = './flow/flow_ttn_doi-test-app.json'
# flow_config_file = './flow/flow_orange_doi-test-fifo.json'
# flow_config_file = './flow/flow_ttn_test-thesis-pierre.json'
# flow_config_file = './flow/flow_chirpstack_mj-test-app.json'
# flow_config_file = './flow/flow_ttn_loraship-ifremer-app.json'
flow_config_file = './flow/flow_orange_loraship-fifo.json'

processloop_delay= 10

# Overwrite values above with passed command-line arguments
if args.flow is not None:
    flow_config_file = args.flow
if args.delayloop is not None:
    processloop_delay = float(args.delayloop)

#%% section: main
#############################################################################
#
#############################################################################

print('>>>>> Hello ! >>>>>>\n')

print('... loading flow info from file', flow_config_file)

with open(flow_config_file) as json_file:
    nwkinfo = json.load(json_file)

print('--- Flow Configuration ---')
print(nwkinfo)
print('--------------------------\n')

print('>>>>> Starting Flow >>>>>>\n')

if __name__ == '__main__':
    ## Build main app
    mainapp = MainApp(nwkinfo)
    ## Choose speed of processing thread 
    mainapp.set_processloop_delay(processloop_delay)
    ## run main app (start client thread + process/store thread)
    mainapp.print_console_header()
    mainapp.run_app()
    
    print('>>>>> Ending dataflux instance >>>>>>\n')

#%%


