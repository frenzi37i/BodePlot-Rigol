'''
RIGOL DS1054Z - FEELTECH FY32xx AUTOMATED FREQUENCY RESPONSE ANALYSIS
Francesco Nastrucci - frenzi37i - 10/01/2021

FORK OF https://github.com/ailr16/BodePlot-DS1054Z
Original project by ailr16.

Features: 
> 	Amplitude and phase semilogarithmic plots
>   Average acquisition mode, with 4 waves average
	TODO: CHECK AVERAGE MODE FOR f<1hz
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

___________________________________________________________________________________________________

'''

from numpy.core.fromnumeric import mean
import pyvisa
import feeltech
import time
import numpy
import matplotlib.pyplot as plt
import math

''' SCOPE'S ORIGINAL SETTINGS BACKUP AND RESTORE FUNCTION'''
def originalSettings(cmd,scope,readedParam):
	#Backup or restore scope original parameters
	param = [   #parameters used by the script that need backup and restore
	#N=number , S=string
		["ACQuire:TYPE","S"],
		["ACQuire:AVERages","N"],
		["CHANnel1:COUPling","S"],
		["CHANnel2:COUPling","S"],
		["CHANnel1:VERNier","N"],
		["CHANnel2:VERNier","N"],
		["CHANnel1:SCALe","N"],
		["CHANnel2:SCALe","N"],
		["CHANnel1:OFFset","N"],
		["CHANnel2:OFFset","N"],
		["TRIGger:MODE","S"],
		["TRIGger:COUPling","S"],
		["TRIGger:SWEep","S"],
		["TRIGger:EDGe:SOURce","S"],
		["TRIGger:EDGe:SLOpe","S"],
		["TRIGger:EDGe:LEVel","N"],
		["TIMebase:MAIN:SCAle","N"],
		["ACQuire:MDEPth","S"]
	]

	for i,[p,Type] in enumerate(param):
		if cmd=="backup":
			raw = scope.query(p+"?")
			if Type == 'S':
				raw=raw[0:raw.find("\\")]
				readedParam.append(str(raw))
			if Type == 'N':
				readedParam.append(float(raw))
		if cmd=="restore":
			if Type == 'N':
				scope.write(p+" "+str(readedParam[i]))
			else:
				scope.write(p+" "+readedParam[i])
		i=i+1

	if cmd == "backup":
		print("Scope's original settings stored.")
	else:
		print("Scope's original settings restored.")

	return readedParam

######################################################################################

'''SCOPE SETUP'''
def scopeSetup(scope,waveVMax):
	print("Scope setup...") #verbosity
    
	scope.write("ACQuire:MDEPth AUTO")      #set automatic memory depth

	'''VOLTAGE MEASUREMENTS'''
	scope.write("MEASure:CLEar ALL")				     #Clear all measurement items
	scope.write("MEASure:ITEM VMAX,CHANnel1")			 #Create the VTOP measurement item for CH1
	scope.write("MEASure:ITEM VMAX,CHANnel2")			 #Create the VTOP measurement item for CH2
	scope.write("MEASure:ITEM RPHase,CHANnel2,CHANnel1") #Create the phase measurement between CH2 and CH1

	'''ACQUISITION MODE SETUP'''
	#scope.write("ACQuire:TYPE AVERages") 		#set acquisition mode on average
	scope.write("ACQuire:AVERages 2") 			#Set 2 cycle average 

	'''CHANNEL COUPLING SETUP'''
	scope.write("CHANnel1:COUPling AC") 			#set AC coupling
	scope.write("CHANnel2:COUPling AC") 			

	''' INITIAL VERTICAL SCALE SETUP'''
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

	return [verticalResCH1,verticalResCH2]
######################################################################################
'''HORIZONTAL RESOLUTION'''
def setHorizRes(scope,freq,nT):
	#Write scope horizontal resolution and return real setted value. 
	#It needs: scope object, frequency of the sine wanted, number of period to visualize
	horizDiv = 12
	scope.write("TIMebase:MAIN:SCAle "+ str(nT/(horizDiv*freq)))	#Set the horizontal scale of oscilloscope 
	currScale = float(scope.query("TIMebase:MAIN:SCAle?"))  #read the real setted scale
	return currScale
######################################################################################
'''CH2 VERTICAL RESOLUTION AND ZERO OFFSET'''
def setCH2(scope,res):
			scope.write("CHANnel2:SCALe ",str(res))          #set the vertical scale
			res = float(scope.query("CHANnel2:SCALe?"))      #read setted scale
			scope.write("CHANnel2:OFFSet ",str(-res*4*0.99)) #set the offset near 0 at the bottom of the screen
			return res   									 #return setted scale
######################################################################################
'''PLOTS FUNCTION'''
def plots(freqVect,db,PHASE):
	print("Plotting...")
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

######################################################################################

