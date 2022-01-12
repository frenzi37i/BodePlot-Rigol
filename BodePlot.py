'''
# RIGOL DS1054Z - FEELTECH FY32xx AUTOMATED FREQUENCY RESPONSE ANALYSIS
### Francesco Nastrucci - frenzi37i - 10/01/2021

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
  trigger the signal, a red octagon is plotted in amplitude and phase plots
* For very low amplitude values (vpeak<5mV) phases measurements are considered 
   not accurate and are marked with yellow dot in the phase plot
________________________________________________________________________________

## Use 
* GPIB drivers are needed. 
* Connect both scope and signal generator to PC with usb cables. 
* Connect signal generator CH1 output and scope CH1 to the DUT's input; 
* Connect DUT's output to scope CH2.
* SET SCOPE ADDRESS AND SIGNAL GENERATOR SERIAL PORT into BodePlot.py script 
  before starting it.
* On windows, Feeltech Signal generator COM port can be founded under 
  'Device Manager->COM Ports'
* Be sure to have all the needed python packages (if not, install them with pip)

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
* np 
* pyvisa
* feeltech

'''

import matplotlib.pyplot as plt
import numpy as np 
import time
import feeltech
import pyvisa

###############################  GLOBAL SETTINGS ###############################
# INSTRUMENTS CONNECTIONS PORT
SCOPE_ADDR = 'USB0::0x1AB1::0x04CE::DS1ZA223107793::INSTR' # Rigol 1054Z Address
SIG_GEN_PORT = 'COM19'  # USB Serial port for the FeelTech FY32xx

# GLOBAL CONSTANTS
FIXED_T_DELAY = 4         # Fixed time delay between frequency steps [s]
MEAS_AVER = 4           # Measurements averages
MIN_STEPS = 2           
MAX_STEPS = 1000
MIN_FREQ = 0.2          # 0.2 Hz
MAX_FREQ = 10*10**6     # 10 MHz
MIN_V = 0.5             # Minimum peak to peak voltage [V]
MAX_V = 20              # Maximum peak to peak voltage [V]
PHASE_MIN_V = 0.005     # Under this voltage, phases are considered unreliable
################################################################################

'''READ USER SETTINGS FROM CMD LINE'''


def cmd_check(text, L_val, u_val, tpe):  # checks user inputted values
    while True:
        val = input(text)
        try:
            if tpe == 'f':
                if float(val) < L_val or float(val) > u_val:
                    print(
                        "Inputted value is out of bound; [", L_val, ",", u_val, "]")
                else:
                    return float(val)
            if tpe == 'i':
                if int(val) < L_val or int(val) > u_val:
                    print(
                        "Inputted value is out of bound; [", L_val, ",", u_val, "]")
                else:
                    return int(val)
        except:
            if tpe == 'i':
                t = 'integer'
            else:
                t = ''
            print("Inputted value must be a", t, "number!")


def readUserSettings():
    print("\n     ANALYSIS SETUP     ")
    print("-"*25)
    start_freq = cmd_check("Start frequency [Hz]? ", MIN_FREQ, MAX_FREQ, 'f')
    end_freq = cmd_check("End frequency [Hz]? ", start_freq+0.5, MAX_FREQ, 'f')
    f_steps = cmd_check("Number of steps? ", MIN_STEPS, MAX_STEPS, 'i')
    log_analysis = cmd_check(
        "Frequency sweep = LINEAR [0] or LOGARITHMIC[1] ? ", 0, 1, 'i')
    vpp = cmd_check("Peak to Peak generated voltage? [V] ", MIN_V, MAX_V, 'f')
    v_max = vpp/2
    return start_freq, end_freq, f_steps, v_max, log_analysis

################################################################################


''' SCOPE'S ORIGINAL SETTINGS BACKUP AND RESTORE FUNCTION'''

def decode_str(raw,tpe):
    return tpe(raw[0:raw.find("\\")])

def scope_settings(cmd, scope, readed_param):
    # Backup or restore scope original parameters
    param = (       # parameters used by the script that need backup and restore
            #N=number , S=string
            ("ACQuire:TYPE", str),
            ("ACQuire:AVERages", float),
            ("CHANnel1:COUPling", str),
            ("CHANnel2:COUPling", str),
            ("CHANnel1:VERNier", float),
            ("CHANnel2:VERNier", float),
            ("CHANnel1:SCALe", float),
            ("CHANnel2:SCALe", float),
            ("CHANnel1:OFFset", float),
            ("CHANnel2:OFFset", float),
            ("TRIGger:MODE", str),
            ("TRIGger:COUPling", str),
            ("TRIGger:SWEep", str),
            ("TRIGger:EDGe:SOURce", str),
            ("TRIGger:EDGe:SLOpe", str),
            ("TRIGger:EDGe:LEVel", float),
            ("TIMebase:MAIN:SCAle", float),
            ("ACQuire:MDEPth", str),
            ("MEASure:STATistic:DISPlay",int)
    )

    for i, (p, tpe) in enumerate(param):
        if cmd == "backup":
            raw = scope.query(p+"?")
            readed_param.append(decode_str(raw,tpe))
        if cmd == "restore":
            scope.write(p + ' ' + str(readed_param[i]))
        i = i+1

    if cmd == "backup":
        print("Scope's original settings stored.")
    else:
        print("Scope's original settings restored.")

    return readed_param

