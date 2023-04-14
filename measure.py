from EnergyProfiler import PowerZone,Profiler
import argparse

parser = argparse.ArgumentParser(description='Start the profiler')
parser.add_argument('--file', dest='filename',metavar='Filename',action='store',
                    default="default.hdf5",
                    help='Output file name, HDF5 format')

parser.add_argument('--time', dest='time',metavar='ProfileTime',action='store',
                    default=10, type=float,
                    help='Profiler run time in Seconds [S]')

parser.add_argument('--dt', dest='timestep',metavar='dt',action='store', 
                    default=0.1, type=float,
                    help='Profiler time step in Seconds [S]')

parser.add_argument('--auto', dest='autodetect',action='store_true', 
                    help='Autodetect the powerzones exposed with intel-rapl interfaxe')

args = parser.parse_args()

print("Start profiling")
if args.autodetect:
    powerzones=PowerZone.autodetect("amd_energy")
else:
    powerzones=[PowerZone("/sys/class/powercap/intel-rapl:0:0","intel-rapl"),
            PowerZone("/sys/class/powercap/intel-rapl:1:0","intel-rapl"),
            PowerZone("/sys/class/powercap/intel-rapl:0","intel-rapl"),
            PowerZone("/sys/class/powercap/intel-rapl:1","intel-rapl")]

print(powerzones)

profiler=Profiler(powerzones,time=args.time,dt=args.timestep)
print(profiler)
profiler.start()
profiler.save(args.filename)
