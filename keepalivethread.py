import time
from signals import write_signal
def keepalive_worker(client, signals, unit_id, word_order,
                     state):
    # state is a shared object/dict containing:
    # state["battery_ctrl"], state["desired_power"], state["stop"], state["period_s"]

    last_tx = 0.0
    while not state["stop"]:
        try:
            if state["battery_ctrl"]:
                now = time.time()
                if now - last_tx >= state["period_s"]:
                    
                    write_signal(client, signals["power_setpoint"], unit_id, state["desired_power"], word_order)
                    last_tx = now
        except Exception as e:
            print(f"\n[keepalive] write failed: {e}")
            state["battery_ctrl"] = False
            time.sleep(1.0)

        time.sleep(0.1)
        

