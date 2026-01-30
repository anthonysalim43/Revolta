from pymodbus.client import ModbusTcpClient
from pymodbus.client import ModbusSerialClient
from pymodbus import ModbusException
import time 
import json
import sys
#31011
import threading

from signals import (read_signal, write_signal,read_all_raw_signals)
from commands import (Device_Type,get_metric,bat_charge_discharge,max_bat_charge_discharge)
#from keepalivethread import(keepalive_worker)
from terminal_os import(key_pressed,clear_screen)
from keepalivethread import(keepalive_worker)



thread_state = {
  "battery_ctrl": False,
  "desired_power": 0.0,
  "stop": False,
  "period_s": 1.0,
}




def main():
    # ---------------------------------------------------------
    #  SMA Sunny Island — Read Device Type + Power Registers
    # s
    SB_IP   = "192.168.129.33" # IP address or SSH something for the sunny boy 
    VIC_IP   = "10.55.55.247"
    SI_IP   = "10.55.55.243"
    SI_PORT = 502



    PORT = "COM5"
    DEVICE_ID = 1
    BAUDRATE = 9600
    PARITY = "N"
    STOPBITS = 1
    TIMEOUT_S = 1.0

    client = ModbusSerialClient(
        port=PORT,
        baudrate=BAUDRATE,
        parity=PARITY,
        stopbits=STOPBITS,
        bytesize=8,
        timeout=TIMEOUT_S,
    )

    
    timeout_s =10 # we will choose a timeout of 30s and then we will keep refreshing it before the 30 s goes 
    SETPOINT_REFRESH_S = 1 # refresh the power setpoitt every 5 sec 
    while True:
        ModbusTCP= None
        inverter=input("Please choose a number for your Inverter choice :" \
        "\n Press 1 for SMA Sunny Boy Inverter" \
        "\n Press 2 for SMA Sunny Island Inverter" \
        "\n Press 3 for Victron Energy Multigrid II Inverter "\
        "\n Press 4 for Et340 "\
        "\n>")

        if inverter=="1":
            Inverter_name="SMA/SunnyBoy"
            IP_address=SB_IP
            ModbusTCP=True
            print("You chose SMA Sunny Boy Inverter")
            break

        elif inverter=="2":
            Inverter_name="SMA/SunnyIsland"
            IP_address=SI_IP
            ModbusTCP=True
            print("You chose SMA Sunny Island Inverter")
            break

        elif inverter=="3":
            Inverter_name="VictronEnergy/MultiGridII"
            IP_address=VIC_IP
            ModbusTCP=True
            print("You chose Victron Energy Multigrid II Inverter")
            break

        elif inverter =="4":
             Inverter_name="Et340"
             ModbusTCP=False
             print("You chose Et340")
             break
            
        else:
            print("You chose a wrong key, try again")
            continue
    
    
    with open("config.json") as file:
     cfg = json.load(file) # This way we loaded the json data inside the cfg

    dev = cfg["devices"][Inverter_name] # All invertuer should have name and unitid
    unit_id = dev["connection"]["unit_id"]
    signals = dev.get("signals", {})# it is better to use get , just in case if you write dev["signals"] and an invertuer does not have signals , it will break the code 
    derived = dev.get("derived", {})

    word_order=dev.get("word_order","msw_lsw")



    if ModbusTCP :
        client = ModbusTcpClient(IP_address, port=SI_PORT)
    elif not ModbusTCP:
        PORT = dev["connection"]["port"]
        BAUDRATE = dev["connection"]["baudrate"]
        PARITY = dev["connection"]["parity"]
        STOPBITS = dev["connection"]["stopbits"]
        BYTESIZE = dev["connection"]["bytesize"]
        TIMEOUT = dev["connection"]["timeout"]
        client = ModbusSerialClient(port=PORT,baudrate=BAUDRATE,parity=PARITY,stopbits=STOPBITS, bytesize=BYTESIZE,timeout=TIMEOUT)
    else:
        print("Couldnt Connect ")
    
    try :
        if not client.connect():
            raise RuntimeError("Could not connect to the inverter")
        print("Connected to the Inverter")

        t = threading.Thread(target=keepalive_worker, args=(client, signals, unit_id, word_order, thread_state), daemon=True)
        t.start()#Starting the thread 

        while True:
           

            print("\nMenu:")
            print("  1) Battery Charge/Discharge (W)")
            print("  2) Display current values")
            print("  3) Set Power fallout value ")
            print("  4) Max Battery Discharge")
            print("  5) ET340 data")
            print("  press 'q' to quit the programme")
            cmd = input("> ").strip()

            
            if cmd == "1":                

                bat_charge_discharge(client,signals,unit_id,word_order,thread_state)

            elif cmd == "2":
                while True:
                  
                    values = read_all_raw_signals(client, signals, unit_id,word_order)
                # Device_Type(values.get('device_type'))
                    
                    pv = get_metric("pv_power", signals, derived, values)
                    bat_charge=get_metric("bat_charge", signals, derived, values)
                    bat_discharge=get_metric("bat_discharge", signals, derived, values)
                    grid_power=get_metric("grid_power",signals,derived,values)
                    power_setpoint_timeout=get_metric("power_setpoint_timeout",signals,derived,values)
                    bat_size_wh=get_metric("bat_size_Wh",signals,derived,values)
                #   if battery_charge_status != None :
                #      print(f"Battery Charging: {bat_charge} W")
                #    if battery_discharge_status != None :
                #      print(f"Battery Discharging: -{battery_discharge} W")
                    clear_screen()
                    print(">Live data of the inverteur , please press 9 if you want to stop" )
                    print(f"Battery size: {bat_size_wh} Wh ")#7968 Wh
                    print(f"Timeout setpoint after {power_setpoint_timeout} s")
                    print(f"PV Power Generated: {pv} W") 
                    print(f"Grid Power: {grid_power} W")
                    print(f"Battery Charging: {bat_charge} W")
                    print(f"Battery Discharging: -{bat_discharge} W")
                    #time.sleep(0.5)#pause for a second,reading frequency 1 Hz
                    k=key_pressed()
                    if k=="9":
                        break
                    time.sleep(0.1)#pause for a second,reading frequency 1 Hz

            
                    
            elif cmd=="3":
                fallback_value  = signals.get("power_setpoint_fallback_value")
                if fallback_value is None :
                    print("Setpoint not available for this inverter (missing in JSON).")
                    continue
                try:
                    
                    value = float(input("choose the power fallback 2").strip())
                    write_signal(client, fallback_value , unit_id, value,word_order)
                except Exception as e:
                    print(f"Write failed: {e}")

            elif cmd=="4":
                if max_bat_charge_discharge(client,signals,unit_id,word_order):
                    print("Battery max current charge/discharge was changed Succesfully !")
                
                else:
                    print("Failed to change the maximum battery charge/discharge ")

                
            
            elif cmd =="5":
                 
                 while True:
                  
                    values = read_all_raw_signals(client, signals, unit_id,word_order)
                # Device_Type(values.get('device_type'))
                    
                    v1 = get_metric("grid_voltage_L1", signals, derived, values)
                    i1=get_metric("grid_current_L1", signals, derived, values)
                    power=get_metric("grid_active_power_W", signals, derived, values)
                  
                    clear_screen()
                    print(">Live data of the inverteur , please press 9 if you want to stop" )
                    print(f"voltage: {v1} V ")#7968 Wh
                    print(f"current {i1} A")
                    print(f"Power {power} W") 
                    k=key_pressed()
                    if k=="9":
                        break
                    time.sleep(0.1)#pause for a second,reading frequency 1 Hz


            elif cmd == "q":
                print("Thank you goodbye.")
                keepalive_stop = True
                time.sleep(0.1)  # allow thread to exit

                break

            else:
                print("Invalid option.")

    except KeyboardInterrupt:
        print("\nStopping on user request (Ctrl+C).")
    except (ModbusException, OSError) as e:
        print("Communication error:", e)
    finally:
        client.close()
    print("Modbus client closed.")




if __name__ == "__main__":
    main()    