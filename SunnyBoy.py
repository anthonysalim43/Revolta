from pymodbus.client import ModbusTcpClient
from pymodbus import ModbusException
import time 
import json
import os 
import sys
#31011
import threading

# Global variable 
battery_ctrl = False
desired_power = 0.0
keepalive_stop = False
keepalive_period_s = 1.0  


def keepalive_worker(client, signals, unit_id):
    global battery_ctrl, desired_power, keepalive_stop, keepalive_period_s

    last_tx = 0.0
    while not keepalive_stop:
        try:
            
            if battery_ctrl:
                
                now = time.time()
                if now - last_tx >= keepalive_period_s:
                    
                    write_signal(client, signals["power_setpoint"], unit_id, desired_power)
                    last_tx = now
        except Exception as e:
            # Don't crash the thread; just report and keep trying
            print(f"\n[keepalive] write failed: {e}")

        time.sleep(0.1)  # small sleep so CPU doesnt burn



def key_pressed():
    if os.name == "nt":
        # for window user
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getwch()
        return None
    else:
        # for linux
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setcbreak(fd)  # non-blocking, no Enter needed
            rlist, _, _ = select.select([sys.stdin], [], [], 0)
            if rlist:
                return sys.stdin.read(1)
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)



def Device_Type(dev_code):
  
  
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



def write_signal(client,sig,unit_id, value):



     #"enable_power_exchange": { "ref": 40151, "fc": 16, "dtype": "u32", "scale": 1, "unit": "","access":"w" }
    ref   = sig["ref"]
    fc    = sig["fc"]
    dtype = sig["dtype"]
    scale = sig.get("scale", 1)

    number_register=0

    if dtype in ("u16","s16"):
       number_register=1
    elif dtype in ("u32","s32"):
       number_register=2
    #elif dtype in ("u64","s64"):
    #   number_register=4
    

    if number_register == 0:
     raise ValueError(f"Unsupported dtype: {dtype}")

        

   

    #First you need to check the value you are writting is in the range , for exempele:
    #for u16, value should be from 0 to 65535(0xFFFF)
    if dtype == "u16":
        value=int(round(value*scale))
        if not (0<=value<=0xFFFF):
            raise ValueError(f"value {value} is out of range of u16")
      
       
        reg=value

    elif dtype == "s16":
       value=int(round(value*scale))
       if not (-0x8000<=value<=0x7FFF):
            raise ValueError(f"value {value} is out of range of s16")
       
       
       if value<0:
           value+=0x10000
           
       reg=value
       
    elif dtype == "u32":
        value=int(round(value*scale))
        if not (0<=value<=0xFFFFFFFF):
            raise ValueError(f"value {value} is out of range of u32")
        

        hi=(value>>16 ) & 0xFFFF
        lo=value & 0xFFFF
        reg=[hi,lo]
    elif dtype == "s32":
        value=int(round(value*scale))
        
        if not (-0x80000000<=value<=0x7FFFFFFF):
            raise ValueError(f"value {value} is out of range of s32")
        

        if value<0:
            value+=0x100000000

        hi=(value>>16 ) & 0xFFFF
        lo=value & 0xFFFF
        reg=[hi,lo]
        
    else:
        raise ValueError(f"Unsupported dtype: {dtype}")

      
    if fc == 6:
        if isinstance(reg, list):
          raise ValueError("Value should be an integer and not a list with FC=6")
        res = client.write_register(ref, reg, device_id=unit_id)

    elif fc == 16:
        if not isinstance(reg, list):
            reg = [reg]# this line just double check if it is a list/array or not ,because write registers require a list not a single value
        
        res = client.write_registers(ref, reg, device_id=unit_id)

    else:
        raise ValueError(f"Unsupported FC {fc}")

    if res.isError():
        raise RuntimeError(res)
    

def read_signal(client, sig, unit_id):

    #sig will come of the format sig  = { "ref": 31395, "fc": 4, "dtype": "s32", "unit": "W" }
    #This function will get the addresse reference , fetch it using the function code fc , decode it depending on type and scale it 
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
        return v / scale

    elif dtype == "u16":
        return res.registers[0] / scale

    elif dtype == "s32":
        hi, lo = res.registers
        raw = (hi << 16) | lo
        if raw >= 0x80000000:
            raw -= 0x100000000
        return raw / scale

    elif dtype == "u32":
        hi, lo = res.registers
        return ((hi << 16) | lo) / scale

    elif dtype == "s64":
        r0, r1, r2, r3 = res.registers
        raw = (r0 << 48) | (r1 << 32) | (r2 << 16) | r3
        if raw >= 0x8000000000000000:
            raw -= 0x10000000000000000
        return raw / scale
    
    elif dtype == "u64":
        r0, r1, r2, r3 = res.registers
        raw = (r0 << 48) | (r1 << 32) | (r2 << 16) | r3
        return raw / scale


    else:
        raise ValueError(f"Unsupported dtype: {dtype}")
   

