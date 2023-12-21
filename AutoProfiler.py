import numpy as np
import time
import h5py
import os
from subprocess import Popen, PIPE
import matplotlib.pyplot as plt
from pathlib import Path

class AutoFrequency:
    def __init__(self,path):
        self.path=path
        try:
            self.open_file()
            self.read_name()
        except:
            print(f"Errore apertura file {path}")        
            pass
        self.allocate()
        
    @staticmethod
    def autodetect():
        frequencyzones=list()
        #please remove os.listdir and use import glob; listing = glob.glob('C:/foo/bar/foo.log*')
        for path in os.listdir("/sys/devices/system/cpu/cpufreq/"):
            if 'policy' in path:
                frequencyzones.append(AutoFrequency(f"/sys/devices/system/cpu/cpufreq/{path}"))
        return frequencyzones

    def open_file(self):
        try:
            self.descriptor=open(f"{self.path}/scaling_cur_freq",'r')
        except Exception as e:
            print("QUI")
            print(f"Errore apertura fileeee {self.path}/scaling_cur_freq ")

    def read_name(self):
        try:
            file=open(f"{self.path}/affected_cpus",'r')
            self.name="cpu"+file.readline().rstrip()
            file.close()
        except Exception as e:
            print(f"Errore apertura/lettura file {e}")
            raise

    def __repr__(self):
        s=f"{self.name}\t{round(self.read_frequency()/1E6,2)} GHz"
        return s
    
    def allocate(self):
        self.data=list()
        return
    
    def store_read(self):
        #self.data.append(0)
        self.data+= self.read_frequency(),

    def reset(self):
        self.allocate()

    def read_frequency(self):
        #This could be faster than reading a single line
        value=int(self.descriptor.readlines()[0])
        self.descriptor.seek(0)
        return value
        
    
class AutoPowerZone:
    def __init__(self,path,interface):
        self.path=path
        self.interface=interface
        try:
            self.open_file()
            self.read_name()
        except:
            print("Errore apertura file")        
            pass
        self.allocate()
    
    def open_file(self):
        try:
            if self.interface=='intel-rapl':
                self.descriptor=open(f"{self.path}/energy_uj",'r')
            elif self.interface=='amd_energy':
                self.descriptor=open(f"{self.path}_input",'r')
            else:
                print("Interfaccia sbagliata")
                raise Exception
        except Exception as e:
            print(f"Errore apertura file {e}")
             
    def read_name(self):
        try:
            if self.interface=='intel-rapl': 
                file=open(f"{self.path}/name",'r')
                zone_name=self.path.split("/")[-1]
                self.name=zone_name+"/"+file.readline().splitlines()[0]
                file.close()
            elif self.interface=='amd_energy':
                file=open(f"{self.path}_label",'r')
                self.name="/amd_energy/"+file.readline().splitlines()[0]
                file.close()
        except Exception as e:
            print(f"Errore apertura/lettura file {e}")
            raise
            
    def read_energy(self):
        value=int(self.descriptor.readlines()[0])
        self.descriptor.seek(0)
        return value
    
    def __repr__(self):
        s=f"{self.name}\t{self.read_energy()} uj"
        return s
    
    def allocate(self):
        self.data=list()
        return
    
    def store_read(self):
        #self.data.append(0)
        self.data+= self.read_energy(),
        
    def reset(self):
        self.allocate()
            
    @staticmethod
    def autodetect(interface='intel-rapl'):
        powerzones=list()
        if interface == 'intel-rapl':
            for path in os.listdir("/sys/class/powercap"):
                if path != "intel-rapl" and path.find("mmio")==-1:
                    powerzones.append(AutoPowerZone(f"/sys/class/powercap/{path}",interface='intel-rapl'))
        elif interface == 'amd_energy':
            for path in os.listdir("/sys/class/hwmon/hwmon2"):
                if path.find("label")>1:
                    trim=path.find("_")
                    powerzones.append(AutoPowerZone(f"/sys/class/hwmon/hwmon2/{path[:trim]}",interface='amd_energy'))
        return powerzones

