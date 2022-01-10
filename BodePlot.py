'''
RIGOL DS1054Z - FEELTECH FY32xx AUTOMATED FREQUENCY RESPONSE ANALYSIS
Francesco Nastrucci - frenzi37i - 10/01/2021

FORK OF https://github.com/ailr16/BodePlot-DS1054Z
Original project by ailr16.

Features: 
> 	Amplitude and phase semilogarithmic plots
>   Average acquisition mode, with 4 waves average
	TODO: CHECK AVERGA MODE FOR f<1hz
>	Logaritmic or linear frequencies span 
>	Automated setup
>	PARTIALLY TODO: Automated restore of the previous acquisition settings
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

___________________________________________________________________________________________________

'''

from numpy.core.fromnumeric import mean
import pyvisa
import feeltech
import time
import numpy
import matplotlib.pyplot as plt
import math


###################################################################################
###############################  USER SETTINGS ####################################
# ANALYSIS PARAMETERS 
startFreq = 5   	#Start frequency [Hz]
endFreq = 1000  	#Stop frequency [Hz]
freqSteps = 20   	#Number of frequencies steps
waveVMax = 5 	 	#Wave Max Voltage
logAnalysis = True	#Log spaced frequencis if True, Linearly spaced frequencies if false

fixedTimeDelay = 3  #Adjust the time delay between frequency increments [s]

# INSTREUMENTS CONNECTIONS PORT
scopeAddres='USB0::0x1AB1::0x04CE::DS1ZA223107793::INSTR' #Rigol 1054Z Address
sigGenCOMPort = 'COM19' #USB Serial port for the FeelTech FY32xx

###################################################################################

print("\n########### FREQUENCY RESPONSE ANALYSIS SCRIPT #############")

''' USER INPUTTED VALUES CHECK '''
if startFreq < 0.5:
	print('ERROR. Frequency must be greater than 0.5 Hz')
	print('Please press Enter to exit :-(')
	input()
	exit()

if startFreq < 0 or endFreq < 0:
	print('ERROR. Frequency must be positive')
	print('Please press Enter to exit :-(')
	input()
	exit()

if startFreq > endFreq:
	print('ERROR. Start Frequency must be less than End Frequency')
	print('Please press Enter to exit:-(')
	input()
	exit()

if freqSteps <= 1:
	print('ERROR. Frequency steps must be greater than 1')
	print('Please press Enter to exit :-(')
	input()
	exit()
	
if waveVMax <= 0:
	print('ERROR. Max Voltage must be greater than zero')
	print('Please press Enter to exit :-(')
	input()
	exit()


print("\nInstruments setup...") #verbosity

'''VECTORS INITIALIZATION'''
CH1VMax = numpy.zeros(freqSteps)				#Create an array for CH1 measurements
CH2VMax = numpy.zeros(freqSteps)				#Create an array for CH2 measurements
PHASE = numpy.zeros(freqSteps)               	#Create an array for PHASE measurements
db = numpy.zeros(freqSteps)						#Create an array for the result in db
freqVect = numpy.zeros(freqSteps)				#Create an array for values of frequency
lastScale = numpy.zeros(freqSteps)

#LOGARITHMIC SPACED FREQUENCIES
if logAnalysis==True: 
	freqVect = numpy.logspace(numpy.log10(startFreq),numpy.log10(endFreq),freqSteps,endpoint=True,base=10)
#LINEARLY SPACED FREQUENCIES
else:
	freqVect = numpy.linspace(startFreq,endFreq,freqSteps,endpoint=True)


''' FUNCTION GENERATOR CONNECTION and SETUP'''
ft = feeltech.FeelTech(sigGenCOMPort)       #Connect FeelTech signal generator
c1 = feeltech.Channel(1,ft)					#Init the CH1 of generator
c1.waveform(feeltech.SINE)					#CH1 will generate a sine wave
c1.amplitude(waveVMax*2)					#Set CH1 peak to peak voltage

''' SCOPE CONNECTION and SETUP '''
rm = pyvisa.ResourceManager()					#PyVISA Resource Manager
scope = rm.open_resource('USB0::0x1AB1::0x04CE::DS1ZA223107793::INSTR') #connect the scope