def get_metric(name, signals, derived, values):
   
    #Some metric will be directly in the signal , like PV power in Sunny Island
    #Some will need to be calculated like PV power in Sunny Boy
    #If the signal already exist it will just return the valeue  from the signal 
    #If not , how to calcualte it is in the json , it will check how and calcualte the value 

    if name in signals:
        return values.get(name)#metric exist in signal

    
    d = derived.get(name) #Metric not in signal and need to be derived 
  
    if not d: #Metric is neither in signal or derived , it does not exist just return nothing 
        return None


     
    #exemple Layout of derived if name = pv_power:
    # "pv_power": { "expr": "inverter_ac_power - bat_discharge", "unit": "W" }
      
    expr = d["expr"]# This will result the string "inverter_ac_power -bat_discharge "

    try:#Now we need to trasnform the string text formula to a real math formula  using eval 
        return eval(expr, {"__builtins__": {}}, values) # eval calcualte a string formula
                # It will get the variable , and fetch there value inside of values 
                #(it is all the value from the signal thet get all the metric, we already got it before from read_all_metric and passed it here as parameter , we have list of all value ) 
                #this will do inverter_ac_power - bat_discharge
                #{"__builtins__": {}} is just a precaution to disable all python built in function , in case in the jason you wrote a function instead of variable and operator 
                
    except NameError as e:#In case there is a typo inside the JSON file i dont want my file to crash
        print(f"Cannot compute '{name}': {e}")
        return None




def read_all_raw_signals(client, signals, unit_id):
    
    #This will loop over all signal
    #Each Signal  for exemple "bat_discharge":     { "ref": 31395, "fc": 4, "dtype": "s32", "unit": "W" }
    # It will put the "bat_discharge" as the name , and the {"ref:31395,"fc":4 ...} as the sig :
        #name = "bat_discharge"
        #sig  = { "ref": 31395, "fc": 4, "dtype": "s32", "unit": "W" }
    # then we have the all the info of the signal in sig , it will go to read_signal, fetch the signal value and decode it 
    # It will finaly save the value in values[bat_discharge]
        #values = {
        #"bat_discharge": 1200,
        #"inverter_ac_power": 4200,
        #...
        #}

    values = {}
    for name, sig in signals.items():

        access=sig.get("access")
        if access not in ("r", "rw"):
            continue 
        
        values[name] = read_signal(client, sig, unit_id)

    return values