class AutoProfiler:
    def __init__(self,powerzones=None, command=None,args=None, dt=0.1,filename="default.hdf5"):
        self.dt=dt
        #Timestep in nS
        self.dtns=dt*1e9
        self.filename=filename
        if (command is not None): 
            # I can start profiling ! 
            self.powerzones=powerzones
            if len(powerzones)>0:
                print("Detected powerzones:\n[name]\t[current read]")
                for zone in self.powerzones:
                    print(zone)
            else:
                print("No powerzones detected")
            #Try to discover frequecy
            self.frequencyzones=AutoFrequency.autodetect()
            if len(self.frequencyzones) > 0:
                for zone in self.frequencyzones:
                    print(zone)                
            self.command=command
            self.args=args
            #How many time the process sleep between each cicle, higher the value, more precise is the measure
            self.sleeptime=dt
            self.time_dict=None
            print(f"Profiler command: {self.command}, args {self.args}, dt {self.dt}")


    def start(self):
        #lanciamo un altro programma ! poi profiliamo fintanto che sto coso gira, poi ci fermiamo.
        self.reset()
        t0=time.time_ns()
        process=Popen([self.command, *self.args.split(" ")], stdout=PIPE, stderr=PIPE)
        init_time=last_time=time.time_ns()
        looptime=self.dtns#- 5052469
        sleeptime=self.sleeptime/7000000
        while process.poll() is None:
            last_time=time.time_ns()
            self.cycle()
            while (time.time_ns()-last_time < looptime):
                time.sleep(sleeptime)
                #qui ho finito di profilare
           
        stdoutput=process.stdout.read().decode()
        events=list()
        print( time.get_clock_info("time"))
        for line in stdoutput.splitlines():
            if ("Start" in line) or ("End" in line):
                name_event,time_event=line.split(":")
                events.append((name_event,float(time_event)-t0/(10**(9))))
        if len(events)>0:
            print(events)
        else:
            print("No events recorded")
            events=None
        stderr=process.stderr.read().decode()
        print("Command output:")
        print(stdoutput)
        print(stderr)
        self.save(events=events,filename=self.filename)
        print(f"Profiling time: {round((last_time-init_time)/(10**9),2)} [s]")
        print("End profiling")

    def cycle(self):
        _ = tuple(map(AutoPowerZone.store_read,self.powerzones))
        _ = tuple(map(AutoFrequency.store_read,self.frequencyzones))
        #[i.store_read() for i in self.frequencyzones]
        #[i.store_read() for i in self.powerzones]
        
    def reset(self):
        for zone in self.powerzones:
            zone.reset()

    def __repr__(self):
        s=f"Profiler command: {self.command}, args {self.args}, dt {self.dt} [s]\nZones:\n"
        for zone in self.powerzones:
            s+=f"\t{zone.name}\n"
        return s   
        
    def save(self,filename="default.hdf5",events=None):
        '''
        This function is a DRAFT
        '''
        with h5py.File(filename, 'w') as f:
            for zone in self.powerzones:
                data=np.array(zone.data)
                dset = f.create_dataset(f"{zone.name}", data=np.diff(data/(1e6*self.dt)))
                dset.attrs['dt'] = self.dt
            if events is not None:
                g=f.create_group("events")
                for name_event,time_event in events:
                    g.attrs[name_event]=time_event
            for zone in self.frequencyzones:
                data=np.array(zone.data)
                dset = f.create_dataset(f"/frequency/{zone.name}", data=data/(1e6))
                dset.attrs['dt'] = self.dt

    def plot_profile(self,filename=None):
        if self.filename is not None:
            basename= Path(self.filename).stem
            self.profiles=dict()
            with h5py.File(self.filename, 'r') as f:
                plt.figure(figsize=(16,7),dpi=300)
                plt.title(f"{basename} power")
                for zone_group in f.keys():
                    #first plot the energy stuff and save to file
                    if zone_group != "frequency":
                        for zone_dataset in f[zone_group].keys():
                            dataset=f[zone_group][zone_dataset]
                            x_axis=dataset.attrs['dt']*np.arange(0,len(dataset))
                            y_axis=dataset[:]
                            if np.mean(y_axis)> 0.1:
                                plt.plot(x_axis,y_axis,label=f"{zone_group}/{zone_dataset}",lw=1)
                            else:
                                plt.plot(x_axis,y_axis,lw=1)
                if "events" in f:
                    for name_event,time_event in f["events"].attrs.items():
                        plt.axvline(x=time_event,color='r')
                        plt.text(time_event, 40, name_event,rotation=90,verticalalignment='center')

                plt.legend()
                plt.ylabel ("Power [W]")
                plt.xlabel("Time [s]")
                plt.savefig(f"{basename}_energy.png")
                
                #plot frequency stuff
                plt.figure(figsize=(16,7),dpi=300)
                plt.title(f"{basename} frequency")
                for zone_group in f.keys():
                    if zone_group == "frequency":
                        for zone_dataset in f[zone_group].keys():
                            dataset=f[zone_group][zone_dataset]
                            x_axis=dataset.attrs['dt']*np.arange(0,len(dataset))
                            y_axis=dataset[:]

                            if np.std(y_axis)> 0.5:
                                plt.plot(x_axis,y_axis,label=f"{zone_group}/{zone_dataset}",lw=1)
                            else:
                                plt.plot(x_axis,y_axis,lw=1)

                if "events" in f:
                    for name_event,time_event in f["events"].attrs.items():
                        plt.axvline(x=time_event,color='r')
                        plt.text(time_event, 40, name_event,rotation=90,verticalalignment='center')

                plt.legend()
                plt.ylabel ("Frequency GHz")
                plt.xlabel("Time [s]")
                plt.savefig(f"{basename}_frequency.png")
                plt.savefig("results_frequency.png")

