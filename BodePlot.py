'''
# RIGOL DS1054Z - FEELTECH FY32xx AUTOMATED FREQUENCY RESPONSE ANALYSIS
### Francesco Nastrucci - frenzi37i - 10/01/2021

TESTED ON WINDOWS ONLY

## Features
*	Amplitude and phase semilogarithmic plots
* Average acquisition mode, with 2 waves average (for f>2Hz) or high resolution mode (for f<2Hz)
*	Logaritmic or linear frequencies span 
*	Automated setup
*	Automated restore of the previous scope's settings
*	Automated fine adjustment of the vertical scale for maximized voltage sensitivity, with clipping detection 
*       Sense measurements anomalies, and redo the affected measurements. If anomaly are still present,
	data are plotted anyway but the affected ones are highlighted with a red octagon. 
*   For very low amplitude values (vpeak<3.5mV) phases measurements are considered not accurate and are marked with yellow circle in the phase plot
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

'''

###################################################################################
###############################  USER SETTINGS ####################################
# INSTRUMENTS CONNECTIONS PORT
scopeAddress='USB0::0x1AB1::0x04CE::DS1ZA223107793::INSTR' #Rigol 1054Z Address
sigGenCOMPort = 'COM19' #USB Serial port for the FeelTech FY32xx
###################################################################################


from numpy.core.fromnumeric import mean
from numpy.lib.arraysetops import ediff1d
import pyvisa
import feeltech
import time
import numpy
import matplotlib.pyplot as plt
import math

######################################################################################
'''READ USER SETTINGS FROM CMD LINE'''
def cmnd(text,lval,uval,TYpe):  #checks user inputted values
	while(1):
		val = input(text)
		
		try:
			if TYpe=='f':
				if float(val)<lval or float(val)>uval:	
					print("Inputted value is out of bound; [",lval,",",uval,"]")
				else:
					return float(val)
			if TYpe=='i':
				if int(val)<lval or int(val)>uval:	
					print("Inputted value is out of bound; [",lval,",",uval,"]")
				else:
					return int(val)
		except:
			if TYpe=='i':
				t='integer'
			else:
				t=''
			print("Inputted value must be a",t,"number!")

def readUserSettings():
	print("\n     ANALYSIS SETUP     ")
	print("-"*25)
	startFreq = cmnd("Start frequency [Hz]? ",0.2,10*10**6,'f')
	endFreq = cmnd("End frequency [Hz]? ",startFreq+0.5,10*10**6,'f')
	freqSteps = cmnd("Number of steps? ",2,10000,'i')
	logAnalysis = cmnd("Frequency sweep = LINEAR [0] or LOGARITHMIC[1] ? ",0,1,'i')
	vpp = cmnd("Peak to Peak generated voltage? [V] ",0.05,20,'f')
	waveVMax = vpp/2	
	return [startFreq,endFreq,freqSteps,waveVMax,logAnalysis]

######################################################################################

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
    

	'''VOLTAGE MEASUREMENTS'''
	scope.write("MEASure:CLEar ALL")				     #Clear all measurement items
	scope.write("MEASure:ITEM VMAX,CHANnel1")			 #Create the VTOP measurement item for CH1
	scope.write("MEASure:ITEM VMAX,CHANnel2")			 #Create the VTOP measurement item for CH2
	scope.write("MEASure:ITEM RPHase,CHANnel2,CHANnel1") #Create the phase measurement between CH2 and CH1

	'''ACQUISITION MODE SETUP'''
	scope.write("ACQuire:MDEPth AUTO")      #set automatic memory depth
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
	scope.write("TRIGger:EDGe:LEVel ",str(numpy.round(waveVMax*0.7,1)))
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
'''MEASUREMENT FUNCTION'''
def MEASURE(scope,c1,i,freqVect,fixedTimeDelay,lastScale):
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
	CH1VMax = scope.query("MEASure:ITEM? VMAX,CHANnel1")			#Read and save CH1 VMax
	CH2VMax = scope.query("MEASure:ITEM? VMAX,CHANnel2")			#Read and save CH2 VMax
	PHASE = scope.query("MEASure:ITEM? RPHase,CHANnel2,CHANnel1")#read phase between CH1 and CH2
	
	lastScale[i]=verticalResCH2; #save last vertical scale
	return [CH1VMax,CH2VMax,PHASE]

######################################################################################
'''UNDER VOLTAGE DETECTION'''
def underVDetect(CH2VMax):
	#detect if there are measured voltage under 3.5mV
	elem = []
	for i,e in enumerate(CH2VMax):
		if e<0.0035:
			elem.append(i)
	return elem

######################################################################################
'''ANOMALY DETECTION'''
def anomalyDetect(PHASE,underVElem):
	#Phase data are heavily wrong when readings fail, so we check for anomaly in phase; 
	#we avoid elements with too lower voltage, because thier phases are unreliable; these elements are not marked as anomalies
	detect = False
	elements =[]
	for i,elem in enumerate(PHASE): #fer all the elements in phase array 
		#check if this element is an undervoltage one
		isUV=False
		for e in underVElem:
			if i==e:
				isUV=True

		if isUV == False: #If this is not an undervoltage element, we can check if this is an outlier
			PH = numpy.delete(PHASE,numpy.concatenate(([i],numpy.array(underVElem)))); #delete current element and undervoltage ones from the buffer vector
			if abs(elem)>abs(mean(PH))*20:  #If the current phase is greater than 20 times the mean of the phase array without this value, this is an anomaly
				detect = True	
				elements.append(i)
	
	return [detect,elements]

