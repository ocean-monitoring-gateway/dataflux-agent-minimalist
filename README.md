![logo](./docs/dataflux_logo_1.png)

Python scripts and libraries to continuously read, process and store new data coming from various LoRa servers into an InfluxDB V2 database.

Table of Content
- [Overview](#overview)
- [Environment installation](#environment-installation)
- [Starting a new flow](#starting-a-new-flow)
  - [Step 1: Adding fport routing information](#step-1-adding-fport-routing-information)
  - [Step 2: Flow configuration](#step-2-flow-configuration)
  - [Step 3: Run the script](#step-3-run-the-script)
- [Injecting data manually](#injecting-data-manually)


*Ifremer / LIRMM (CNRS, University of Montpellier)*

---

## Overview

For each running instance of *dataflux.py* , a connection - named *flow* - is created between a specified pool of devices  inside a LoRa network (data source) and some buckets inside an Influxdb v2 database.

Those instances are run in parallel and their number depends on how many data sources we want to connect to the database. Typical sources are *integration* features offered by the LoRa servers. More info at [MQTT Server | The Things Stack for LoRaWAN](https://www.thethingsindustries.com/docs/integrations/mqtt/) , [MQTT and FIFO in Live Object doc](https://liveobjects.orange-business.com/doc/html/lo_manual_v2.html#_mqtt_api) or [MQTT - ChirpStack open-source](https://www.chirpstack.io/application-server/integrations/mqtt/).

**List of currently supported server:**

- TTN over MQTT protocol
- Orange over MQTT protocol 
- Chirpstack over MQTT protocol
- Local files (script compatible with generic csv files and with data directly downloaded as .csv or .json on the TTN and Orange web interface)

**Related Documentation**

- [Advanced Topics](./docs/advanced-topics.md)

## Environment installation

It is recommended to run the program using the **Python 3.7** version.

To install all required package at once, open a console, clone the repository,  go to the program root directory and use conda or pip to install package

```
# using conda
conda create --name <myenv>
conda activate <myenv>
conda install --channel=conda-forge --file requirements.txt

# using pip inside conda env
conda create --name <myenv>
conda activate <myenv>
pip install -r requirements.txt
```

## Starting a new flow

Start a proper Python environment with required packages installed and follow the steps below to create a new connection between a server and an Influxdb database.

### Step 1: Adding fport routing information
- Choose a fport through which your device payload will be sent
- On InfluxDB, create a new bucket if necessary
- **(Only on the host)** At the root of the Dataflux project, open the file `./influxdb_authbuckets.json` and add the token associated with your InfluxDB bucket
- Open the file `./fport_routing_table.csv`
- Add a new row with:
    - Chosen port
    - InfluxDB bucket name
    - InfluxDB measurement name
    - Decoder function name
    - Comments about this new route
- Open the file `lib/lib_decoder.py`
- In the section  *“define custom decoder functions”*, add the definition of your decoder function so it decodes correctly your device payload

### Step 2: Flow configuration

Write a *flow* file (.json) with info on start and end points. For supported servers, several templates are available in directory `./flow/`.

Below is an example of a *flow* file to connect a TTN en-devices application to the Influxdb database.

```json
{
    "nwk_type": "ttn",
    "protocol": "mqtt",
    "client_id": "myttnappname",
    "influx_bucket": "mybucket",
    "influx_meas": "received",
    "server": "eu1.cloud.thethings.network",
    "port": 1883,
    "username": "myttnappname@ttn",
    "apikey": "MYAPIKEY",
    "topic": "v3/myttnappname/devices/+/up",
    "use_tls": false
}    
```

The 3 first fields *"nwk_type"*, *"protocol"* and *"client_id"* are mandatory and used by the *dataflux.py* program to configure and identify it-self all along the execution. 

The next two fields *"influx_bucket"* and *"influx_meas"* are also mandatory and must point to an existing and already declared bucket. Field *"influx_meas"* can be any value but still chosen carefully.

> **Warning:** These fields refer to the *flow*'s bucket, used for data backup and network analysis, **it is not the final buckets for end-devices messages**. Messages, if checked valid, are then automatically redirected toward the proper buckets according to their "FPort" and rules defined in file `./fport_routing_table.csv`.

Existence and values of last fields will depend on the server we want to connect and on the protocol used to get data out.

| Field         | Possible values                                                                                                                                                      | Type      |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| nwk_type      | "ttn" or "orange" or "chirpstack" or "generic"                                                                                                                       | Mandatory |
| protocol      | "mqtt" or "http" or "ssh" or "manual"                                                                                                                                | Mandatory |
| client_id     | Any string. It is the *flow* identifier and will be used to tag influxdb entries.                                                                                    | Mandatory |
| influx_bucket | Any existing bucket name. Recommended: "iot-networks"                                                                                                                | Mandatory |
| influx_meas   | Any string but this is the 1st level of data filtering inside Influxdb. Recommended: "received" if its an automatic *flow* "uploaded" if it a manual data injection. | Mandatory |
| [*Others*]    | Will depend on the server and on the protocol.                                                                                                                       | Optional  |

### Step 3: Run the script

Run the *dataflux.py* with your *flow* file as argument. 

```
python dataflux.py --flow myflow.json
```

It is recommended to run the script inside a docker. Instructions and Dockerfile templates can be found in this git repository in folder `./docker/`.

The script can also run as a systemctl deamon, on smaller host such as a Raspberry Pi.

## Injecting data manually

Edit the dedicated *flow* file `./flow/flow_localfile.json` to specify the correct network info (*nwk_type*) and Influxdb info (*influx_bucket* , *influx_meas*)

```
{
    "nwk_type": "ttn",
    "protocol": "manual",
    "client_id": "localfile",
    "influx_bucket": "iot-networks-dev",
    "influx_meas": "uploaded"
}
```

| Field     | Possible values|
| --------- | ---------------|
| nwk_type  | "ttn" or "orange" or "chirpstack" or "generic". For any standard csv or json files use "generic" type. Use the others for files downloaded directly from "live data" tabs on the TTN, Orange or Chirpstack web interfaces |
| protocol  | "manual" only (do not edit this field)|
| client_id | Any string. But recommended value is "uploaded"|

Run the command below with path to your *flow* and *input* files

```
python injectdata.py --flow flow_localfile.json --input path/to/mydata.csv
```

