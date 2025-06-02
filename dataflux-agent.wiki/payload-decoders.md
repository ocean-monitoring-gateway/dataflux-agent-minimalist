# Payload Decoders Documentation

---

## decoder: Custom Cayenne LPP

**Function name:** `payload_decoder_cayennelpp(hexstr)`

**Location:** in dataflux/lib/lib_decoder.py

**Linked to Fport:** 

**Description:** A decoder that is based on the Python package [pycayennelpp](https://pypi.org/project/pycayennelpp/) to decode hexadecimal payload encoded with the Cayenne LPP format. Returned field names (columns) correspond to the Cayenne sensor types (see below for actual names), followed by a 2-digit suffix that identify the field inside the payload.

```
# fields names
digital_input, digital_output, analog_input, analog_output, lum_sensor, pres_sensor, temp_sensor, humid_sensor, acc_x, acc_y, acc_z, baro_sensor, gyro_x, gyro_y, gyro_z, gps_lat, gps_lng, gps_alt
```

**Payload format:** See Mydevices [on-line documentation](https://docs.mydevices.com/docs/lorawan/cayenne-lpp)

---

## decoder: name

**Function name:** `payload_decoder_xxxx(hexstr)`

**Location:** in dataflux/lib/lib_decoder.py

**Linked to Fport:**

**Description:** Text

**Payload format:** Text

---

## decoder: name

**Function name:** `payload_decoder_xxxx(hexstr)`

**Location:** in dataflux/lib/lib_decoder.py

**Linked to Fport:**

**Description:** Text

**Payload format:** Text

---

## decoder: name

**Function name:** `payload_decoder_xxxx(hexstr)`

**Location:** in dataflux/lib/lib_decoder.py

**Linked to Fport:**

**Description:** Text

**Payload format:** Text

---