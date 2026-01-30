
from signals import read_signal, write_signal

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




def get_metric(name, signals, derived, values):
   
    #Some metric will be directly in the signal , like PV power in Sunny Island
    #Some will need to be calculated like PV power in Sunny Boy
    #If the signal already exist it will just return the valeue  from the signal 
    #If not , how to calcualte it is in the json , it will check how and calcualte the value 
    sig=signals.get(name)
    if sig is not None and "read" in sig:
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

def bat_charge_discharge(client,signals,unit_id,word_order,state):
                
    wm_mode = signals["wm_mode_cfg"]
    en = signals["enable_power_exchange"]
    sp = signals["power_setpoint"]
    timeout=signals["power_setpoint_timeout"]
    apply_fallback=signals["power_setpoint_fallback"]

    bat_voltage=read_signal(client, signals["bat_voltage"], unit_id,word_order)
    max_charge_current=read_signal(client, signals["max_charge_current_A"], unit_id,word_order)  
    max_discharge_current=read_signal(client, signals["max_discharge_current_A"], unit_id,word_order)
    
    try:
        write_signal(client, en, unit_id, 802,word_order)# According to doc , 802 mean active , 803 mean Inactive power setpoint
        print("Power control is enabled")
    except Exception as e:
        print(f"Enable Power control failed: {e}")
        return 

    # Ask setpoint
    try:
        while True :
            
            bat_voltage=read_signal(client, signals["bat_voltage"], unit_id,word_order)
            max_charge_current=read_signal(client, signals["max_charge_current_A"], unit_id,word_order)  
            max_discharge_current=read_signal(client, signals["max_discharge_current_A"], unit_id,word_order)
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
                    if max_bat_charge_discharge(client,signals,unit_id,word_order):
                        print("Battery max current charge/discharge was changed Succesfully !")
                        continue#We will go back to the user to press the power charging discharging button 
                                # if we choose to forward in the code and not let the user choose the value again make sure you check if the new value is inside the allowed value
    
                    else:
                        print("Failed to change the maximum battery charge/discharge ")
                elif cmd=="3" :
                    break
                else :
                    print("Invalid option.") 
                

           
            state["desired_power"] = value
            state["battery_ctrl"] = True

            print("Charging/Discharging ")
            write_signal(client, wm_mode, unit_id, 1079,word_order)
            write_signal(client,timeout,unit_id,10,word_order)
            write_signal(client, sp, unit_id, state["desired_power"],word_order)
            write_signal(client, apply_fallback, unit_id, 2507,word_order)
            break
        #     k=key_pressed()
            #   if k=="9":
            #     break
    except Exception as e:
        print(f"Write failed: {e}")




def max_bat_charge_discharge(client,signals,unit_id,word_order): 
        
        max_charge_current=read_signal(client, signals["max_charge_current_A"], unit_id,word_order)  
        max_discharge_current=read_signal(client, signals["max_discharge_current_A"], unit_id,word_order) 
        if  max_charge_current is None or max_discharge_current is None :
            print("Setpoint not available for this inverter (missing in JSON).")
            return  False  

        print(f"Maximum Battery Charge current: {max_charge_current} A | Maximum Battery Discharge current: {max_discharge_current} A")
        
        print("\nMenu:")
        print("  1) Change Maximum Battery Charge current ")
        print("  2) Change Maximum Battery DisCharge current")
        print("      Press any other  Button to go back to Main Menu")
        cmd = input("> ").strip()
        if cmd=="1":
            value_max_charge_current_A=signals["max_charge_current_A"]
            try:
                value = float(input("choose the maximum battery charge current in A").strip())
                write_signal(client, value_max_charge_current_A, unit_id, value,word_order)
                return True
            except Exception as e:
                print(f"Write failed: {e}")
                return  False 
        elif cmd=="2":
            value_max_discharge_current_A=signals["max_discharge_current_A"]

            try:
                value = float(input("choose the maximum battery discharge value in A").strip())
                write_signal(client, value_max_discharge_current_A, unit_id, value,word_order)
                return True 
            except Exception as e:
                print(f"Write failed: {e}")
                return  False 
        else:
            return False
       
