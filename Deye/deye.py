from pymodbus.client import ModbusSerialClient
from pymodbus import ModbusException
import time, json, os

# --------------------------
# Helpers (same spirit as yours)
# --------------------------

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")#Linux vs window



def write_signal(client,sig,unit_id, value,word_order):


    if "write" not in sig:
        raise KeyError(f"Signal is not a writting block: {sig}")
    #"enable_power_exchange": { "ref": 40151, "fc": 16, "dtype": "u32", "scale": 1, "unit": "","access":"w" }
    w=sig["write"]
    ref   = w["ref"]
    fc    = w["fc"]
    dtype = w["dtype"]
    scale = w.get("scale", 1)

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

        if word_order=="msw_lsw":
            reg=[hi,lo]
        elif word_order=="lsw_msw":
            reg=[lo,hi]
        else: 
            raise ValueError(f"Unsupported word_order: {word_order}")
        
    elif dtype == "s32":
        value=int(round(value*scale))
        
        if not (-0x80000000<=value<=0x7FFFFFFF):
            raise ValueError(f"value {value} is out of range of s32")
        

        if value<0:
            value+=0x100000000

        hi=(value>>16 ) & 0xFFFF
        lo=value & 0xFFFF
        if word_order=="msw_lsw":
            reg=[hi,lo]
        elif word_order=="lsw_msw":
            reg=[lo,hi]
        else: 
            raise ValueError(f"Unsupported word_order: {word_order}")
        
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
    

def read_signal(client, sig, unit_id,word_order):

    #sig will come of the format sig  = { "ref": 31395, "fc": 4, "dtype": "s32", "unit": "W" }
    #This function will get the addresse reference , fetch it using the function code fc , decode it depending on type and scale it 
    if "read" not in sig:
        raise KeyError(f"Signal is not a read signal: {sig}")
    
    r=sig["read"]
    ref   = r["ref"]
    fc    = r["fc"]
    dtype = r["dtype"]
    scale = r.get("scale", 1)
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



    regs = res.registers
    if dtype == "s16":
        v = regs[0]
        if v >= 0x8000:
            v -= 0x10000
        return v / scale

    elif dtype == "u16":
        return regs[0] / scale

    elif dtype == "s32":

        if word_order =="msw_lsw":
            hi, lo = regs[0],regs[1]

        elif word_order =="lsw_msw":
            lo,hi =regs[0],regs[1]
        else:
            raise ValueError(f"Unsupported word_order: {word_order}")
        raw = (hi << 16) | lo
        if raw >= 0x80000000:
            raw -= 0x100000000
        return raw / scale

    elif dtype == "u32":

        if word_order =="msw_lsw":
            hi, lo = regs[0],regs[1]

        elif word_order =="lsw_msw":
            lo,hi =regs[0],regs[1]
        else:
            raise ValueError(f"Unsupported word_order: {word_order}")
        return ((hi << 16) | lo) / scale

    elif dtype == "s64":

        if word_order =="msw_lsw":
           r0, r1, r2, r3 =regs[0],regs[1],regs[2],regs[3]

        elif word_order =="lsw_msw":
            r0,r1,r2,r3 =regs[3],regs[2],regs[1],regs[0]
        else:
            raise ValueError(f"Unsupported word_order: {word_order}")
        raw = (r0 << 48) | (r1 << 32) | (r2 << 16) | r3
        if raw >= 0x8000000000000000:
            raw -= 0x10000000000000000
        return raw / scale
    
    elif dtype == "u64":

        if word_order =="msw_lsw":
           r0, r1, r2, r3 =regs[0],regs[1],regs[2],regs[3]

        elif word_order =="lsw_msw":
            r0,r1,r2,r3 =regs[3],regs[2],regs[1],regs[0]
        else:
            raise ValueError(f"Unsupported word_order: {word_order}")
        raw = (r0 << 48) | (r1 << 32) | (r2 << 16) | r3
        return raw / scale


    else:
        raise ValueError(f"Unsupported dtype: {dtype}")
   


def read_all_raw_signals(client, signals, unit_id,word_order):
    
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

        if "read" not in sig:
            continue 
        
        values[name] = read_signal(client, sig, unit_id,word_order)

    return values

