from pymodbus.client import ModbusSerialClient
from pymodbus import ModbusException
import time, json, os
from pymodbus.client import ModbusTcpClient
# --------------------------
# Helpers (same spirit as yours)
# --------------------------



def main():
    




    #192.168.1.129


    client = ModbusTcpClient("192.168.1.129", port=502, timeout=2)
    client.connect()

    unit_id = 1  # inverter RTU slave id behind the gateway
    res = client.read_holding_registers(address=0, count=1, slave=unit_id)
    print(res.registers if not res.isError() else res)



if __name__ == "__main__":
    main()
