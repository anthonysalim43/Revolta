from pymodbus.client import ModbusTcpClient
from pymodbus import ModbusException
import time
import json

from config import (
    Device_Type,
    Battery_Charge,
    Battery_Discharge,
    Inverteur_AC_Power,
    clear_screen,
)

def main():
    SB_IP   = "192.168.129.33"
    VIC_IP  = "10.55.55.247"
    SI_IP   = "10.55.55.243"
    PORT    = 502

    while True:
        inverter = input(
            "Please choose a number for your Inverter choice :"
            "\n Press 1 for SMA Sunny Boy Inverter"
            "\n Press 2 for SMA Sunny Island Inverter"
            "\n Press 3 for Victron Energy Multigrid II Inverter\n"
        )

        if inverter == "1":
            Inverter_name = "SMA/SunnyBoy"
            IP_address = SB_IP
            break
        elif inverter == "2":
            Inverter_name = "SMA/SunnyIsland"
            IP_address = SI_IP
            break
        elif inverter == "3":
            Inverter_name = "VictronEnergy/MultiGridII"
            IP_address = VIC_IP
            break
        else:
            print("Wrong key, try again.")

    with open("config.json") as file:
        cfg = json.load(file)

    cfg_signal = cfg["devices"][Inverter_name]["signals"]
    unit_id = cfg["devices"][Inverter_name]["connection"]["unit_id"]

    client = ModbusTcpClient(IP_address, port=PORT)

    try:
        if not client.connect():
            raise RuntimeError("Could not connect to the inverter")
        print("Connected to the Inverter")

        while True:
            clear_screen()
            Device_Type(cfg_signal, client, unit_id)

            inv_ac = Inverteur_AC_Power(cfg_signal, client, unit_id)
            bat_chg, chg_status = Battery_Charge(cfg_signal, client, unit_id)
            bat_dis, dis_status = Battery_Discharge(cfg_signal, client, unit_id)

            PV_Power = inv_ac + bat_chg - bat_dis

            if chg_status:
                print(f"Battery Charging: {bat_chg} W")
            if dis_status:
                print(f"Battery Discharging: -{bat_dis} W")

            print(f"Inverteur AC Power: {PV_Power} W")
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nStopping on user request (Ctrl+C).")
    except (ModbusException, OSError) as e:
        print("Communication error:", e)
    finally:
        client.close()
        print("Modbus client closed.")

if __name__ == "__main__":
    main()