######################################################################################
'''PLOT FUNCTION'''
def plots(freqVect,db,PHASE,detectAnomaly,elementsAnomaly,elementUV):
	print("Plotting...")
	fig,(f1,f2)=plt.subplots(2,sharex=True)
	#plt.ion()

	'''Amplitude plot'''
	f1.plot(freqVect,db,marker='o')	
	f1.set(xlabel='f [Hz]',ylabel='dB', title='Amplitude')
	f1.axhline(-3,linestyle="--",color='r') #-3db horizontal line

	'''Phase plot'''
	f2.plot(freqVect,PHASE,marker='o')			#Graph data
	f2.set(xlabel='f [Hz]',ylabel='phase [°]', title='Phase')

	'''Plot anomaly indicators if anomaly present'''
	if detectAnomaly == True: 
		f1.plot(freqVect[elementsAnomaly],db[elementsAnomaly],marker='H',color='r',linestyle = 'None')
		f2.plot(freqVect[elementsAnomaly],PHASE[elementsAnomaly],marker='H',color='r',linestyle = 'None')

	'''Plot undervoltages unreliables phases'''
	if len(elementUV) > 0: 
		f2.plot(freqVect[elementUV],PHASE[elementUV],marker='o',color='y',linestyle = 'None')

	f1.grid(True)
	f2.grid(True)
	plt.xscale('symlog')
	plt.show()

######################################################################################

def main():
	global scopeAddress
	global sigGenCOMPort

	print("\n########### FREQUENCY RESPONSE ANALYSIS SCRIPT #############")	

	[startFreq,endFreq,freqSteps,waveVMax,logAnalysis]=readUserSettings()  #read settings from user with error checks
	
	'''for debug
	startFreq = 10
	endFreq =1000
	freqSteps = 5
	waveVMax = 1
	logAnalysis = True
	'''

	fixedTimeDelay = 3  #Adjust the time delay between frequency increments [s]

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
	print("_"*30,"\nConnecting to signal generator...")
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
	print("Setup completed.")

	'''MEASUREMENTS'''
	print("_"*30)
	print("Starting measurements\nWait for scope to settle...")
	time.sleep(fixedTimeDelay)					#Time delay
	print("MEASUREMENT STARTED")
    
	for i in range(0,freqSteps):
		print(numpy.floor(100*((i+1)/freqSteps)),"% - Analyzing ",numpy.round(freqVect[i],2)," Hz")   #print completed process percentage
		[CH1VMax[i],CH2VMax[i],PHASE[i]] = MEASURE(scope,c1,i,freqVect,fixedTimeDelay,lastScale) 	  #TAKE MEASUREMENTS
    
	db = 20*numpy.log10(CH2VMax/CH1VMax)	#Compute db
	
	'''TOO LOW AMPLITUDE VALUE DETECTION'''
	#If amplitude is too low (<2mV), phase detection is unreliable, so anomaly detection have to discard those values
	underVElem = underVDetect(CH2VMax) 

	'''ANOMALY DETECTION'''	
	[detect,elements] = anomalyDetect(PHASE,underVElem)   #Check for anomaly in calculated data based on phase values, avoiding usigng measuremnt with voltage lower than 2mV

	if detect ==True: 
		print("Detected anomalies for measurements: ",elements,"\nTrying to redo these measurements lowering the trigger.")
		#If something is fail maybe is due to a too high trigger; can try to lower it. 
		scope.write("TRIGger:EDGe:LEVel ",str(numpy.round(waveVMax*0.2,1)))

		for j in range(1,4): #repeat meauserements at maximum 4 times if wring values are detected; then plot the graph anyway
			for i in elements: 
				[CH1VMax[i],CH2VMax[i],PHASE[i]] = MEASURE(scope,c1,i,freqVect,fixedTimeDelay,lastScale) #Try to retake failed measurements

			[detect,newElements] = anomalyDetect(PHASE,underVElem) #recheck for anomaly detect

			if detect == True: #if anomaly detected again
				if newElements == elements:  #if are the same ones, exit from the cycle.
					print("Anomalies still present on measurements: ",elements)
					break
				else:   #if are new ones, try to correct them
					print("Other anomalies detected on measurements: ",newElements,"\nTry to redo these ones")
					elements=newElements #update element to analyze and try to reanalyze 
			else:
				print("Anomalies resolved.") #if no more anomalies are detected, we are ok. 
				break


	print("MEASUREMENT COMPLETED") 			#verbosity

	print("_"*30)

	originalSettings('restore',scope,readedParam) #restore scope's original settings

	plots(freqVect,db,PHASE,detect,elements,underVElem) 	#plot frequency response diagrams
	
	scope.close()								#Stop communication with oscilloscope

	print("Done.") #verbosity


if __name__ == "__main__":
    main()
