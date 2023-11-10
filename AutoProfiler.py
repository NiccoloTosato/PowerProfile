import numpy as np
import time
from gwpy.timeseries import TimeSeries,TimeSeriesDict
import h5py
import os
from subprocess import Popen, PIPE
import matplotlib.pyplot as plt

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
                self.name=file.readline().splitlines()[0]
                file.close()
        except Exception as e:
            print(f"Errore apertura/lettura file {e}")
            raise
            
    def read_energy(self):
        value=int(self.descriptor.readline())
        self.descriptor.seek(0)
        return value
    
    def __repr__(self):
        s=f"{self.name}\t{self.read_energy()} uj"
        return s
    
    def allocate(self):
        self.data=list()
        return
    
    def store_read(self):
        self.data.append(self.read_energy())
        return
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
                    powerzones.append(PowerZone(f"/sys/class/hwmon/hwmon2/{path[:trim]}",interface='amd_energy'))
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
            self.command=command
            self.args=args
            #How many time the process sleep between each cicle, higher the value, more precise is the measure
            self.sleeptime=dt/10
            self.time_dict=None
            print(f"Profiler command: {self.command}, args {self.args}, dt {self.dt}")


                
    def start(self):
        #lanciamo un altro programma ! poi profiliamo fintanto che sto coso gira, poi ci fermiamo.
        self.reset()
        process=Popen([self.command, self.args], stdout=PIPE, stderr=PIPE)
        init_time=last_time=time.time_ns()
        while process.poll() is None:
            while (time.time_ns()-last_time < self.dtns):
                time.sleep(self.sleeptime)
            self.cycle()
            last_time=time.time_ns()
        #qui ho finito di profilare
        #self.time_dict=self.to_timedict()
        print("Command output:")
        print(process.stdout.read())
        self.save(filename=self.filename)
        print(f"Profiling time: {round((last_time-init_time)/(10**9),2)} [s]")
        print("End profiling")

    def cycle(self):
        for zone in self.powerzones:
            zone.store_read()
            
    def reset(self):
        for zone in self.powerzones:
            zone.reset()
            
    def __repr__(self):
        s=f"Profiler command: {self.command}, args {self.args}, dt {self.dt} [s]\nZones:\n"
        for zone in self.powerzones:
            s+=f"\t{zone.name}\n"
        return s   
        
    def save(self,filename="default.hdf5"):
        with h5py.File(filename, 'w') as f:
            for zone in self.powerzones:
                data=np.array(zone.data)
                dset = f.create_dataset(f"{zone.name}", data=np.diff(data/(1e6*self.dt)))
                dset.attrs['dt'] = self.dt        
        #timedict=TimeSeriesDict()
        #i=0
        #for zone in self.powerzones:
            #power=np.diff(zone.data/(1e6*self.dt))
        #    name=zone.name
        #    if name in timedict:
        #        name+=f"_{i}"
        #        i+=1
        #    timedict[name]=TimeSeries(power,dx=self.dt,unit="Watts",name=zone.name)
    def plot_profile(self,filename=None):
        if self.filename is not None:
            self.profiles=dict()
            plt.figure(figsize=(16,7),dpi=300)
            with h5py.File(self.filename, 'r') as f:
                for zone_group in f.keys():
                    for zone_dataset in f[zone_group].keys():
                        dataset=f[zone_group][zone_dataset]
                        x_axis=dataset.attrs['dt']*np.arange(0,len(dataset))
                        plt.plot(x_axis,dataset[:],label=f"{zone_group}/{zone_dataset}")
                plt.legend()
                plt.ylabel ("Power [W]")
                plt.xlabel("Time [s]")
                plt.savefig("results.png")
    '''
    def plot(self):
        plot=self.time_dict.plot()
        ax = plot.gca()
        ax.set_xlim(0, self.time)
        ax.set_ylabel("Power [W]")
        ax.set_xlabel("Time [S]")
        plot.refresh()        
        plot.legend()        

    
    def load_profile(self,filename):
        self.time_dict=TimeSeriesDict.read(filename)
        for serie in self.time_dict:
            self.time=self.time_dict[serie].dt.value*len(self.time_dict[serie])
            break
        
    def plot(self):
        plot=self.time_dict.plot()
        ax = plot.gca()
        ax.set_xlim(0, self.time)
        ax.set_ylabel("Power [W]")
        ax.set_xlabel("Time [S]")
        plot.refresh()        
        plot.legend()
    
    def save(self,filename):
        try:
            time_dict=self.to_timedict()
            time_dict.write(filename)
        except:
            print("Non possibile salvare")     
            
    @staticmethod
    def metadata_apply(file_name,metadata):
        with h5py.File(file_name, "a") as f:
            try:
                metadata_group=f.create_group("metadata")
                for name,value in metadata.items():
                    metadata_group.attrs[name]=value
            except Exception as e:
                print("Qualcosa di strano")
                print(e)
'''
