import logging, types, time, enum

logging.basicConfig(level=logging.INFO)

try: import smbus
except ImportError:
    logging.warning("smbus not installed, using stub instead.")
    class smbus(object):
        class SMBus(object):
            def __init__(self, *args, **kwargs): pass
            def read_i2c_block_data(*args): return []
            def write_byte_data(*args): pass

I2C_NORM_LEN    = 4
I2C_LONG_LEN    = 24
I2C_ID_ZEROBORG = 0x40
PWM_MAX         = 255
IR_MAX_BYTES    = I2C_LONG_LEN-2

class Command(enum.IntEnum):
    SetLED       = 1     # Set the LED status
    GetLED       = 2     # Get the LED status
    SetAFwd      = 3     # Set motor 1 PWM rate in a forwards direction
    SetARev      = 4     # Set motor 1 PWM rate in a reverse direction
    GetA         = 5     # Get motor 1 direction and PWM rate
    SetBFwd      = 6     # Set motor 2 PWM rate in a forwards direction
    SetBRev      = 7     # Set motor 2 PWM rate in a reverse direction
    GetB         = 8     # Get motor 2 direction and PWM rate
    SetCFwd      = 9     # Set motor 3 PWM rate in a forwards direction
    SetCRev      = 10    # Set motor 3 PWM rate in a reverse direction
    GetC         = 11    # Get motor 3 direction and PWM rate
    SetDFwd      = 12    # Set motor 4 PWM rate in a forwards direction
    SetDRev      = 13    # Set motor 4 PWM rate in a reverse direction
    GetD         = 14    # Get motor 4 direction and PWM rate
    AllOff       = 15    # Switch everything off
    SetAllFwd    = 16    # Set all motors PWM rate in a forwards direction
    SetAllRev    = 17    # Set all motors PWM rate in a reverse direction
    SetFailSafe  = 18    # Set the failsafe flag, turns the motors off if communication is interrupted
    GetFailSafe  = 19    # Get the failsafe flag
    ResetEPO     = 20    # Resets the EPO flag, use after EPO has been tripped and switch is now clear
    GetEPO       = 21    # Get the EPO latched flag
    SetEPOIgnore = 22    # Set the EPO ignored flag, allows the system to run without an EPO
    GetEPOIgnore = 23    # Get the EPO ignored flag
    GetNewIR     = 24    # Get the new IR message received flag
    GetLastIR    = 25    # Get the last IR message received (long message, resets new IR flag)
    SetLEDIR     = 26    # Set the LED for indicating IR messages
    GetLEDIR     = 27    # Get if the LED is being used to indicate IR messages
    GetAnalog1   = 28    # Get the analog reading from port #1, pin 2
    GetAnalog2   = 29    # Get the analog reading from port #2, pin 4
    GetID        = 0x99  # Get the board identifier
    SetI2cAdd    = 0xAA  # Set a new I2C address
    ValueFwd     = 1     # I2C value representing forward
    ValueRev     = 2     # I2C value representing reverse
    ValueOn      = 1     # I2C value representing on
    ValueOff     = 0     # I2C value representing off
    AnalogMax    = 0x3FF # Maximum value for analog readings

def scanForZeroBorg(busNumber=1):
    logging.info("Scanning I\u00B2C bus #{}".format(busNumber))
    found=[]
    bus=smbus.SMBus(busNumber)
    for address in range(0x03,0x78):
        try:
            i2cRecv=bus.read_i2c_block_data(address, Command.GetID, I2C_NORM_LEN)
            if len(i2cRecv)==I2C_NORM_LEN:
                if i2cRecv[1]==I2C_ID_ZEROBORG:
                    logging.info('Found ZeroBorg at 0x{:02X}'.format(address))
                    found.append(address)

        except KeyboardInterrupt: raise
        except: pass

    if len(found)==0:
        logging.warning(
            "No ZeroBorg boards found, is bus #{} correct? "
            "(Should be 0 for Rev. 1 or 1 for Rev. 2)".format(busNumber)
        )
    elif len(found)==1: logging.info("1 ZeroBorg board found.")
    else: logging.info("{} ZeroBorg boards found.".format(len(found)))
    return found

