# RIGOL DS1054Z - FEELTECH FY32xx AUTOMATED FREQUENCY RESPONSE ANALYSIS
### Francesco Nastrucci - frenzi37i - 12/01/2021

TESTED ON WINDOWS ONLY

## Features
* Amplitude and phase semilogarithmic plots
* Average acquisition mode, with 4 waves average (for f>2Hz) or high resolution 
   mode (for f<2Hz)
* Logaritmic or linear frequencies span 
* Automated setup
* Automated restore of the previous scope's settings
* Automated fine adjustment of the vertical scale for maximized voltage 
   sensitivity, with clipping detection 
* Sense triggering errors and try to correct them. If it's not possible to 
  trigger the signal, a red octagon is plotted in amplitude and phase plots for that frequency
* For very low amplitude values (vpeak<5mV) phases measurements are considered 
   not accurate and are marked with yellow dot in the phase plot
__________________________________________________________________________________
## Use 
* GPIB drivers are needed. 
* Connect both scope and signal generator to PC with usb cables. 
* Connect signal generator CH1 output and scope CH1 to the Device Under Test input; 
* Connect DUT's output to scope CH2.
* SET SCOPE ADDRESS AND SIGNAL GENERATOR SERIAL PORT into BodePlot.py script before starting it.
* On windows, Feeltech Signal generator COM port can be founded under 'Device Manager->COM Ports'
* Be sure to have all the needed python packages (if not, install them with pip or anaconda)

### To find your scope address
While scope is connected with usb cable to the PC, run this script:
```python
import pyvisa
rm = pyvisa.ResourceManager()
rm.list_resources()
```
You have to find something like this: 
USB0::0x1AB1::0x04CE::DS1ZA223107793::INSTR
this is the scope address to copy into the main script.

## Needed packages
* matplotlib
* numpy 
* pyvisa
* feeltech

## Plot example
This is the output for an R-C low pass filter with R=1k, C=10n


