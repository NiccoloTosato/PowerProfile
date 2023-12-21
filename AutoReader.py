import numpy as np
import time
import h5py
import os
import math
from subprocess import Popen, PIPE
import matplotlib.pyplot as plt
from pathlib import Path
from abc import ABC, abstractmethod 

class AutoReader(ABC):
    @abstractmethod
    def __init__(self,path):
        pass

    def __len__(self):
        return len(self.data)

    @abstractmethod
    def autodetect(self):
        pass
    
    @abstractmethod
    def read_name(self):
        pass

    @abstractmethod
    def open_file(self):
        pass

    @abstractmethod
    def __repr__(self):
        pass
    
    def allocate(self):
        self.data=list()
        return
    
    def store_read(self):
        #self.data.append(0)
        self.data+= self.read(),

    def reset(self):
        self.allocate()

    def read(self):
        #This could be faster than reading a single line
        value=int(self.descriptor.readlines()[0])
        self.descriptor.seek(0)
        return value

class AutoFrequency(AutoReader):
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
        s=f"{self.name}\t{round(self.read()/1E6,2)} GHz"
        return s
    
    
class AutoPowerZone(AutoReader):
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
            
    def __repr__(self):
        s=f"{self.name}\t{self.read()} uj"
        return s
    
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