def setNewAddress(newAddress, oldAddress=-1, busNumber=1):
    if newAddress<0x03 or newAddress>0x77:
        logging.error("Error, I\u00B2C addresses below 3 (0x03) and above 119 (0z77) "
            "are reserved, use an address between 3 (0x03) and 119 (0x77).")

    if oldAddress<0x0:
        found=scanForZeroBorg(busNumber)
        if len(found)<1:
            logging.error("No ZeroBorg boards found, cannot set a new I\u00B2C address!")
            return
        else: oldAddress=found[0]

    logging.info(
        "Changing I\u00B2C address from {:02X} to {:02X} (bus #{})".format(
            oldAddress, newAddress, busNumber))

    bus=smbus.SMBus(busNumber)
    try:
        i2cRecv=bus.read_i2c_block_data(oldAddress, Command.GetID, I2C_ID_ZEROBORG)
        if len(i2cRecv)==I2C_NORM_LEN:
            if i2cRecv[1]==I2C_ID_ZEROBORG:
                foundChip=True
                logging.info("Found ZeroBorg at {:02X}.".format(oldAddress))
            else:
                foundChip=False
                logging.warning("Found a devie at {:02X}, but it is not a ZeroBorg "
                    "(ID {:02X} instead of {:02X})".format(
                        oldAddress, i2cRecv[1], I2C_ID_ZEROBORG))
        else:
            foundChip=False
            logging.error("Missing ZeroBorg at {:02X}".format(oldAddress))

    except KeyboardInterrupt: raise
    except: 
        foundChip=False
        logging.error("Missing ZeroBorg at {:02X}".format(oldAddress))

    if foundChip:
        bus.write_byte_data(oldAddress, Command.SetI2cAdd, newAddress)
        time.sleep(.1)
        logging.info("Address changed to {:02X}, "
            "attempting to communicate on new address.".format(newAddress))

        try:
            i2cRecv=bus.read_i2c_block_data(newAddress, Command.GetID, I2C_NORM_LEN)
            if len(i2cRecv)==I2C_NORM_LEN:
                if i2cRecv[1]==I2C_ID_ZEROBORG:
                    foundChip=True
                    logging.info("Found ZeroBorg at {:02X}.".format(newAddress))
                else:
                    foundChip=False
                    logging.warning("Found a devie at {:02X}, but it is not a ZeroBorg "
                        "(ID {:02X} instead of {:02X})".format(
                            oldAddress, i2cRecv[1], I2C_ID_ZEROBORG))
            else:
                foundChip=False
                logging.error("Missing ZeroBorg at {:02X}".format(newAddress))

        except KeyboardInterrupt: raise
        except:
            foundChip=False
            logging.error("Missing ZeroBorg at {:02X}".format(newAddress))

    if foundChip:
        logging.info("New I\u00B2C address of {:02X} set successfully.".format(newAddress))
    else: logging.error("Failed to set new I\u00B2C address!")

