from modbus_shared import (modbus_lock)

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

    with modbus_lock:
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

        
    with modbus_lock:
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