################################################################################


'''SCOPE SETUP'''


def scope_setup(scope, v_max):
    print("Scope setup...")

    '''VOLTAGE and PHASE MEASUREMENTS'''
    scope.write("MEASure:CLEar ALL")
    scope.write("MEASure:ITEM VMAX,CHANnel1")
    scope.write("MEASure:ITEM VMAX,CHANnel2")
    scope.write("MEASure:ITEM RPHase,CHANnel2,CHANnel1")
    scope.write("MEASure:STATistic:DISPlay ON")
    scope.write("MEASure:STATistic:ITEM VMAX,CHANnel1")
    scope.write("MEASure:STATistic:ITEM VMAX,CHANnel2")
    scope.write("MEASure:STATistic:ITEM RPHase,CHANnel2,CHANnel1")

    '''ACQUISITION MODE SETUP'''
    scope.write("ACQuire:MDEPth AUTO")
    scope.write("ACQuire:AVERages " + str(MEAS_AVER))

    '''CHANNEL COUPLING SETUP'''
    scope.write("CHANnel1:COUPling AC")
    scope.write("CHANnel2:COUPling AC")

    ''' INITIAL VERTICAL SCALE SETUP'''
    scope.write("CHANnel1:VERNier 1")
    scope.write("CHANnel2:VERNier 1")

    # To improve vertical resolution, vertical resolution is setted at the 
    # selected Vmax/8 divisions + 15%; the 0 reference is setted at the bottom 
    # of the screen; this way we have only the positive half wave in full screen 
    # resolution
    v_res_ch1 = np.round(v_max/8 * 1.15, 2)
    scope.write("CHANnel1:SCALe ", str(v_res_ch1))
    scope.write("CHANnel1:OFFSet ", str(-v_res_ch1*4))

    # Initial settings for channel 2 equal to channel 1
    v_res_ch2 = v_res_ch1
    scope.write("CHANnel2:SCALe ", str(v_res_ch2))
    scope.write("CHANnel2:OFFSet ", str(-v_res_ch2*4*0.99))

    '''TRIGGER SETUP'''
    scope.write("TRIGger:MODE EDGE")
    scope.write("TRIGger:COUPling DC")
    scope.write("TRIGger:SWEep NORMal")
    scope.write("TRIGger:EDGe:SOURce CHANnel1")
    scope.write("TRIGger:EDGe:SLOpe POSitive")
    scope.write("TRIGger:EDGe:LEVel ", str(np.round(v_max*0.7, 1)))
    scope.write("RUN")


################################################################################
'''HORIZONTAL RESOLUTION'''


def set_H_res(scope, freq, nT):
    # Write scope horizontal resolution and return real setted value.
    # Args: scope object, setted sine frequency, number of period to visualize
    h_div = 12
    # Set the horizontal scale of oscilloscope
    scope.write("TIMebase:MAIN:SCAle " + str(nT/(h_div*freq)))
    curr_scale = float(scope.query("TIMebase:MAIN:SCAle?")
                      )  # read the real setted scale
    return curr_scale


################################################################################
'''CH2 VERTICAL RESOLUTION AND ZERO OFFSET'''


def set_ch2_v(scope, res):
    scope.write("CHANnel2:SCALe ", str(res))         # Set the vertical scale
    res = float(scope.query("CHANnel2:SCALe?"))      # Read setted scale
    # Set the offset near 0 at the bottom of the screen
    scope.write("CHANnel2:OFFSet ", str(-res*4*0.99))
    return res   									 # Return real setted scale


################################################################################
'''MEASUREMENT FUNCTION'''


