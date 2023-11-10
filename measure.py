from AutoProfiler import AutoProfiler,AutoPowerZone
import argparse

parser = argparse.ArgumentParser(description='Start the profiler')
parser.add_argument('--file', dest='filename',metavar='Filename',action='store',
                    default="default.hdf5",
                    help='Output file name, HDF5 format')

parser.add_argument('--command', dest='command',metavar='Command',action='store',
                    default="sleep",
                    help='Exacutable to profile')

parser.add_argument('--args', dest='args',metavar='Args',action='store',
                    default="",
                    help='Exacutable args')

parser.add_argument('--dt', dest='timestep',metavar='dt',action='store', 
                    default=0.1, type=float,
                    help='Profiler time step in Seconds [S]')

parser.add_argument('--auto', dest='autodetect',action='store_true', 
                    help='Autodetect the powerzones exposed with intel-rapl interfaxe')

args = parser.parse_args()

print("Start profiling")
if args.autodetect:
    powerzones=AutoPowerZone.autodetect()
else:
    powerzones=[AutoPowerZone("/sys/class/powercap/intel-rapl:0:0","intel-rapl"),
            AutoPowerZone("/sys/class/powercap/intel-rapl:1:0","intel-rapl"),
            AutoPowerZone("/sys/class/powercap/intel-rapl:0","intel-rapl"),
            AutoPowerZone("/sys/class/powercap/intel-rapl:1","intel-rapl")]

profiler=AutoProfiler(powerzones,command=args.command,args=args.args,dt=args.timestep,filename=args.filename)
profiler.start()
profiler.plot_profile()