def main():
	###################################################################################
	###############################  USER SETTINGS ####################################
	# ANALYSIS PARAMETERS 
	startFreq = 2   	#Start frequency [Hz]
	endFreq = 15  	#Stop frequency [Hz]
	freqSteps = 10   	#Number of frequencies steps
	waveVMax = 5 	 	#Wave Max Voltage
	logAnalysis = True	#Log spaced frequencis if True, Linearly spaced frequencies if false

	fixedTimeDelay = 3  #Adjust the time delay between frequency increments [s]

	# INSTREUMENTS CONNECTIONS PORT
	scopeAddress='USB0::0x1AB1::0x04CE::DS1ZA223107793::INSTR' #Rigol 1054Z Address
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
	print("Connecting to signal generator...")
	try: 
		ft = feeltech.FeelTech(sigGenCOMPort)       #Connect FeelTech signal generator
		c1 = feeltech.Channel(1,ft)					#Init the CH1 of generator
		c1.waveform(feeltech.SINE)					#CH1 will generate a sine wave
		c1.amplitude(waveVMax*2)					#Set CH1 peak to peak voltage
	except:
		print("Signal generator connection failed. Check connection port.")
		input()
		exit()
	print("Signal generator connected.")
    
	''' SCOPE CONNECTION and SETUP '''
	print("Connecting to scope...")
	rm = pyvisa.ResourceManager()              #PyVISA Resource Manager
	try:
		scope = rm.open_resource(scopeAddress) #connect the scope
	except:
		print("Scope connection failed. Check scope address.")
		input()
		exit()
	print("Scope connected")	
	readedParam = originalSettings('backup',scope,[]) #backup scope settings
	[verticalResCH1,verticalResCH2] = scopeSetup(scope, waveVMax) #setup scope
	print("done.")

	'''MEASUREMENTS'''
	print("\nStarting measurements\nWait for scope to settle...")
	time.sleep(fixedTimeDelay)					#Time delay
	print("_________________________\nMeasure started")
    
	i = 0
	while i < freqSteps:
		print(numpy.floor(100*((i+1)/freqSteps)),"% - Analyzing ",numpy.round(freqVect[i],2)," Hz")   #print completed process percentage

		'''FREQUENCY AND HORIZONTAL SCALE SETUP'''
		freq = freqVect[i]                      #Set frequency 
		c1.frequency(freq)						#Set CH1 (gen) frequency 
		currHScale  = setHorizRes(scope,freq,2) #Set horizontal resolution for see 2 periods and read back truly adopted resolution
		scope.write("ACQuire:TYPE HRESolution") #set acquisition mode on high resolution only for CH2 autoscale

		timeDelay = currHScale*12*2*1.5  #calculate the sleep time for this frequency, for 2 cycles on screen + 50%
		#If the calculated value is less than 1 second, use 1 second
		if timeDelay<fixedTimeDelay:
			timeDelay = fixedTimeDelay 

		'''AUTOSCALE CH2 VERTICAL SCALE'''
		#Set CH2 vertical scale to the maximum voltage, and reference at the bottom of the screen
		if i<1:  #set starting value for the first 2 cycle
			scope.write("CHANnel2:SCALe 10")  
			scope.write("CHANnel2:OFFSet -38")
		else: #after 2 cycles, starts from the mean value of the last 2 elements for a faster settling
			verticalResCH2=(lastScale[i-2]+lastScale[i-1])/2
			verticalResCH2=setCH2(scope,verticalResCH2) #set channel 2 resolution and zero offset

		time.sleep(1) 
		vRead = float(scope.query("MEASure:ITEM? VMAX,CHANnel2"))  #first reading 
		verticalResCH2=numpy.round(vRead/8*1.5,2)                  #first adjustment try ad 60% the teoretical resolution
		verticalResCH2 = setCH2(scope,verticalResCH2)              #set resolution
		
		while(1):		
			#Check for over or under-resolution (clipping or too low resolution) with a shorter horizontale scale then the real measurmentes (for faster settling)
			time.sleep(timeDelay)
			vRead = float(scope.query("MEASure:ITEM? VMAX,CHANnel2")) #read voltage
			if vRead<verticalResCH2*4 or vRead>verticalResCH2*7.90: #respectively undervoltage and clipping
				verticalResCH2=numpy.round(vRead/8*1.3,4)
				#print("Clip or undervoltage")
			else:
				break
			if verticalResCH2<0.001: #check for minimum limits
				verticalResCH2=0.001 
			oldScale = float(scope.query("CHANnel2:SCALe?"))            #save last scale
			verticalResCH2 = setCH2(scope,verticalResCH2)               #set the resolution
			if oldScale == verticalResCH2: #if nothing changed we can't improve the scale and we have to exit
				break

		'''TAKE THE MEASUREMENT'''
		scope.write("ACQuire:TYPE AVERages")   #set acquisition mode on average for taking measurements
		time.sleep(timeDelay) #let the scope settle down
		CH1VMax[i] = scope.query("MEASure:ITEM? VMAX,CHANnel1")			#Read and save CH1 VMax
		CH2VMax[i] = scope.query("MEASure:ITEM? VMAX,CHANnel2")			#Read and save CH2 VMax
		PHASE[i] = scope.query("MEASure:ITEM? RPHase,CHANnel2,CHANnel1")#read phase between CH1 and CH2
		
		lastScale[i]=verticalResCH2; #save last vertical scale
		i = i + 1							#Increment index

	print("MEASURE COMPLETED\n_________________________") 			#verbosity

	db = 20*numpy.log10(CH2VMax/CH1VMax)	#Compute db

	originalSettings('restore',scope,readedParam) #restore scope's original settings

	plots(freqVect,db,PHASE) 				#plot frequency response diagrams
	
	scope.close()							#Stop communication with oscilloscope

	print("Done.") #verbosity


if __name__ == "__main__":
    main()