from pymodbus.client import ModbusTcpClient
from pymodbus import ModbusException
import time 
import json
import os 


def Device_Type(cfg_signal,client, unit_id):
  
  device_type_signal = cfg_signal["device_type"]
  dev_code=read_signal(client,device_type_signal,unit_id)
  dev_map = {
    9331: "Sunny Island 3.0M-12",
    9332: "Sunny Island 4.4M-12",
    9333: "Sunny Island 6.0H-12",
    9334: "Sunny Island 8.0H-12",
    9474: "Sunny Island 4.4M-13",
    9475: "Sunny Island 6.0H-13",
    9476: "Sunny Island 8.0H-13",
    9486: "Sunny Island 5.0H-13",
    
    19084:"Sunny Boy Smart Energy 7.7-US",
    19085:"Sunny Boy Smart Energy 6.0",
    19086:"Sunny Boy Smart Energy 5.8-US",
    19087:"Sunny Boy Smart Energy 4.8-US",
    19088:"Sunny Boy Smart Energy 3.8-US",
    19128:"Sunny Boy Smart Energy 3.6",
    19129:"Sunny Boy Smart Energy 4.0",
    19130:"Sunny Boy Smart Energy 5.0"
  }

  print("Inverter Detected:", dev_map.get(dev_code, "Unknown"))



def Battery_Charge(cfg_signal,client, unit_id):
    battery_charge_signal = cfg_signal["bat_charge"]
    value=read_signal(client,battery_charge_signal,unit_id)

    if value > 0:
        status="Charging"
    else:
        status= None 
    
    return value,status

def Battery_Discharge(cfg_signal,client, unit_id):
    battery_discharge_signal = cfg_signal["bat_discharge"]
    value=read_signal(client,battery_discharge_signal,unit_id)

    if value > 0:
        status="Discharging"
    else:
        status= None 

    return value,status



def Inverteur_AC_Power(cfg_signal,client, unit_id):#It will return the value in watt , if the value is not in watt it will change it and put it in watt and return it 
    inverteur_ac_power_signal = cfg_signal["inverteur_ac_power"]# this will tell me to get the data pv_ac_power from json
    value=read_signal(client,inverteur_ac_power_signal,unit_id)


    return value


def read_signal(client, sig, unit_id):
    ref   = sig["ref"]
    fc    = sig["fc"]
    dtype = sig["dtype"]
    scale = sig.get("scale", 1)

    number_register=0

    if dtype in ("u16","s16"):
       number_register=1
    elif dtype in ("u32","s32"):
       number_register=2
    elif dtype in ("u64","s64"):
       number_register=4
    

    if number_register == 0:
     raise ValueError(f"Unsupported dtype: {dtype}")

        

    if fc == 4:
        res = client.read_input_registers(ref, count=number_register, device_id=unit_id)
    elif fc == 3:
        res = client.read_holding_registers(ref, count=number_register, device_id=unit_id)
    elif fc == 1:
        res = client.read_coils(ref, 1, device_id=unit_id)#coil is always one register 
    else:
        raise ValueError(f"Unsupported FC {fc}")

    if res.isError():
        raise RuntimeError(res)


    if dtype == "s16":
        v = res.registers[0]
        if v >= 0x8000:
            v -= 0x10000
        return v * scale

    elif dtype == "u16":
        return res.registers[0] * scale

    elif dtype == "s32":
        hi, lo = res.registers
        raw = (hi << 16) | lo
        if raw >= 0x80000000:
            raw -= 0x100000000
        return raw * scale

    elif dtype == "u32":
        hi, lo = res.registers
        return ((hi << 16) | lo) * scale

    elif dtype == "s64":
        r0, r1, r2, r3 = res.registers
        raw = (r0 << 48) | (r1 << 32) | (r2 << 16) | r3
        if raw >= 0x8000000000000000:
            raw -= 0x10000000000000000
        return raw * scale

    else:
        raise ValueError(f"Unsupported dtype: {dtype}")
   
    
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")