def measure(scope, c1, i, freq_vect, last_v_scale, v_max):
    scope.write("TRIGger:SWEep NORMal")  # Set trigger on normal mode

    '''FREQUENCY AND HORIZONTAL SCALE SETUP'''
    freq = freq_vect[i]                      # Set current frequency
    c1.frequency(freq)						# Set CH1 (gen) frequency
    # Set horizontal resolution for see 2 periods and read back truly adopted 
    # resolution
    curr_h_scale = set_H_res(scope, freq, 2)
    # Set acquisition mode on high resolution only for CH2 autoscale
    scope.write("ACQuire:TYPE HRESolution")
    
    # calculate the sleep time for this frequency, for 2 cycles on screen + 50%
    # If the calculated value is less than 1 second, use 1 second
    t_delay = curr_h_scale*12*2*1.5  
    if t_delay < FIXED_T_DELAY:
        t_delay = FIXED_T_DELAY

    '''AUTOSCALE CH2 VERTICAL SCALE'''
    # Set CH2 vertical scale to the maximum voltage, and reference at the bottom 
    # of the screen
    if i < 1:  # set starting value for the first 2 cycle
        scope.write("CHANnel2:SCALe 10")
        scope.write("CHANnel2:OFFSet -38")
    # after 2 cycles, starts from the mean value of the last 2 elements for a 
    # faster settling
    else:  
        v_res_ch2 = (last_v_scale[i-2]+last_v_scale[i-1])/2
        v_res_ch2 = set_ch2_v(scope, v_res_ch2)

    time.sleep(t_delay/2) # Time needed to update trigger status
    
    # Check for trigger
    start_time = time.time()
    trigg_error = False
    one_shot_auto = False
    one_shot_norm = False
    while True: 
      
        # If this is taking too much time signal this as an error and proceed 
        if time.time()-start_time > t_delay: 
            trigg_error = True
            print("Can't trigger at this frequency. Trigger error raised.")
            break

        trig_status = decode_str(scope.query("TRIGger:STATus?"),str)
        if trig_status != "WAIT":  # Continue to measure if we are triggered
            #double check trigger status
            time.sleep(0.5)
            trig_status = decode_str(scope.query("TRIGger:STATus?"),str)
            if trig_status != "WAIT":
                break
        else: 
            # If not triggered, try to set trigger to auto like 1st options
            if time.time()-start_time < t_delay/2 and one_shot_auto == False:
                scope.write("TRIGger:SWEep AUTO")
                one_shot_auto = True

            #Last otpion: try normal trigger with very low level
            if time.time()-start_time > t_delay/2 and one_shot_norm == False:
                scope.write("TRIGger:SWEep NORMal")
                scope.write("TRIGger:EDGe:LEVel ", str(np.round(v_max*0.2, 1)))
                one_shot_norm = True

            
    # If we haven't triggered the signal, save this measuremnent as 0, and 
    # proceed with the next one; otherway take the measurements
    if trigg_error == True: 
        ch1_v_max = 0
        ch2_v_max = 0
        phase = 0
        v_res_ch2 = 10

    else:
        v_read = float(scope.query("MEASure:ITEM? VMAX,CHANnel2"))  # first reading
        # first adjustment try ad 60% the teoretical resolution
        v_res_ch2 = np.round(v_read/8*1.5, 2)
        v_res_ch2 = set_ch2_v(scope, v_res_ch2)  # set resolution

        while True:
            # Check for over or under-resolution (clipping or too low resolution) 
            # with a shorter horizontale scale then the real measurmentes (for 
            # faster settling)
            time.sleep(t_delay)
            v_read = float(scope.query("MEASure:ITEM? VMAX,CHANnel2"))
            
            # Low resolution or clipping detection
            if (v_read < v_res_ch2*4) or (v_read > v_res_ch2*7.90):  
                v_res_ch2 = np.round(v_read/8*1.3, 4)
            else:      # resolution ok
                break
            if v_res_ch2 < 0.001:     # check for minimum vertical resolution limits
                v_res_ch2 = 0.001
            old_scale = float(scope.query("CHANnel2:SCALe?"))  # save last scale
            v_res_ch2 = set_ch2_v(scope, v_res_ch2) 
            if old_scale == v_res_ch2:  # we can't improve resolution
                break

        '''TAKE THE MEASUREMENT'''
        scope.write("MEASure:STATistic:RESet")
        scope.write("ACQuire:TYPE AVERages")  # average mode for taking measurements
        time.sleep(t_delay)  # let the scope settle down
        ch1_v_max = scope.query("MEASure:STATistic:ITEM? AVERages,VMAX,CHANnel1")
        ch2_v_max = scope.query("MEASure:STATistic:ITEM? AVERages,VMAX,CHANnel2")
        phase = scope.query("MEASure:STATistic:ITEM? AVERages,RPHase,CHANnel2,CHANnel1")

    return ch1_v_max, ch2_v_max, phase, v_res_ch2, trigg_error


################################################################################
'''UNDER VOLTAGE DETECTION'''


def under_v_detct(ch2_v_max,trigg_err):
    # detect if there are measured voltage under 3.5mV
    elem = []
    for i, e in enumerate(ch2_v_max):
        if e < PHASE_MIN_V:
            if trigg_err[i] == 0:
                elem.append(i)
    return elem

