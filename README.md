# BodePlot
 Bode Plot With RIGOL DS1054 and FeelTech FY32xx
IGOL DS1054Z - FEELTECH FY32xx AUTOMATED FREQUENCY RESPONSE ANALYSIS
Francesco Nastrucci - frenzi37i - 10/01/2021

FORK OF https://github.com/ailr16/BodePlot-DS1054Z
Original project by ailr16.

Features: 
> 	Amplitude and phase semilogarithmic plots
>   Average acquisition mode, with 4 waves average
>	Logaritmic or linear frequencies span 
>	Automated setup
>	Automated restore of the previous acquisition settings
>	Automated fine adjustment of the vertical scale, for maximized voltage sensitivity, with clipping detection 
>   Each measurements is done in a fixed time of 5 seconds; for lower frequencies the measurement 
	time is automatically increased in order to acquire at least 4 complete screen

________________________________________________________________________________________________
Use: 
GPIB drivers are needed. 
Connect both scope and signal generator to PC with usb cables. 
Connect signal generator CH1 output and scope CH1 to the Device Under Test input; 
Connect DUT's output to scope CH2.
Set analysis properties and instruments ports into this script before starting it.
On windows, Feeltech Signal generator COM port can be founded under 'Device Manager->COM Ports'
Be sure to have all the needed python packages (if not, install them with pip or anaconda)

In order to find your scope address, run this script:
import pyvisa
rm = pyvisa.ResourceManager()
rm.list_resources()

You have to find something like this: 
USB0::0x1AB1::0x04CE::DS1ZA223107793::INSTR

