
import configparser
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import time
import logging
from pathlib import Path
from tmp117 import Tmp117



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
        
        
        
    


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s')
    logging.info("LFG")
    config = configparser.ConfigParser()
    config.read(Path(__file__).with_name('conf.ini'))
    influx_url = config['INFLUX']['url']
    influx_token = config['INFLUX']['token']
    influx_org = config['INFLUX']['org']

    writer=influx_writer(influx_url, influx_token, influx_org)

    i2c_address = 0x4a
    sensor = Tmp117(i2c_address)
    sensor.init()
    sensor.setConversionMode(0x11)
    sensor.oneShotMode()
    
    while(True):
        logging.debug("while")
        if(sensor.dataReady()):
            celsius = sensor.readTempC()
            writer.write('lab_sensors', 'Ambient_Temp', 'TMP117_on_calibratorpi', celsius)
            logging.debug("Shot fired, temp="+str(celsius))
            time.sleep(30)
            sensor.oneShotMode()

        time.sleep(1)

if __name__ == "__main__":
    main()




    










