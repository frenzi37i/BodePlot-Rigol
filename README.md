# RIGOL DS1054Z - FEELTECH FY32xx AUTOMATED FREQUENCY RESPONSE ANALYSIS
### Francesco Nastrucci - frenzi37i - 10/01/2021

FORK OF https://github.com/ailr16/BodePlot-DS1054Z
Original project by ailr16.

## Features
Features: 
*	Amplitude and phase semilogarithmic plots
* Average acquisition mode, with 2 waves average (for f>2Hz) or high resolution mode (for f<2Hz)
*	Logaritmic or linear frequencies span 
*	Automated setup
*	Automated restore of the previous scope's settings
*	Automated fine adjustment of the vertical scale, for maximized voltage sensitivity, with clipping detection __________________________________________________________________________________
## Use 
* GPIB drivers are needed. 
* Connect both scope and signal generator to PC with usb cables. 
* Connect signal generator CH1 output and scope CH1 to the Device Under Test input; 
* Connect DUT's output to scope CH2.
* Set analysis properties and instruments ports into this script before starting it.
* On windows, Feeltech Signal generator COM port can be founded under 'Device Manager->COM Ports'
* Be sure to have all the needed python packages (if not, install them with pip or anaconda)

In order to find your scope address, run this script:
```python
import pyvisa
rm = pyvisa.ResourceManager()
rm.list_resources()
```
You have to find something like this: 
USB0::0x1AB1::0x04CE::DS1ZA223107793::INSTR

## Needed packages
* matplotlib
* numpy 
* pyvisa
* feeltech

