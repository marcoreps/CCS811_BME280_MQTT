import smbus2
import bme280
import configparser
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import logging
import qwiic_ccs811
from tmp117 import Tmp117
from pathlib import Path
import serial

SERIAL_PORT = '/dev/ttyACM1'
SERIAL_BAUD_RATE = 115200




class influx_writer:

    def __init__(self, url, token, org):
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        
    def write(self, bucket, measurement, field, val, timestamp=None, tags=None):
        if not timestamp:
            timestamp = datetime.now()
        logging.debug('writing point to influxdb: measurement=%s field=%s val=%s'%(str(measurement),str(field),str(val)))
        p = Point(measurement).field(field, float(val))
        if tags is not None:
            for t in tags:
                p.tag(t[0], t[1])
        logging.debug('point made')
        try:
            self.write_api.write(bucket, record=p)
        except Exception as exc:
            logging.error(exc)
            pass
        logging.debug('point written, writer done')
        
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
logging.info("Starting ...")


config = configparser.ConfigParser()
config.read(Path(__file__).with_name('conf.ini'))
influx_url = config['INFLUX']['url']
influx_token = config['INFLUX']['token']
influx_org = config['INFLUX']['org']

writer=influx_writer(influx_url, influx_token, influx_org)

port = 1
bme280_address = 0x77
bus = smbus2.SMBus(port)

calibration_params = bme280.load_calibration_params(bus, bme280_address)



ccs = qwiic_ccs811.QwiicCcs811()
if ccs.connected == False:
    print("The Qwiic CCS811 device isn't connected to the system. Please check your connection", \
        file=sys.stderr)
ccs.begin()


i2c_address = 0x4a
tmp = Tmp117(i2c_address)
tmp.init()
tmp.setConversionMode(0x11)
tmp.oneShotMode()



ser = None
try:
    # Open the serial port with a timeout for readline()
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD_RATE, timeout=10) 
    logging.info(f"Successfully opened serial port {SERIAL_PORT} at {SERIAL_BAUD_RATE} baud.")
    ser.flushInput()
    logging.info("Serial input buffer flushed.")
except serial.SerialException as e:
    logging.error(f"Could not open serial port {SERIAL_PORT}: {e}")
    
    
def read_serial_tmp119_temp():
    
    if ser is None or not ser.is_open:
        logging.error("Serial port is not open for reading Arduino TMP117 data.")
        return

    try:
        while ser.in_waiting > 0:
            line_bytes = ser.readline()
            if not line_bytes:
                logging.debug("Serial readline timed out while draining buffer.")
                continue

            line = line_bytes.decode('utf-8').strip()
            logging.debug(f"Raw serial line received from Arduino (buffered): '{line}'")

            if line.startswith("Temperature:"):
                try:
                    # Extract the numerical part after "Temperature:"
                    temp_str = line.split(':')[1]
                    temperature = float(temp_str)
                    return temperature
                except (ValueError, IndexError) as e:
                    logging.warning(f"Failed to parse temperature from line '{line}': {e}")
            elif line: 
                logging.debug(f"Non-temperature line received from Arduino (buffered): '{line}'")

    except serial.SerialTimeoutException:
        logging.warning("Serial read timed out while buffering.")
    except Exception as e:
        logging.error(f"Error reading from serial port for buffering: {e}")



while(True):

    while not tmp.dataReady():
        time.sleep(1)
    celsius = tmp.readTempC()
    writer.write('lab_sensors', 'Ambient_Temp', 'TMP117_on_gpibpi', celsius)
    
    
    serial_celsius = read_serial_tmp119_temp()
    if serial_celsius is not None:
        writer.write('lab_sensors', 'Ambient_Temp', 'TMP119_on_MG24', serial_celsius)
        logging.info(f"MG24 TMP119 Temp: {serial_celsius:.4f} °C")
    else:
        logging.warning("No valid TMP119 reading received from MG24 via serial in this cycle.")
    
    

    data = bme280.sample(bus, bme280_address, calibration_params)
    writer.write('lab_sensors', 'Ambient_Temp', 'BME280', data.temperature)
    writer.write('lab_sensors', 'Ambient_Pressure', 'BME280', data.pressure)
    writer.write('lab_sensors', 'Ambient_Humidity', 'BME280', data.humidity)

    ccs.set_environmental_data(data.humidity, data.temperature)
    ccs.read_algorithm_results()
    writer.write('lab_sensors', 'Ambient_CO2', 'CCS811', ccs.get_co2())
    writer.write('lab_sensors', 'Ambient_tVOC', 'CCS811', ccs.get_tvoc())
    
    time.sleep(30)
    tmp.oneShotMode()
