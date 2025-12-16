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


def PV_Power_Generated(cfg_signal,client, unit_id,Inverter_name):


    if Inverter_name=="SMA/SunnyBoy":

        inverteur_ac_power=Inverteur_AC_Power(cfg_signal,client, unit_id)
        battery_charge,_=Battery_Charge(cfg_signal,client, unit_id) 
        battery_discharge,_=Battery_Discharge(cfg_signal,client, unit_id) 
        value= inverteur_ac_power + battery_charge - battery_discharge
        return value

    
    elif Inverter_name=="SMA/SunnyIsland":
        pv_power_generated_signal = cfg_signal["pv_power_generated"]
        value=read_signal(client,pv_power_generated_signal,unit_id)
        return value


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

def main():
    # ---------------------------------------------------------
    #  SMA Sunny Island — Read Device Type + Power Registers
    # s
    SB_IP   = "192.168.129.33" # IP address or SSH something for the sunny boy 
    VIC_IP   = "10.55.55.247"
    SI_IP   = "10.55.55.243"
    SI_PORT = 502
   
    while True:
        inverter=input("Please choose a number for your Inverter choice :" \
        "\n Press 1 for SMA Sunny Boy Inverter" \
        "\n Press 2 for SMA Sunny Island Inverter" \
        "\n Press 3 for Victron Energy Multigrid II Inverter\n")

        if inverter=="1":
            Inverter_name="SMA/SunnyBoy"
            IP_address=SB_IP
            print("You chose SMA Sunny Boy Inverter")
            break

        elif inverter=="2":
            Inverter_name="SMA/SunnyIsland"
            IP_address=SI_IP
            print("You chose SMA Sunny Island Inverter")
            break

        elif inverter=="3":
            Inverter_name="VictronEnergy/MultiGridII"
            IP_address=VIC_IP
            print("You chose Victron Energy Multigrid II Inverter")
            
        else:
            print("You chose a wrong key, try again")
            continue
    
    
    with open("config.json") as file:
     cfg = json.load(file) # This way we loaded the json data inside the cfg

    cfg_signal=cfg["devices"][Inverter_name]["signals"]
    unit_id=cfg["devices"][Inverter_name]["connection"]["unit_id"]
   

    client = ModbusTcpClient(IP_address, port=SI_PORT)
    try :
        if not client.connect():
            raise RuntimeError("Could not connect to the inverter")
        print("Connected to the Inverter")



        while True:
            clear_screen()
            Device_Type(cfg_signal,client, unit_id)
            pv_power_generated=PV_Power_Generated(cfg_signal,client, unit_id,Inverter_name)
            battery_charge,battery_charge_status=Battery_Charge(cfg_signal,client, unit_id) 
            battery_discharge,battery_discharge_status=Battery_Discharge(cfg_signal,client, unit_id) 
           


        #   if battery_charge_status != None :
        #      print(f"Battery Charging: {battery_charge} W")
        #    if battery_discharge_status != None :
        #      print(f"Battery Discharging: -{battery_discharge} W")

            print(f"PV Power Generated: {pv_power_generated} W") 
            print(f"Battery Charging: {battery_charge} W")
            print(f"Battery Discharging: -{battery_discharge} W")
            time.sleep(0.5)#pause for a second,reading frequency 1 Hz


    except KeyboardInterrupt:
        print("\nStopping on user request (Ctrl+C).")
    except (ModbusException, OSError) as e:
        print("Communication error:", e)
    finally:
        client.close()
    print("Modbus client closed.")




if __name__ == "__main__":
    main()    