class ZeroBorg(object):
    """
This module is designed to communicate with the ZeroBorg
busNumber               I\u00B2C bus on which the ZeroBorg is attached (Rev 1 is bus 0, Rev 2 is bus 1)
bus                     the smbus object used to talk to the I\u00B2C bus
i2cAddress              The I\u00B2C address of the ZeroBorg chip to control
foundChip               True if the ZeroBorg chip can be seen, False otherwise
printFunction           Function reference to call when printing text, if None "print" is used
    """

    def __init__(self):
        self._busNumber=1
        self._i2cAddress=I2C_ID_ZEROBORG
        self._bus=None
        self._foundChip=False
        self._printFunction=None

    def init(self, tryOtherBus=True):
        """
        init([tryOtherBus])
        Prepare the I2C driver for talking to the ZeroBorg
        If tryOtherBus is True or omitted, this function will attempt to use the other bus if the ZeroBorg devices can not be found on the current busNumber
        """        
        self.print("Loading ZeroBorg on bus {}, address {:02X}.".format(
            self._busNumber, self._i2cAddress))

        self._bus=smbus.SMBus(self._busNumber)
        try:
            i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, Command.GetID, I2C_NORM_LEN)
            if len(i2cRecv)==I2C_NORM_LEN:
                if i2cRecv[1]==I2C_ID_ZEROBORG:
                    self._foundChip=True
                    self.print("Found ZeroBorg at {:02x}.".format(self._i2cAddress))
                else:
                    self._foundChip=False
                    self.print("Found a device at {:02X}, but it is not a ZeroBorg "
                        "(ID {:02X} instead of {:02X}.".format(
                            self._i2cAddress, i2cRecv[1], I2C_ID_ZEROBORG))
            else:
                self._foundChip=False
                self.print("Missing ZeroBorg at {:02X}.".format(self._i2cAddress))
        except KeyboardInterrupt: raise
        except:
            self._foundChip=False
            self.print("Missing ZeroBorg at {:02X}.".format(self._i2cAddress))

        if not self._foundChip:
            self.print("ZeroBorg not found.")
            if tryOtherBus:
                self._busNumber=1 if self._busNumber==0 else 0
                self.print("Trying bus number {} instead.".format(self._busNumber))
                self.init(False)


    def print(self, message):
        """
        print(message)
        Wrapper used by the ZeroBorg instance to print messages, will call printFunction if set, print otherwise
        """        
        if self._printFunction==None: print(message)
        else: self._printFunction(message)

    def noPrint(self, message):
        """
        NoPrint(message)
        Does nothing, intended for disabling diagnostic printout by using:
        ZB = ZeroBorg.ZeroBorg()
        ZB.printFunction = ZB.NoPrint
        """ 

    def _setMotor(self, motor, power):
        pwm=int(PWM_MAX*power)        
        if power<0:
            motor+=1 # Reverse
            pwm=-pwm
            
        if pwm>PWM_MAX: pwm=PWM_MAX

        try: self._bus.write_byte_data(self._i2cAddress, motor, pwm)
        except KeyboardInterrupt: raise
        except: self.print("Failed setting motor drive level!")

    def setMotor1(self, power):
        """
        setMotor1(power)
        Sets the drive level for motor 1, from +1 to -1.
        e.g.
        setMotor1(0)     -> motor 1 is stopped
        setMotor1(0.75)  -> motor 1 moving forward at 75% power
        setMotor1(-0.5)  -> motor 1 moving reverse at 50% power
        setMotor1(1)     -> motor 1 moving forward at 100% power
        """
        self._setMotor(Command.SetAFwd, power)

    def setMotor2(self, power):
        """
        setMotor2(power)
        Sets the drive level for motor 2, from +1 to -1.
        e.g.
        setMotor2(0)     -> motor 2 is stopped
        setMotor2(0.75)  -> motor 2 moving forward at 75% power
        setMotor2(-0.5)  -> motor 2 moving reverse at 50% power
        setMotor2(1)     -> motor 2 moving forward at 100% power
        """
        self._setMotor(Command.SetBFwd, power)

    def setMotor3(self, power):
        """
        setMotor3(power)
        Sets the drive level for motor 3, from +1 to -1.
        e.g.
        setMotor3(0)     -> motor 3 is stopped
        setMotor3(0.75)  -> motor 3 moving forward at 75% power
        setMotor3(-0.5)  -> motor 3 moving reverse at 50% power
        setMotor3(1)     -> motor 3 moving forward at 100% power
        """
        self._setMotor(Command.SetCFwd, power)

    def setMotor4(self, power):
        """
        setMotor4(power)
        Sets the drive level for motor 4, from +1 to -1.
        e.g.
        setMotor4(0)     -> motor 4 is stopped
        setMotor4(0.75)  -> motor 4 moving forward at 75% power
        setMotor4(-0.5)  -> motor 4 moving reverse at 50% power
        setMotor4(1)     -> motor 4 moving forward at 100% power
        """
        self._setMotor(Command.SetDFwd, power)

    def setMotors(self, power):
        """
        setMotors(power)
        Sets the drive level for all motors, from +1 to -1.
        e.g.
        setMotors(0)     -> all motors are stopped
        setMotors(0.75)  -> all motors are moving forward at 75% power
        setMotors(-0.5)  -> all motors are moving reverse at 50% power
        setMotors(1)     -> all motors are moving forward at 100% power
        """
        self._setMotor(Command.SetAllFwd, power)

    def motorsOff(self):
        """
        motorsOff()
        Sets all motors to stopped, useful when ending a program
        """
        try: self._bus.write_byte_data(self._i2cAddress, Command.AllOff, 0)
        except KeyboardInterrupt: raise
        except: self.print("Failed sending motors off command!")

    def _getMotor(self, motor):
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, motor, I2C_NORM_LEN)
        except KeyboardInterrupt: raise
        except:
            self.print("Failed reading motor drive level!")
            return

        power=float(i2cRecv[2])/float(PWM_MAX)
        if i2cRecv[1]==Command.ValueFwd: return power
        elif i2cRecv[1]==Command.ValueRev: return -power
        return

    def getMotor1(self):
        """
        power = getMotor1()
        Gets the drive level for motor 1, from +1 to -1.
        e.g.
        0     -> motor 1 is stopped
        0.75  -> motor 1 moving forward at 75% power
        -0.5  -> motor 1 moving reverse at 50% power
        1     -> motor 1 moving forward at 100% power
        """
        return self._getMotor(Command.GetA)

    def getMotor2(self):
        """
        power = getMotor2()
        Gets the drive level for motor 1, from +1 to -1.
        e.g.
        0     -> motor 1 is stopped
        0.75  -> motor 1 moving forward at 75% power
        -0.5  -> motor 1 moving reverse at 50% power
        1     -> motor 1 moving forward at 100% power
        """
        return self._getMotor(Command.GetB)

    def getMotor3(self):
        """
        power = getMotor3()
        Gets the drive level for motor 1, from +1 to -1.
        e.g.
        0     -> motor 1 is stopped
        0.75  -> motor 1 moving forward at 75% power
        -0.5  -> motor 1 moving reverse at 50% power
        1     -> motor 1 moving forward at 100% power
        """
        return self._getMotor(Command.GetC)

    def getMotor4(self):
        """
        power = getMotor4()
        Gets the drive level for motor 1, from +1 to -1.
        e.g.
        0     -> motor 1 is stopped
        0.75  -> motor 1 moving forward at 75% power
        -0.5  -> motor 1 moving reverse at 50% power
        1     -> motor 1 moving forward at 100% power
        """        
        return self._getMotor(Command.GetD)

    motor1=property(getMotor1, setMotor1)
    motor2=property(getMotor2, setMotor2)
    motor3=property(getMotor3, setMotor3)
    motor4=property(getMotor4, setMotor4)
    
    def setLED(self, state):
        """
        setLED(state)
        Sets the current state of the LED, False for off, True for on
        """        
        level=Command.ValueOn if state else Command.ValueOff

        try: self._bus.write_byte_data(self._i2cAddress, Command.SetLED, level)
        except KeyboardInterrupt: raise
        except: self.print("Failed sending LED state!")

    def getLED(self):
        """
        state = getLED()
        Reads the current state of the LED, False for off, True for on
        """
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, Command.GetLED, I2C_NORM_LEN)
        except KeyboardInterrupt: raise
        except:
            self.print("Failed reading LED state!")
            return

        return False if i2cRecv[1]==Command.ValueOff else True

    led=property(getLED, setLED)

    def resetEPO(self):
        """
        resetEPO()
        Resets the EPO latch state, use to allow movement again after the EPO has been tripped
        """
        try: self._bus.write_byte_data(self._i2cAddress, Command.ResetEPO, 0)
        except KeyboardInterrupt: raise
        except: self.print("Failed resetting EPO!")

    def getEPO(self):
        """
        state = getEPO()
        Reads the system EPO latch state.
        If False the EPO has not been tripped, and movement is allowed.
        If True the EPO has been tripped, movement is disabled if the EPO is not ignored (see SetEpoIgnore)
            Movement can be re-enabled by calling ResetEpo.
        """
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, Command.GetEPO, I2C_NORM_LEN)
        except KeyboardInterrupt: raise
        except:
            self.print('Failed reading EPO ignore state!')
            return

        return False if i2cRecv[1]==Command.ValueOff else True

    def setEPOIgnore(self, state):
        """
        setEPOIgnore(state)
        Sets the system to ignore or use the EPO latch, set to False if you have an EPO switch, True if you do not
        """        
        level=Command.ValueOn if state else Command.ValueOff

        try: self._bus.write_byte_data(self._i2cAddress, Command.SetEPOIgnore, level)
        except KeyboardInterrupt: raise
        except: self.print("Failed sending EPO ignore state!")

    def getEPOIgnore(self):
        """
        state = getEPOIgnore()
        Reads the system EPO ignore state, False for using the EPO latch, True for ignoring the EPO latch
        """
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, Command.GetEPOIgnore, I2C_NORM_LEN)
        except KeyboardInterrupt: raise
        except:
            self.print("Failed reading EPO ignore state!")

        return False if i2cRecv[1]==Command.ValueOff else False

    epoIgnore=property(getEPOIgnore, setEPOIgnore)

    def hasNewIRMessage(self):
        """
        state = hasNewIRMessage()
        Reads the new IR message received flag.
        If False there has been no messages to the IR sensor since the last read.
        If True there has been a new IR message which can be read using GetIrMessage().
        """
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, Command.GetNewIR, I2C_NORM_LEN)
        except KeyboardInterrupt: raise
        except:
            self.print("Failed reading new IR message received flag!")
            return

        return False if i2cRecv[1]==Command.ValueOff else True

    def getIRMessage(self):
        """
        message = getIRMessage()
        Reads the last IR message which has been received and clears the new IR message received flag.
        Returns the bytes from the remote control as a hexadecimal string, e.g. 'F75AD5AA8000'
        Use HasNewIrMessage() to see if there has been a new IR message since the last call.
        """
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, Command.GetLastIR, I2C_LONG_LEN)
        except KeyboardInterrupt: raise
        except:
            self.print("Failed reading IR message")
            return

        message=''
        for i in range(IR_MAX_BYTES): message+='{:02X}'.format(i2cRecv[i+1])
        return message.rstrip('0')
            
    def setLEDIR(self, state):
        """
        setLEDIR(state)
        Sets if IR messages control the state of the LED, False for no effect, True for incoming messages blink the LED
        """
        level=Command.ValueOn if state else Command.ValueOff

        try: self._bus.write_byte_data(self._i2cAddress, Command.SetLEDIR, level)
        except KeyboardInterrupt: raise
        except: self.print("Failed sending LED state!")

    def getLEDIR(self):
        """
        state = getLEDIR()
        Reads if IR messages control the state of the LED, False for no effect, True for incoming messages blink the LED
        """
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, Command.GetLEDIR, I2C_NORM_LEN)
        except KeyboardInterrupt: raise
        except: 
            self.print("Failed reading LED state!")
            return

        return False if i2cRecv[1]==Command.ValueOff else True

    ledIR=property(getLEDIR, setLEDIR)

    def _getAnalog(self, analog):
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, analog, I2C_NORM_LEN)
        except KeyboardInterrupt: raise
        except:
            self.print("Failed reading analog level!")
            return

        raw=(i2cRecv[1]<<8)+i2cRecv[2]
        level=float(raw)/float(Command.AnalogMax)
        return level*3.3

    def getAnalog1(self):
        """
        voltage = getAnalog1()
        Reads the current analog level from port #1 (pin 2).
        Returns the value as a voltage based on the 3.3 V reference pin (pin 1).
        """
        return self._getAnalog(Command.GetAnalog1)

    def getAnalog2(self):
        """
        voltage = getAnalog2()
        Reads the current analog level from port #2 (pin 4).
        Returns the value as a voltage based on the 3.3 V reference pin (pin 1).
        """        
        return self._getAnalog(Command.GetAnalog2)

    def setCommsFailSafe(self, state):
        """
        setCommsFailsafe(state)
        Sets the system to enable or disable the communications failsafe
        The failsafe will turn the motors off unless it is commanded at least once every 1/4 of a second
        Set to True to enable this failsafe, set to False to disable this failsafe
        The failsafe is disabled at power on
        """
        level=Command.ValueOn if state else Command.ValueOff

        try: self._bus.write_byte_data(self._i2cAddress, Command.SetFailSafe, level)
        except KeyboardInterrupt: raise
        except: self.print("Failed sending communications failsafe state!")

    def getCommsFailSafe(self):
        """
        state = getCommsFailsafe()
        Read the current system state of the communications failsafe, True for enabled, False for disabled
        The failsafe will turn the motors off unless it is commanded at least once every 1/4 of a second
        """
        try: i2cRecv=self._bus.read_i2c_block_data(self._i2cAddress, Command.GetFailSafe, I2C_NORM_LEN)
        except KeyboardInterrupt: raise
        except:
            self.print("Failed reading communications failsafe state!")
            return

        return False if i2cRecv[1]==Command.ValueOff else True

    commsFailSafe=property(getCommsFailSafe, setCommsFailSafe)

    @classmethod
    def help(cls):
        """
        help()
        Displays the names and descriptions of the various functions and settings provided
        """
        flist=[cls.__dict__.get(a) for a in dir(cls) if isinstance(cls.__dict__.get(a), types.FunctionType)]
        flist=sorted(flist, key=lambda x: x.__code__.co_firstlineno)

        print(cls.__doc__)
        print()
        for f in flist:
            if f.__doc__==None: continue
            print("=== {} === {}".format(f.__name__, f.__doc__))


if __name__=="__main__":
    ZeroBorg.help()
    #zb=ZeroBorg()
    #zb.print("Testing ZeroBorg print()")
    #zb.init()
    