def get_metric(name, signals, derived, values):
    if name in signals:
        return values.get(name)
    d = derived.get(name)
    if not d:
        return None
    expr = d["expr"]
    return eval(expr, {"__builtins__": {}}, values)

# --------------------------
# Deye-specific helpers
# --------------------------

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
    19130:"Sunny Boy Smart Energy 5.0",

     # For the Deye Sun
    512: "String Machine Inverteur",#0x0200
    1024:" Single phase energy storage machine hybrid",#0x0400
    1280:"low voltage three-phase energy storage machine phase3 hybird",#0x0500
    1536:"High-voltage three-phase energy storage machine 6-15kw",#0x0600
    1537:"High-voltage three-phase energy storage machine 20-50kw"#0x0601
  }

  print("Inverter Detected:", dev_map.get(dev_code, "Unknown"))



def hhmm_to_u16(hhmm: str) -> int:
    # "23:59" or "2359" -> 2359
    hhmm = hhmm.replace(":", "").strip()
    if len(hhmm) != 4:
        raise ValueError("Time must be HHMM (e.g. 0830)")
    hh = int(hhmm[:2]); mm = int(hhmm[2:])
    if not (0 <= hh <= 23 and 0 <= mm <= 59):
        raise ValueError("Invalid time")
    return hh * 100 + mm





def logging_configuration(
    client,
    signals: dict,
    unit_id: int,
    word_order: str,
    out_dir: str = "logs",
    filename_prefix: str = "deye_config_snapshot",
    hv_power_lsb_w: int = 10,   # HV often uses 10 W/LSB for some power limit regs
):
    """
    Read and log the current configuration registers, print them, and save to a JSON file.
    Returns: (snapshot_dict, filepath)
    """

    # Remove duplicates while keeping order
    list_setting = [
        "tou_time1","tou_time2","tou_time3","tou_time4","tou_time5","tou_time6",
        "tou_bat_pwr1","tou_bat_pwr2","tou_bat_pwr3","tou_bat_pwr4","tou_bat_pwr5","tou_bat_pwr6",
        "tou_soc1",
        "mains_charging_enable","tou_charge_en1","grid_check_ct_meter",
        "selling_elec_enable","PV_selling_enable","tou_selling_en",
        "max_PV_sell_pwr","max_sell_power",
        "max_bat_charge_current_A","max_bat_discharge_current_A","max_grid_charge_current_A",
    ]
    seen = set()
    list_setting = [k for k in list_setting if not (k in seen or seen.add(k))]

    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(out_dir, f"{filename_prefix}_{ts}.json")

    snapshot = {
        "timestamp": ts,
        "unit_id": unit_id,
        "word_order": word_order,
        "settings": {}
    }

    print("\n=== Configuration snapshot ===")
    for key in list_setting:
        sig = signals.get(key)
        if sig is None:
            print(f"[MISSING] {key} is not defined in config.json")
            snapshot["settings"][key] = {"status": "missing_in_config"}
            continue

        if "read" not in sig:
            print(f"[NO READ] {key} has no read definition")
            snapshot["settings"][key] = {"status": "no_read_access"}
            continue

        r = sig["read"]
        meta = {
            "ref": r.get("ref"),
            "fc": r.get("fc"),
            "dtype": r.get("dtype"),
            "scale": r.get("scale", 1),
            "unit": r.get("unit", "")
        }

        try:
            value = read_signal(client, sig, unit_id, word_order)

            entry = {"status": "ok", "value": value, **meta}

            # Optional: add a human-friendly engineering conversion for known HV "raw" power limit regs
            # Your TOU power regs are stored as raw in your JSON ("unit": "raw")
            if key.startswith("tou_bat_pwr") and meta["unit"] == "raw":
                entry["value_w"] = int(value) * hv_power_lsb_w  # raw -> W (HV typical)
            if key in ("max_PV_sell_pwr", "max_sell_power") and meta["unit"] == "W":
                # In your code you often write these as raw (W/10), so if you want, store an extra guess:
                # NOTE: remove this if you decide to fix scale in JSON instead (recommended).
                entry["value_w_guess_if_raw10W"] = int(value) * hv_power_lsb_w

            snapshot["settings"][key] = entry
            print(f"{key} = {value}")

        except Exception as e:
            print(f"[ERROR] {key}: {e}")
            snapshot["settings"][key] = {"status": "error", "error": str(e), **meta}

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"\nSaved snapshot to: {filepath}\n")
    return snapshot, filepath