'''VOLTAGE MEASUREMENTS'''
scope.write("MEASure:CLEar ALL")				     #Clear all measurement items
scope.write("MEASure:ITEM VMAX,CHANnel1")			 #Create the VTOP measurement item for CH1
scope.write("MEASure:ITEM VMAX,CHANnel2")			 #Create the VTOP measurement item for CH2
scope.write("MEASure:ITEM RPHase,CHANnel2,CHANnel1") #Create the phase measurement between CH2 and CH1


'''ACQUISITION MODE SETUP'''
scope.write("ACQuire:TYPE?")      			#read current mode
r=str(scope.read_raw())           			#reading raw response
origAcqMode=r[r.find("'")+1:r.find("\\")]   #extract current mode
scope.write("ACQuire:TYPE AVERages") 		#set acquisition mode on average
scope.write("ACQuire:AVERages 4") 			#Set 4 cycle average 

'''CHANNEL COUPLING SETUP'''
scope.write("CHANnel1:COUPling AC") 			#set AC coupling
scope.write("CHANnel2:COUPling AC") 			

''' INITIAL VERTICAL SCALE SETUP'''
#Store old vernier mode settings (fine scale setting)
scope.write("CHANnel1:VERNier?") 
r=str(scope.read_raw())
origVernModeCH1 = r[r.find("'")+1:r.find("'")+2] 
scope.write("CHANnel2:VERNier?") 
r=str(scope.read_raw())
origVernModeCH2 = r[r.find("'")+1:r.find("'")+2] 

scope.write("CHANnel1:VERNier 1") #set CH1 to vernier mode
scope.write("CHANnel2:VERNier 1") #set CH2 to vernier mode

#To improve the vertical resolution, we set the vertical resolution at the selected Vmax/8 divisions + 15%, 
#and set the 0 at the bottom of the screen; 
#this way we have only the positive wave in full screen resolution
verticalResCH1=numpy.round(waveVMax/8*1.15,2)
scope.write("CHANnel1:SCALe ",str(verticalResCH1))
scope.write("CHANnel1:OFFSet ",str(-verticalResCH1*4))

#Starting settings for channel 2 equal to channel 1
verticalResCH2 = verticalResCH1
scope.write("CHANnel2:SCALe ",str(verticalResCH2))
scope.write("CHANnel2:OFFSet ",str(-verticalResCH2*4*0.99))

'''TRIGGER SETUP'''
scope.write("TRIGger:MODE EDGE")
scope.write("TRIGger:COUPling DC")
scope.write("TRIGger:SWEep NORMal")
scope.write("TRIGger:EDGe:SOURce CHANnel1")
scope.write("TRIGger:EDGe:SLOpe POSitive")
scope.write("TRIGger:EDGe:LEVel ",str(numpy.round(waveVMax*0.8,1)))
scope.write("RUN")

print("DONE") #verbosity

'''MEASUREMENTS'''
print("\nStarting to measure...\nWait for scope to settle...")
time.sleep(fixedTimeDelay)					#Time delay
print("\nMEASURE STARTED")

