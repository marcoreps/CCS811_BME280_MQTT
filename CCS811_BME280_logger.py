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



while(True):

    while not tmp.dataReady():
        time.sleep(1)
    celsius = tmp.readTempC()
    writer.write('lab_sensors', 'Ambient_Temp', 'TMP117_on_gpibpi', celsius)

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