def logging_configuration(client, signals, unit_id: int, soc_target_pct: int, bat_power_limit_w: int,word_order,
                           out_dir: str = "logs",
                           filename_prefix: str = "deye_config_snapshot",
                           hv_power_lsb_w: int = 10,):   

    #In thise function we we will log the value of the configuration

    
    list_setting=["tou_time1","tou_time2","tou_time3","tou_time4","tou_time5","tou_time6",
    "tou_bat_pwr1","tou_bat_pwr2","tou_bat_pwr3","tou_bat_pwr4","tou_bat_pwr5","tou_bat_pwr6",
    "tou_soc1","mains_charging_enable","tou_charge_en1","grid_check_ct_meter",
    "selling_elec_enable","PV_selling_enable","tou_selling_en","max_PV_sell_pwr","max_sell_power"]
    for key in list_setting:

        if "read" not in signals[key]:
            print(f"Couldnt read {key}")

        else:
            value = read_signal(client, signals[key], unit_id,word_order) 
            print(f"{key} = {value}")
    



    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(out_dir, f"{filename_prefix}_{ts}.json")

    snapshot = {
        "timestamp": ts,
        "unit_id": unit_id,
        "word_order": word_order,
        "settings": {}
    }

    print("\n Configuration snapshot ")
    for key in list_setting:
            sig = signals.get(key)
            if sig is None:
                print(f"[MISSING] {key} is not defined in config.json")
                snapshot["settings"][key] = {"status": "missing_in_config"}
                continue

            if "read" not in sig:
                print(f"[NO READ] {key} has no read definition")
                snapshot["settings"][key] = {"status": "no_read_access"}
                continue

            r = sig["read"]
            meta = {
                "ref": r.get("ref"),
                "fc": r.get("fc"),
                "dtype": r.get("dtype"),
                "scale": r.get("scale", 1),
                "unit": r.get("unit", "")
            }

            try:
                value = read_signal(client, sig, unit_id, word_order)

                entry = {"status": "ok", "value": value, **meta}

               
                if key.startswith("tou_bat_pwr") and meta["unit"] == "raw":
                    entry["value_w"] = int(value) * hv_power_lsb_w  # raw -> W (HV typical)
                if key in ("max_PV_sell_pwr", "max_sell_power") and meta["unit"] == "W":
                    entry["value_w_guess_if_raw10W"] = int(value) * hv_power_lsb_w

                snapshot["settings"][key] = entry
                print(f"{key} = {value}")

            except Exception as e:
                print(f"[ERROR] {key}: {e}")
                snapshot["settings"][key] = {"status": "error", "error": str(e), **meta}

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"\nSaved snapshot to: {filepath}\n")
    return snapshot, filepath



    #return values
 





