import numpy as np
import time
from gwpy.timeseries import TimeSeries,TimeSeriesDict
import h5py

class PowerZone:

    def __init__(self,path):
        self.path=path
        try:
            self.open_file()
            self.read_name()
        except:
            print("Errore apertura file")        
            pass
    
    def open_file(self):
        try:
            self.descriptor=open(f"{self.path}/energy_uj",'r')
        except Exception as e:
            print(f"Errore apertura file {e}")
             
    def read_name(self):
        try:
            file=open(f"{self.path}/name",'r')
            self.name=file.readline().splitlines()[0]
            file.close()
        except Exception as e:
            print(f"Errore apertura file {e}")
            raise
            
    def read_energy(self):
        value=int(self.descriptor.readline())
        self.descriptor.seek(0)
        return value
    
    def __repr__(self):
        s=f"{self.name} {self.read_energy()} uj"
        return s
    
    def allocate(self,samplenumber):
        self.data=np.zeros(samplenumber)
        self.counter=0
        return
    
    def store_read(self):
        self.data[self.counter]=self.read_energy()
        self.counter+=1
        return
    
    def reset(self):
        self.counter=0
    
        
        
        
class Profiler:
    def __init__(self,powerzones=None,time=None,dt=None):
        if (powerzones is not None) and (time is not None): 
            self.powerzones=powerzones
            self.time=time
            #How many samples I will read for each PowerZone
            self.sample=int(time/dt)
            self.dt=dt
            #Timestep in nS
            self.dtns=dt*1e9
            #How many time the process sleep between each cicle, higher the value, more precise is the measure
            self.sleeptime=dt/10
            #allocate one array for each zone
            for zone in self.powerzones:
                zone.allocate(self.sample)
            self.time_dict=None

    def start(self):
        self.reset()
        last_time=time.time_ns()
        for _ in range(self.sample):
            while (time.time_ns()-last_time < self.dtns):
                time.sleep(self.sleeptime)
            self.cycle()
            last_time=time.time_ns()
        self.time_dict=self.to_timedict()
            
    def cycle(self):
        for zone in self.powerzones:
            zone.store_read()
            
    def reset(self):
        for zone in self.powerzones:
            zone.reset()
            
    def __repr__(self):
        s=f"Profile time: {self.time} s, N* samples {self.sample}, dt {self.dt} s\nZones:\n"
        for zone in self.powerzones:
            s+=f"\t{zone.name}\n"
        return s     
    
    def to_timedict(self):
        timedict=TimeSeriesDict()
        i=0
        for zone in self.powerzones:
            power=np.diff(zone.data/(1e6*self.dt))
            timedict[zone.name+"-"+str(i)]=TimeSeries(power,dx=self.dt,unit="Watts",name=zone.name)
            i+=1
        return timedict
    
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