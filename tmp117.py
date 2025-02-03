import smbus2

MODE_CONTINUOUS_CONVERSION_MODE = 0b00
MODE_ONE_SHOT = 0b11
MODE_SHUTDOWN = 0b01

MODE_AVG_0  = 0b00
MODE_AVG_8  = 0b01
MODE_AVG_32 = 0b10
MODE_AVG_64 = 0x11


class Tmp117(object):

  REG_TEMP_RESULT   = 0X00
  REG_CONFIGURATION = 0x01
  REG_T_HIGH_LIMIT  = 0X02
  REG_T_LOW_LIMIT   = 0X03
  REG_EEPROM_UL     = 0X04
  REG_EEPROM1       = 0X05
  REG_EEPROM2       = 0X06
  REG_TEMP_OFFSET   = 0X07
  REG_EEPROM3       = 0X08
  REG_DEVICE_ID     = 0X0F

  DEVICE_ID_VALUE = 0x0117
  TEMP_RESOLUTION = 0.0078125
    
  def __init__(self, address=0x48):
    self.address = address
    self._i2c = smbus2.SMBus(1)

  def init(self):
    chip_id = self.getDeviceId()
    if chip_id != self.DEVICE_ID_VALUE:
      raise ValueError('Wrong chip id at address: 0x{:X}'.format(chip_id))
        
  def readRegister(self, register):
    data = self._i2c.readWord(self.address, register)

    return (data >> 8) & 0xff | (data & 0xff) << 8

  def writeRegister(self, register, data):
    data = (data >> 8) & 0xff | (data & 0xff) << 8
    self._i2c.writeWord(self.address, register, data)
    
  def readTempC(self):
    reg_value = self.readRegister(self.REG_TEMP_RESULT)
    return reg_value * self.TEMP_RESOLUTION

  def getConfigurationRegister(self):
    return self.readRegister(self.REG_CONFIGURATION)

  def writeConfiguration(self, config):
    self.writeRegister(self.REG_CONFIGURATION, config)
    
  def softReset(self):
    config = self.getConfigurationRegister()
    config |= (1 << 1)
    self.writeConfiguration(config)

  def setAlertPinMode(self, data_ready):
    config = self.getConfigurationRegister()
    if data_ready:
      config |= (1 << 2)
    else:
      config &= ~(1 << 2)
    self.writeConfiguration(config)

  def setAlertPinPolarity(self, high):
    config = self.getConfigurationRegister()
    if high:
      config |= (1 << 3)
    else:
      config &= ~(1 << 3)
    self.writeConfiguration(config)
        
  def setThermAlertMode(self, therm_mode):
    config = self.getConfigurationRegister()
    if therm_mode:
      config |= (1 << 4)
    else:
      config &= ~(1 << 4)
    self.writeConfiguration(config)

  def setConversionMode(self, mode):
    if mode not in (MODE_AVG_0, MODE_AVG_8, MODE_AVG_32, MODE_AVG_64):
      return
    config = self.getConfigurationRegister()
    config &= ~(0x3 << 5)
    config |= (mode << 5)
    self.writeConfiguration(config)

  def setConversionCycle(self, time):
    if time > 0x7 or time < 0:
      return
    config = self.getConfigurationRegister()
    config &= ~(0x7 << 7)
    config |= (time << 7)
    self.writeConfiguration(config)

  def setMode(self, mode):
    config = self.getConfigurationRegister()
    config &= ~(0x03 << 10)
    config |= (mode << 10)
    self.writeConfiguration(config)
        
  def continuousConversionMode(self):
    self.setMode(MODE_CONTINUOUS_CONVERSION_MODE)
        
  def oneShotMode(self):
    self.setMode(MODE_ONE_SHOT)

  def shutdownMode(self):
    self.setMode(MODE_SHUTDOWN)

  def dataReady(self):
    config = self.getConfigurationRegister()
    return config & (1 << 13)

  def getDeviceId(self):
    return self.readRegister(self.REG_DEVICE_ID)
        