import time
import h5py
import os
import math
import numpy as np
import matplotlib.pyplot as plt
from subprocess import Popen, PIPE
from pathlib import Path
from AutoReader import AutoFrequency,AutoPowerZone
from collections import deque

def exhaust(generator):
    deque(generator, maxlen=0)
    
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
        looptime=self.dtns # - 5052469
        sleeptime=self.sleeptime/1000
        #step=0
        while process.poll() is None:
            last_time=time.time_ns()
            self.cycle()
            #step+=1
            while (time.time_ns()-last_time < looptime):
                time.sleep(sleeptime)
        #self.cycle()    
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
        profiling_time_ns=last_time-t0
        print(f"Profiling time: {round(profiling_time_ns/(10**9),2)} [s]")
        expected_timestep=math.floor(profiling_time_ns/self.dtns)
        print(f"Expected time step count {expected_timestep}")
        print(f"Sampled time step count {len(self.powerzones[0])}")
        print("End profiling")

    def cycle(self):
        exhaust(map(AutoPowerZone.store_read,self.powerzones))
        exhaust(map(AutoFrequency.store_read,self.frequencyzones))
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
                            dt=dataset.attrs['dt']
                            if np.mean(y_axis)> 0.1:
                                plt.plot(x_axis,y_axis,label=f"{zone_group}/{zone_dataset}",lw=1)
                            else:
                                plt.plot(x_axis,y_axis,lw=1)
                if "events" in f:
                    y_min,y_max = plt.gca().get_ylim()
                    for name_event,time_event in f["events"].attrs.items():
                        plt.axvline(x=time_event,color='r')
                        plt.text(time_event, (y_min+y_max)/2, name_event,rotation=90,verticalalignment='center')

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


