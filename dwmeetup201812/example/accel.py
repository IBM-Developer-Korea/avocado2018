import json
import network
import time
import math
import umqtt.simple as simple
from machine import Pin
import ugfx
from mpu6050 import MPU

sta_if = network.WLAN(network.STA_IF)

orgID = "ua3ev8" # <<< org_id 
deviceType = "badge2018"
deviceID = ''.join('{:02X}'.format(c) for c in sta_if.config('mac'))
user = "use-token-auth"
authToken = 'helloiot' # <<< auth_token

clientID = "d:" + orgID + ":" + deviceType + ":" + deviceID
broker = orgID + ".messaging.internetofthings.ibmcloud.com"
buttonTopic = b"iot-2/evt/button/fmt/json"
accelTopic = b"iot-2/evt/accel/fmt/json"
colorCommandTopic = b"iot-2/cmd/color/fmt/json"
ledCommandTopic = b"iot-2/cmd/led/fmt/json"

# LED
led_red = Pin(17, Pin.OUT, value=0)
led_blue = Pin(16, Pin.OUT, value=0)

# ugfx
ugfx.init()
ugfx.input_init()
ugfx.clear(ugfx.BLACK)

# button 
def btn_cb(c, key, pressed):
  event = {'d': {'char': key, 'type': 'keydown' if pressed else 'keyup' }}
  print((buttonTopic, key, event))
  c.publish(buttonTopic, json.dumps(event))

def sub_cb(topic, msg):
    obj = json.loads(msg)
    print((topic, msg, obj))
    if topic == ledCommandTopic:
        led_cb(obj)
    elif topic == colorCommandTopic:
        color_cb(obj)

def led_cb(obj):
  if obj['d']['target'] == "red":
      led = led_red
  elif obj['d']['target'] == "blue":
      led = led_blue
  else:
      print('Unknown target')
      return
  if obj['d']['action'] == "on":
      led.value(1)
  elif obj['d']['action'] == "off":
      led.value(0)
  elif obj['d']['action'] == "toggle":
      led.value(1 if led.value() == 0 else 0)
  else:
      print('Unknown action')
      return

prev_color = ""
def color_cb(obj):
  global prev_color

  try:
      color = getattr(ugfx, obj['d']['color'].upper())
  except:
      try:
        color = int(obj['d']['color'])
      except:
        print('Unknown color')
        return
  if prev_color != color:
      ugfx.clear(color)
      prev_color = color

def main():
    # Garbage Collection
    gc.collect()

    # init MQTT
    c = simple.MQTTClient(clientID, broker, user=user, password=authToken, ssl=True)
    c.set_callback(sub_cb)
    c.connect()
    c.subscribe(colorCommandTopic)
    c.subscribe(ledCommandTopic)
    # init input button 
    ugfx.input_attach(ugfx.JOY_UP, lambda pressed: btn_cb(c, 'U', pressed))
    ugfx.input_attach(ugfx.JOY_DOWN, lambda pressed: btn_cb(c, 'D', pressed))
    ugfx.input_attach(ugfx.JOY_LEFT, lambda pressed: btn_cb(c, 'L', pressed))
    ugfx.input_attach(ugfx.JOY_RIGHT, lambda pressed: btn_cb(c, 'R', pressed))
    ugfx.input_attach(ugfx.BTN_MID, lambda pressed: btn_cb(c, 'M', pressed))
    ugfx.input_attach(ugfx.BTN_A, lambda pressed: btn_cb(c, 'A', pressed))
    ugfx.input_attach(ugfx.BTN_B, lambda pressed: btn_cb(c, 'B', pressed))
    # init MPU6050
    # i2c = machine.I2C(scl=machine.Pin(26), sda=machine.Pin(25))
    mpu = MPU(26, 25)
    mpu.calibrate()
    print("Connected, waiting for event")

    accel = {'d': {
        'acceleration_x':'',
        'acceleration_y':'',
        'acceleration_z':'',
        'temperature':'',
        'gyro_x':'',
        'gyro_y':'',
        'gyro_z':'',
      }
    }

    try:
        while True:
            x, y, z, t, dx, dy, dz = mpu.read_sensors_scaled()
            accel['d']['acceleration_x'] = x
            accel['d']['acceleration_y'] = y
            accel['d']['acceleration_z'] = z
            accel['d']['temperature'] = t/340 + 36.53
            accel['d']['gyro_x'] = dx
            accel['d']['gyro_y'] = dy
            accel['d']['gyro_z'] = dz
            c.publish(accelTopic, json.dumps(accel))

            time.sleep_ms(500)
            #c.wait_msg()
            c.check_msg()
    finally:
        c.disconnect()
        ugfx.input_init()
        print("Disonnected")