i = 0
while i < freqSteps:
	print(numpy.floor(100*((i+1)/freqSteps)),"% - Analyzing ",numpy.round(freqVect[i],2)," Hz")   #print completed process percentage

	'''FREQUENCY AND HORIZONTAL SCALE SETUP'''
	freq = freqVect[i]                      #Set frequency 
	c1.frequency(freq)						#Set CH1 (gen) frequency 
	scope.write("TIMebase:MAIN:SCAle "+ str(1/(3*freq)))	#Set the horizontal scale of oscilloscope for at least 4 period view
	currScale = float(scope.query("TIMebase:MAIN:SCAle?"))  #read the real setted scale
	timeDelay = currScale*12*4  #calculate the sleep time for this frequency = 4 time a full screen acquisition (because we are averaging values over 4 acquisitions) 

	#If the calculated value is less than the fixed one, use the fixed one; otherway use the calculated one
	if timeDelay<fixedTimeDelay:
		timeDelay = fixedTimeDelay 

	'''AUTOSCALE CH2 VERTICAL SCALE'''
	#print("Adjusting CH2 vertical scale...") #verbosity
	#Set CH2 vertical scale to the maximum voltage, and reference at the bottom of the screen
	if i>1: #after 2 cycles, starts from the mean value
		verticalResCH2=(lastScale[i-2]+lastScale[i-1])/2
		scope.write("CHANnel2:SCALe ",str(verticalResCH2))          #set the vertical scale
		realVerticalResCH2 = float(scope.query("CHANnel2:SCALe?"))
		scope.write("CHANnel2:OFFSet ",str(-realVerticalResCH2*4*0.99)) #set the offset near 0 at the bottom of the screen
	else:
		scope.write("CHANnel2:SCALe 10")  
		scope.write("CHANnel2:OFFSet -38")

	time.sleep(1)
	vRead = float(scope.query("MEASure:ITEM? VMAX,CHANnel2")) #first reading 
	verticalResCH2=numpy.round(vRead/8*2,2)
	scope.write("CHANnel2:SCALe ",str(verticalResCH2))          #set the vertical scale
	realVerticalResCH2 = float(scope.query("CHANnel2:SCALe?"))
	scope.write("CHANnel2:OFFSet ",str(-realVerticalResCH2*4*0.99)) #set the offset near 0 at the bottom of the screen
	
	while(1):		
		#Check for over or under-resolution (clipping or too low resolution)
		time.sleep(timeDelay)
		vRead = float(scope.query("MEASure:ITEM? VMAX,CHANnel2")) #read voltage
		if vRead<realVerticalResCH2*4 or vRead>realVerticalResCH2*7.90: #clipping
			verticalResCH2=numpy.round(vRead/8*1.3,4)
			#print("Clip or undervoltage")
		else:
			break
		if verticalResCH2<0.001: #check for minimum limits
			verticalResCH2=0.001 
		oldScale = float(scope.query("CHANnel2:SCALe?"))            #check last scale
		scope.write("CHANnel2:SCALe ",str(verticalResCH2))          #set the vertical scale
		realVerticalResCH2=float(scope.query("CHANnel2:SCALe?"))    #check setted value
		scope.write("CHANnel2:OFFSet ",str(-realVerticalResCH2*4*0.99)) #set the offset near 0 at the bottom of the screen
		if oldScale == realVerticalResCH2: #if nothing changed we are in a dangerous loop and we need to exit 
			break

	'''TAKE THE MEASUREMENT'''
	time.sleep(0.5)						#Time delay - wait for measaurement
	CH1VMax[i] = scope.query("MEASure:ITEM? VMAX,CHANnel1")			#Read and save CH1 VMax
	CH2VMax[i] = scope.query("MEASure:ITEM? VMAX,CHANnel2")			#Read and save CH2 VMax
	PHASE[i] = scope.query("MEASure:ITEM? RPHase,CHANnel2,CHANnel1")#read phase between CH1 and CH2
	
	lastScale[i]=realVerticalResCH2; #save last vertical scale
	i = i + 1							#Increment index

print("\nMEASURE COMPLETED")

db = 20*numpy.log10(CH2VMax/CH1VMax)	#Compute db


'''PLOTS'''
fig,(f1,f2)=plt.subplots(2,sharex=True)
#plt.ion()

'''Amplitude plot'''
f1.plot(freqVect,db)			                       
f1.set(xlabel='f [Hz]',ylabel='dB', title='Amplitude')
f1.axhline(-3,linestyle="--",color='r') #-3db horizontal line

'''Phase plot'''
f2.plot(freqVect,PHASE)			#Graph data
f2.set(xlabel='f [Hz]',ylabel='phase [°]', title='Phase')

f1.grid(True)
f2.grid(True)
plt.xscale('symlog')
plt.show()


''' RESTORE SCOPE'S INITIAL PARAMETERS'''
print("\nRestoring scope's original settings") #verbosity
scope.write("ACQuire:TYPE ",origAcqMode)  #restore the original acquistion mode
scope.write("CHANnel1:VERNier ",origVernModeCH1) #restore original vernier mode (fine vertical divisions)
scope.write("CHANnel2:VERNier ",origVernModeCH2)

scope.close()					#Stop communication with oscilloscope

print("Done.") #verbosity