def max_bat_charge_discharge(client,signals,unit_id): 
        
        max_charge_current=read_signal(client, signals["max_charge_current_A_read"], unit_id)  
        max_discharge_current=read_signal(client, signals["max_discharge_current_A_read"], unit_id) 
        if not max_charge_current or not max_discharge_current :
            print("Setpoint not available for this inverter (missing in JSON).")
            return  False  

        print(f"Maximum Battery Charge current: {max_charge_current} A | Maximum Battery Discharge current: {max_discharge_current} A")
        
        print("\nMenu:")
        print("  1) Change Maximum Battery Charge current ")
        print("  2) Change Maximum Battery DisCharge current")
        print("      Press any other  Button to go back to Main Menu")
        cmd = input("> ").strip()
        if cmd=="1":
            value_max_charge_current_A=signals.get("max_charge_current_A_write")
            try:
                value = float(input("choose the maximum battery charge current in A").strip())
                write_signal(client, value_max_charge_current_A, unit_id, value)
                return True
            except Exception as e:
                print(f"Write failed: {e}")
                return  False 
        elif cmd=="2":
            value_max_discharge_current_A=signals.get("max_discharge_current_A_write")

            try:
                value = float(input("choose the maximum battery discharge value in A").strip())
                write_signal(client, value_max_discharge_current_A, unit_id, value)
                return True 
            except Exception as e:
                print(f"Write failed: {e}")
                return  False 
        else:
            return False
       

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def main():
    global battery_ctrl, desired_power, keepalive_stop, keepalive_period_s

    # ---------------------------------------------------------
    #  SMA Sunny Island — Read Device Type + Power Registers
    # s
    SB_IP   = "192.168.129.33" # IP address or SSH something for the sunny boy 
    VIC_IP   = "10.55.55.247"
    SI_IP   = "10.55.55.243"
    SI_PORT = 502

    timeout_s =10 # we will choose a timeout of 30s and then we will keep refreshing it before the 30 s goes 
    SETPOINT_REFRESH_S = 1 # refresh the power setpoitt every 5 sec 
    while True:
        inverter=input("Please choose a number for your Inverter choice :" \
        "\n Press 1 for SMA Sunny Boy Inverter" \
        "\n Press 2 for SMA Sunny Island Inverter" \
        "\n Press 3 for Victron Energy Multigrid II Inverter "\
        "\n>")

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

   

    client = ModbusTcpClient(IP_address, port=SI_PORT)
 
    try :
        if not client.connect():
            raise RuntimeError("Could not connect to the inverter")
        print("Connected to the Inverter")

        t = threading.Thread(target=keepalive_worker, args=(client, signals, unit_id), daemon=True)
        t.start()#Starting the thread of 

        while True:
           

            print("\nMenu:")
            print("  1) Battery Charge/Discharge (W)")
            print("  2) Display current values")
            print("  4) Set Power fallout value ")
            print("  5) Max Battery Discharge")
            print("  press 'q' to quit the programme")
            cmd = input("> ").strip()


            if cmd == "1":
                wm_mode = signals.get("wm_mode_cfg")
                en = signals.get("enable_power_exchange")
                sp = signals.get("power_setpoint")
                timeout=signals.get("power_setpoint_timeout_set")
                apply_fallback=signals.get("power_setpoint_fallback_enable")

                bat_voltage=read_signal(client, signals["bat_voltage"], unit_id)
                max_charge_current=read_signal(client, signals["max_charge_current_A_read"], unit_id)  
                max_discharge_current=read_signal(client, signals["max_discharge_current_A_read"], unit_id)
                if not en or not sp:
                    print("Setpoint not available for this inverter (missing in JSON).")
                    continue

                try:
                    write_signal(client, en, unit_id, 802)# According to doc , 802 mean active , 803 mean Inactive power setpoint
                    print("Power control is enabled")
                except Exception as e:
                    print(f"Enable failed: {e}")
                    continue

                # Ask setpoint
                try:
                    while True :
                       
                        bat_voltage=read_signal(client, signals["bat_voltage"], unit_id)
                        max_charge_current=read_signal(client, signals["max_charge_current_A_read"], unit_id)  
                        max_discharge_current=read_signal(client, signals["max_discharge_current_A_read"], unit_id)
                        value = float(input("Enter Battery Charge/Discharge value in W ").strip())
                    

                        bat_current = value/bat_voltage
                        max_discharge_power=bat_voltage * max_discharge_current
                        max_charge_power=bat_voltage*max_charge_current

                        if bat_current > max_discharge_current or  bat_current < -max_charge_current:
                        
                            print("Chargin/Discharge is outside the current limite\n")
                            print(f"Max Charge current: {max_charge_current} A | Max charge power:-{max_charge_power}\n" )
                            print(f"Max Discharge current: {max_discharge_current} A  | Max discharge power:{max_discharge_power}\n")

                            print("\nMenu:")
                            print("  1) Choose another Charging/Discharging Power")
                            print("  2) Change battery max Charge/Discharge current")
                            print("  3) Go back to Main menu")
                            cmd = input("> ").strip()    

                            if cmd=="1" :
                                continue

                            elif cmd=="2":
                                if max_bat_charge_discharge(client,signals,unit_id):
                                    print("Battery max current charge/discharge was changed Succesfully !")
                                    continue#We will go back to the user to press the power charging discharging button 
                                            # if we choose to forward in the code and not let the user choose the value again make sure you check if the new value is inside the allowed value
                
                                else:
                                    print("Failed to change the maximum battery charge/discharge ")
                            elif cmd=="3" :
                                break
                            else :
                                print("Invalid option.") 
                            

                        battery_ctrl=True
                        desired_power=value
                        print("Charging/Discharging ")
                        write_signal(client, wm_mode, unit_id, 1079)
                        write_signal(client,timeout,unit_id,10)
                        write_signal(client, sp, unit_id, desired_power)
                        write_signal(client, apply_fallback, unit_id, 2507 )
                        break
                    #     k=key_pressed()
                        #   if k=="9":
                        #     break
                except Exception as e:
                    print(f"Write failed: {e}")
            elif cmd=="4":
                power_setpoint_fallback_value_write = signals.get("power_setpoint_fallback_value_write")
                if not power_setpoint_fallback_value_write:
                    print("Setpoint not available for this inverter (missing in JSON).")
                    continue
                try:
                    
                    value = float(input("choose the power fallback 2").strip())
                    write_signal(client, power_setpoint_fallback_value_write, unit_id, value)
                except Exception as e:
                    print(f"Write failed: {e}")

            elif cmd=="5":
                if max_bat_charge_discharge(client,signals,unit_id):
                    print("Battery max current charge/discharge was changed Succesfully !")
                
                else:
                    print("Failed to change the maximum battery charge/discharge ")

                
            

            elif cmd == "2":
                while True:
                  
                    values = read_all_raw_signals(client, signals, unit_id)
                # Device_Type(values.get('device_type'))
                    
                    pv = get_metric("pv_power", signals, derived, values)
                    bat_charge=get_metric("bat_charge", signals, derived, values)
                    bat_discharge=get_metric("bat_discharge", signals, derived, values)
                    grid_power=get_metric("grid_power",signals,derived,values)
                    power_setpoint_timeout=get_metric("power_setpoint_timeout",signals,derived,values)
                    power_setpoint_fallback=get_metric("power_setpoint_fallback_value_read",signals,derived,values)
                #   if battery_charge_status != None :
                #      print(f"Battery Charging: {bat_charge} W")
                #    if battery_discharge_status != None :
                #      print(f"Battery Discharging: -{battery_discharge} W")
                    clear_screen()
                    print(">Live data of the inverteur , please press 9 if you want to stop" )
                    print(f"Power setpoint fallback behavior: {power_setpoint_fallback} ")
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