################################################################################
'''PLOT FUNCTION'''


def plots_v2(freq_vect, db, phase, trigg_error, elementUV):
    print("Plotting...")
    fig, (f1, f2) = plt.subplots(2, sharex=True)
    # plt.ion()

    '''Amplitude plot'''
    f1.plot(freq_vect, db, marker='o')
    f1.set(xlabel='f [Hz]', ylabel='dB', title='Amplitude')
    f1.axhline(-3, linestyle="--", color='r')  # -3db horizontal line

    '''Phase plot'''
    f2.plot(freq_vect, phase, marker='o')
    f2.set(xlabel='f [Hz]', ylabel='phase [°]', title='Phase')

    '''Plot trigger error'''
    for i,e in enumerate(trigg_error):
        if e == True:
            f1.plot(freq_vect[i], 0,
                    marker='H', color='r', linestyle='None')
            f2.plot(freq_vect[i], 0,
                    marker='H', color='r', linestyle='None')

    '''Plot undervoltages unreliables phases'''
    if len(elementUV) > 0:
        f2.plot(freq_vect[elementUV], phase[elementUV],
                marker='o', color='y', linestyle='None', ms=5)

    plt.xscale('log')
    f1.grid(True, which='both', ls='-', color='0.65', lw = 0.5)
    f2.grid(True, which='both', ls='-', color='0.65',lw = 0.5)
    plt.show()


################################################################################


def main():

    print("\n########### FREQUENCY RESPONSE ANALYSIS SCRIPT #############")
    [start_freq, end_freq, f_steps, v_max, log_analysis] = readUserSettings()
    
    '''VECTORS INITIALIZATION'''
    ch1_v_max = np.zeros(f_steps)
    ch2_v_max = np.zeros(f_steps)
    phase = np.zeros(f_steps)
    db = np.zeros(f_steps)
    freq_vect = np.zeros(f_steps)
    last_v_scale = np.zeros(f_steps)
    trigg_error = np.zeros(f_steps)

    '''FREQUENCIES VECTOR'''
    if log_analysis == True:
        freq_vect = np.logspace(np.log10(start_freq), np.log10(
            end_freq), f_steps, endpoint=True, base=10)
    else:
        freq_vect = np.linspace(start_freq, end_freq, f_steps, endpoint=True)

    ''' FUNCTION GENERATOR CONNECTION and SETUP'''
    print("_"*30, "\nConnecting to signal generator...")
    try:
        # Connect FeelTech signal generator
        ft = feeltech.FeelTech(SIG_GEN_PORT)
    except:
        print("Signal generator connection failed. Check connection port.")
        input()
        exit()
    c1 = feeltech.Channel(1, ft)					# Init the CH1 of generator
    c1.waveform(feeltech.SINE)					# CH1 will generate a sine wave
    c1.amplitude(v_max*2)					# Set CH1 peak to peak voltage
    print("Signal generator connected.")

    ''' SCOPE CONNECTION and SETUP '''
    print("Connecting to scope...")
    rm = pyvisa.ResourceManager()
    try:
        scope = rm.open_resource(SCOPE_ADDR)  # Connect the scope
    except:
        print("Scope connection failed. Check scope address.")
        input()
        exit()
    print("Scope connected")
    # Backup scope settings
    readed_param = scope_settings('backup', scope, [])
    scope_setup(scope, v_max)
    print("Setup completed.")

    '''MEASUREMENTS'''
    print("_"*30)
    print("Starting measurements\nWait for scope to settle...")
    time.sleep(FIXED_T_DELAY)
    print("MEASUREMENT STARTED")
    for i in range(0, f_steps):
        print(np.floor(100*((i+1)/f_steps)), "% - Analyzing ",
              np.round(freq_vect[i], 2), " Hz")    # completed process %

        (ch1_v_max[i], ch2_v_max[i], phase[i], last_v_scale[i],trigg_error[i]) \
            = measure(scope, c1, i, freq_vect, last_v_scale,v_max) 	  

    db = 20*np.log10(ch2_v_max/ch1_v_max)  # Compute db

    '''TOO LOW AMPLITUDE VALUE DETECTION'''
    # If amplitude is too low (<3.5mV), phase detection is unreliable, so 
    # anomaly detection have to discard those values; trigger errors are not 
    # undervoltages!
    underVElem = under_v_detct(ch2_v_max,trigg_error)

    print("MEASUREMENT COMPLETED")
    print("_"*30)
    # Restore scope's original settings
    scope_settings('restore', scope, readed_param)
    # Plot frequency response diagrams
    plots_v2(freq_vect, db, phase, trigg_error, underVElem)
    scope.close()				# Stop communication with oscilloscope
    print("Done.")


if __name__ == "__main__":
    main()
