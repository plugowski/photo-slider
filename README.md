# Motorized Slider based on ESP8266 an Micropython

# Installation

Slider and all dependencies should be build as frozen modules (beacuse of memory that use, bytcode is lighter for ESP), 
instruction how to make it you can find here: https://learn.adafruit.com/micropython-basics-loading-modules/frozen-modules

Generally you have to build your own firmware based with followed frozen bytes:

```buildoutcfg
uhttpd
uasyncio
logging.py
console.sink.py
copy
types
```

I reccomend to download [micropython-lib](https://github.com/micropython/micropython-lib) repository and symlinks all 
necessary libs into modules folder.

In few steps:
Start Vagrant

set symlinks for slider modules:
```bash
cd ~/micropython/ports/esp8266
ln -s /vagrant/slider modules/slider
ln -s /vagrant/slider_api.py modules/slider_api.py
ln -s /vagrant/uhttpd/ modules/uhttpd
ln -s /vagrant/uasyncio/ modules/uasyncio
ln -s /vagrant/logging.py modules/logging.py
ln -s /vagrant/console_sink.py modules/console_sink.py
copy
types
```

make all staff
copy main.py into ESP  and reboot

# Wiring & Configuration

All wiring setup is described in `config.py`, you can also change some of predefined values.
Default OLED display is active, but if you want to disable it, please just set `False` for display_active variable.

# Connection

After installation ESP create WiFi network, you can connect to it and use any browser and use host `http://192.168.4.1` 
to open web-based interface which allows you to move a dolly in specified direction and setup timelapse modes.