def set_tou_slot1_all_day(client, signals, unit_id: int, soc_target_pct: int, bat_power_limit_w: int,word_order):
    
    #In order to make sure we are chargin we will set the timeslot 1 all day , so of course the setting will apply immediatly
    # in order to confiigure timeslot 1 , you put the value of the start time in it exemple 0000
    # then the end time of time slot 1 is actualy the start of time slot 2 
    # So in order to do it all day , timeslot 2 finish at 2359

   
    write_signal(client, signals["tou_time1"], unit_id, hhmm_to_u16("0000"),word_order)
    write_signal(client, signals["tou_time2"], unit_id, hhmm_to_u16("2355"),word_order)

    # SOC target
    soc_target_pct = int(soc_target_pct)
    if not (0 <= soc_target_pct <= 100):
        raise ValueError("SOC target must be 0..100")
    write_signal(client, signals["tou_soc1"], unit_id, soc_target_pct,word_order)

    # In the battery power register 154 in thedocumentation say HV is 10 W which mean it is scalled by 10 so we need to divid by 10
    raw = max(0, int(bat_power_limit_w // 10))
    write_signal(client, signals["tou_bat_pwr1"], unit_id, raw,word_order)

    # Enable grid charging by putting the LSB bit to 1 
    write_signal(client, signals["mains_charging_enable"], unit_id, 0x0001,word_order)
    write_signal(client, signals["tou_charge_en1"], unit_id, 0x0001,word_order)









import time

def Test2_Write_Readback_Persistence(client, signals, unit_id, word_order, hv_lsb_w=10):
   
    test_keys = ["PV_selling_enable", "tou_selling_en", "max_PV_sell_pwr", "max_sell_power"]

    def read_key(k):
        if k not in signals or "read" not in signals[k]:
            print(f"[NO READ] {k}")
            return None
        return read_signal(client, signals[k], unit_id, word_order)

    def write_key(k, v):
        if k not in signals or "write" not in signals[k]:
            raise KeyError(f"No write block for {k}")
        write_signal(client, signals[k], unit_id, v, word_order)

    #
    print("\n=== Test 2: Baseline values (before write) ===")
    baseline = {}
    for k in test_keys:
        v = read_key(k)
        baseline[k] = v
        if v is None:
            continue

        if k in ("max_PV_sell_pwr", "max_sell_power"):
            print(f"{k} = {v} (raw)  ~ {int(v) * hv_lsb_w} W (HV)")
        else:
            print(f"{k} = {v}")

   
    print("\nEnter new values to write (safe test).")

    pv_sell = int(input("PV_selling_enable (Reg145) [0=OFF, 1=ON]: ").strip())
    pv_sell = 1 if pv_sell else 0

    tou_sell_hex = input("TOU_selling_en (Reg146) as HEX (e.g. 0x0000 disable, 0x00FF enable all days): ").strip().lower()
    if not tou_sell_hex.startswith("0x"):
        tou_sell_hex = "0x" + tou_sell_hex
    tou_sell = int(tou_sell_hex, 16) & 0xFFFF

    pv_export_w = int(input("Max PV export clamp (W) (Reg340): ").strip())
    total_export_w = int(input("Max total export clamp (W) (Reg143): ").strip())

    
    pv_export_raw = max(0, min(8000, pv_export_w // hv_lsb_w))
    total_export_raw = max(0, min(8000, total_export_w // hv_lsb_w))

    monitor_s = int(input("Monitor duration (seconds) [e.g. 300]: ").strip() or "300")
    poll_s = float(input("Poll period (seconds) [e.g. 10]: ").strip() or "10")

    
    write_key("PV_selling_enable", pv_sell)
    write_key("tou_selling_en", tou_sell)
    write_key("max_PV_sell_pwr", pv_export_raw)
    write_key("max_sell_power", total_export_raw)

   
    print("\n=== Immediate read-back ===")
    expected = {
        "PV_selling_enable": pv_sell,
        "tou_selling_en": tou_sell,
        "max_PV_sell_pwr": pv_export_raw,
        "max_sell_power": total_export_raw,
    }

    for k in test_keys:
        v = read_key(k)
        if v is None:
            continue
        ok = (int(v) == int(expected[k]))
        tag = "[OK]" if ok else "[MISMATCH]"
        if k in ("max_PV_sell_pwr", "max_sell_power"):
            print(f"{tag} {k} = {v} (raw)  ~ {int(v) * hv_lsb_w} W (HV)")
        else:
            print(f"{tag} {k} = {v}")

  
    print(f"\n=== Monitoring for overwrite for {monitor_s}s (every {poll_s}s) ===")
    t_end = time.time() + monitor_s
    overwrites = []

    while time.time() < t_end:
        time.sleep(poll_s)
        for k in test_keys:
            v = read_key(k)
            if v is None:
                continue
            if int(v) != int(expected[k]):
                overwrites.append((time.time(), k, expected[k], v))
                print(f"[OVERWRITE?] {k}: expected {expected[k]}, got {v}")

    if not overwrites:
        print("\n=== Result: No overwrites detected ===")
    else:
        print("\n=== Result: Overwrites detected (summary) ===")
        for ts, k, exp, got in overwrites[:10]:
            print(f"{time.strftime('%H:%M:%S', time.localtime(ts))}  {k}: expected {exp}, got {got}")

    
    print("\n=== Restoring baseline values ===")
    for k in test_keys:
        if baseline[k] is None:
            print(f"[SKIP RESTORE] {k} (no baseline)")
            continue
        try:
            write_key(k, int(baseline[k]))
            print(f"[RESTORED] {k} -> {baseline[k]}")
        except Exception as e:
            print(f"[RESTORE ERROR] {k}: {e}")

    print("\nTest 2 complete.\n")
    return baseline, expected, overwrites


# --------------------------
# Main CLI
# --------------------------

def Selling_PV_only(client,signals,unit_id,word_order):

    #What we need first is to disable charging from the grid to the battery and disable battery selling electricity
    #Enable PV selling to the grid
    write_signal(client, signals["grid_check_ct_meter"], unit_id, 0x0000,word_order)#Choosing CT , in case it is not configured as CT
                                                                                    #Double check if you are using CT or meter
    #Making sure charging from the grid is disabled 
    write_signal(client, signals["mains_charging_enable"], unit_id, 0x0000,word_order)
    write_signal(client, signals["tou_charge_en1"], unit_id, 0x0000,word_order)
    write_signal(client, signals["selling_elec_enable"], unit_id, 0x0000,word_order) #Enabling selling power , value should be 0x0000
    #Enabling PV selling
    write_signal(client, signals["PV_selling_enable"], unit_id, 0x0001,word_order)#Enable Solar Sell

    #Choosing a time of use 
    disabling_all_time_slot(client,signals,unit_id,word_order)
    write_signal(client, signals["tou_time1"], unit_id, hhmm_to_u16("0000"),word_order)
    write_signal(client, signals["tou_time2"], unit_id, hhmm_to_u16("2355"),word_order)

    write_signal(client, signals["tou_selling_en"], unit_id, 0x000,word_order)#Disable in this time of use the selling from battery


    pwr = int(input("Battery discharge power (W): ").strip())
    pwr_HV=max(0, min(8000, pwr // 10)) # Power accordind to register table should be between 0 and 8000 (80 000 in HV since multiplied by 10)

    write_signal(client, signals["max_PV_sell_pwr"], unit_id,pwr_HV,word_order)# How much the battery in tou slot 1 can send power to the grid
    write_signal(client, signals["max_sell_power"], unit_id,pwr_HV,word_order)#How much the inverter can push to the grid (from Battery and PV)



def disabling_all_time_slot(client,signals,unit_id,word_order):

    timeslot=["tou_time1","tou_time2","tou_time3","tou_time4","tou_time5","tou_time6"]
    for key in timeslot:
     write_signal(client, signals[key], unit_id, hhmm_to_u16("2355"),word_order)

    timeslot_bat_pwr=["tou_bat_pwr1","tou_bat_pwr2","tou_bat_pwr3","tou_bat_pwr4","tou_bat_pwr5","tou_bat_pwr6"]
    for key in timeslot_bat_pwr:
     write_signal(client, signals[key], unit_id,0,word_order)
    

def Selling_battery_only(client,signals,unit_id,word_order):

    #What we need first is to disable charging from the grid to the battery and enable selling electricity
    #Also the PV will be not selling to the grid , it will be used for the load and charge battery , but the excess wont go to the grid
    #In other function we will send it to the grid

    write_signal(client, signals["grid_check_ct_meter"], unit_id, 0x0000,word_order)#Choosing CT , in case it is not configured as CT
                                                                                    #Double check if you are using CT or meter
    #Making sure charging from the grid is disabled 

    write_signal(client, signals["mains_charging_enable"], unit_id, 0x0000,word_order)
    write_signal(client, signals["tou_charge_en1"], unit_id, 0x0000,word_order)


    #Disabling the PV Selling
    write_signal(client, signals["PV_selling_enable"], unit_id, 0x0000,word_order)#Disable Solar Sell
    write_signal(client, signals["max_PV_sell_pwr"], unit_id,0,word_order)#PV selling is already disabled , but to make sure with put it to 0 selling power

    #Enabling selling
    write_signal(client, signals["selling_elec_enable"], unit_id, 0x0000,word_order)#0x00 enable selling power
                                                                                    #0x01 enable built in enableb
                                                                                    #0x02 enable external extraposition enabled
    disabling_all_time_slot(client,signals,unit_id,word_order)
    #Choosing a time of use 
    write_signal(client, signals["tou_time1"], unit_id, hhmm_to_u16("0000"),word_order)
    write_signal(client, signals["tou_time2"], unit_id, hhmm_to_u16("2355"),word_order)


    write_signal(client, signals["tou_selling_en"], unit_id, 0x00FF,word_order)#Enabling all days for this tou the selling of power
    

    current_soc=int(read_signal(client,signals["bat_SoC"],unit_id,word_order))

    while True:

        print(f"Current SoC for battery 1 {current_soc}")
        desired_soc = int(input(f"Stop discharging at SOC (0-100, < {current_soc}): ").strip())
        desired_soc = max(0, min(100, desired_soc))
        if 0<=desired_soc<current_soc:
            break
        print("Invalid SOC. It must be below the current SOC.")

    pwr = int(input("Battery discharge power (W): ").strip())
    pwr_HV=max(0, min(8000, pwr // 10)) # Power accordind to register table should be between 0 and 8000 (80 000 in HV since multiplied by 10)
    write_signal(client, signals["tou_soc1"], unit_id, desired_soc, word_order) #Choosing the Soc
    write_signal(client, signals["tou_bat_pwr1"], unit_id,pwr_HV,word_order)# How much the battery in tou slot 1 can send power to the grid
    write_signal(client, signals["max_sell_power"], unit_id,pwr_HV,word_order)#How much the inverter can push to the grid (from Battery and PV)
    




def Charging_grid_only(client, signals, unit_id, word_order):
   
    current_soc = int(read_signal(client, signals["bat_SoC"], unit_id, word_order))

    
    while True:
        print(f"Current battery SOC: {current_soc}%")
        desired_soc = int(input(f"Target SOC for charging (0-100, > {current_soc}): ").strip())
        desired_soc = max(0, min(100, desired_soc))
        if desired_soc > current_soc:
            break
        print("Invalid SOC target. It must be ABOVE the current SOC to force charging.\n")

   
    pwr_w = int(input("Grid charging power limit (W): ").strip())
    pwr_w = max(0, pwr_w)

    
    pwr_raw = max(0, min(8000, pwr_w // 10))  #

    
    try:
        meas = int(read_signal(client, signals["grid_check_ct_meter"], unit_id, word_order))
        print(f"Grid measurement selection (Reg 344): {meas}  (0=CT, 1=meter)")
    except Exception:
        print("Warning: could not read Reg 344 (grid_check_ct_meter).")

    
    disabling_all_time_slot(client, signals, unit_id, word_order)

   
    write_signal(client, signals["tou_time1"], unit_id, hhmm_to_u16("0000"), word_order)
    write_signal(client, signals["tou_time2"], unit_id, hhmm_to_u16("2355"), word_order)

   
    write_signal(client, signals["tou_soc1"], unit_id, desired_soc, word_order)
    write_signal(client, signals["tou_bat_pwr1"], unit_id, pwr_raw, word_order)

    
    write_signal(client, signals["mains_charging_enable"], unit_id, 0x0001, word_order)  
    write_signal(client, signals["tou_charge_en1"], unit_id, 0x0001, word_order)       

   
    write_signal(client, signals["tou_selling_en"], unit_id, 0x0000, word_order)       #disable TOU selling
    write_signal(client, signals["PV_selling_enable"], unit_id, 0x0000, word_order)     #  disable PV export
    write_signal(client, signals["max_PV_sell_pwr"], unit_id, 0x0000, word_order)       #  clamp PV export to 0 (raw units if HV)
    write_signal(client, signals["max_sell_power"], unit_id, 0x0000, word_order)        # clamp total export to 0 (raw units if HV)


    write_signal(client, signals["selling_elec_enable"], unit_id, 0x0002, word_order)   #  external limiting

    print("\nConfigured: Grid charging (TOU slot1 all day)")
    print(f"  Target SOC: {desired_soc}%")
    print(f"  Charge power limit: {pwr_w} W  (raw={pwr_raw})")




def Charging_Discharging_battery_current_limite(client,signals,unit_id,word_order):
    max_bat_charge_current_A = read_signal(client, signals["max_bat_charge_current_A"], unit_id,word_order)
    max_bat_discharge_current_A= read_signal(client, signals["max_bat_discharge_current_A"], unit_id,word_order)
    print(f" Maximum Battery Charge: {max_bat_charge_current_A} A.")
    print(f" Maximum Battery Discharge: {max_bat_discharge_current_A} A.")
    
    while True:
        print("\nMenu:")
        print("  1) Change the Maximum Charging Current")
        print("  2) Change the Maximum Discharging Current")
        print("  3) Go back to Main menu")
        cmd = input("> ").strip()    

        if cmd=="1" :
            current = float(input("Please enter the maxmum Charging Current(A) : ").strip())
            write_signal(client, signals["max_bat_charge_current_A"], unit_id, current,word_order)
            break

        elif cmd=="2":
            current = float(input("Please enter the maxmum Discharging Current(A) : ").strip())
            write_signal(client, signals["max_bat_discharge_current_A"], unit_id, current,word_order)

            break
        elif cmd=="3":
            break
        else :
            print("Invalid option.")
            continue

def main():
    with open("config.json") as f:
        cfg = json.load(f)

    dev = cfg["devices"]["Deye/HV-3P-SG01HP3"]
    unit_id = dev["connection"]["unit_id"]
    word_order=dev["word_order"]
    signals = dev.get("signals", {})
    derived = dev.get("derived", {})

    client = ModbusSerialClient(
        method="rtu",
        port="COM5",   # change on Windows: "COM3"
        baudrate=9600,
        parity="N",
        stopbits=1,
        bytesize=8,
        timeout=1.0
    )

    try:
        if not client.connect():
            raise RuntimeError("Could not open serial port")

        dev_code = read_signal(client, signals["device_type"], unit_id,word_order)
        Device_Type(dev_code) # Checking which inverteur we are using and small test for the modbus communication 

        while True:
            print("\nMenu:")
            print("  0) Test 0: Display live values")
            print("  1) Test 1: Logging the client configuration")
            print("  2) Test 2: Wrtting and checking if invertuer is Overwritting")
            print("  3) Test 3: Charging the Battery from the grid")
            print("  4) Test 4: Discharging the battery to the grid")
            print("  5) Test 5: Selling PV extra power to the grid") 

            print("  5) Checking if ct or Meter")
            print("  6) Charging/Discharging battery Current Limite")
            print("  q) Quit")

           

            cmd = input("> ").strip().lower()


            if cmd == "0":
                for _ in range(2000000):
                    vals = read_all_raw_signals(client, signals, unit_id,word_order)
                    bat_SoC = get_metric("bat_SoC", signals, derived, vals)
                    bat_charge   = get_metric("bat_charge", signals, derived, vals)
                    grid_power  = get_metric("grid_power", signals, derived, vals)
                    bat_discharge = get_metric("bat_discharge", signals, derived, vals)

                    clear_screen()
                    print("Deye Live:")
                    print(f"  SOC: {bat_SoC:.0f} %")
                    print(f"  Battery charge power: {bat_charge:.0f} W (sign depends on inverter convention)")
                    print(f"  Bat discharge: {bat_discharge:.0f} W")
                    print(f"  Grid power:    {grid_power:.0f} W")
                    time.sleep(0.5)
            elif cmd =="1":
                snapshot, path = logging_configuration(client, signals, unit_id, word_order)
                print(path)
                print(snapshot)

            elif cmd=="2":
                    Test2_Write_Readback_Persistence(client, signals, unit_id, word_order, hv_lsb_w=10)
            elif cmd == "3":

                Charging_grid_only(client, signals, unit_id, word_order)

            elif cmd=="4":

                Selling_battery_only(client,signals,unit_id,word_order)
            
            elif cmd=="5":

                Selling_PV_only(client,signals,unit_id,word_order)

            elif cmd=="6":
                ct_enable=read_signal(client,signals["grid_check_ct_meter"],unit_id,word_order)
                if ct_enable ==0:
                    print("CT is connected to the Grid")
                else:
                    print("Meter is connected to the Grid") 
                
            elif cmd=="7":
               
                Charging_Discharging_battery_current_limite(client,signals,unit_id,word_order)
 
          

            elif cmd == "q":
                break
            else:
                print("Invalid option.")

    except KeyboardInterrupt:
        print("\nStopping.")
    except (ModbusException, OSError, RuntimeError, ValueError) as e:
        print("Error:", e)
    finally:
        client.close()
        print("Closed.")

if __name__ == "__main__":
    main()
