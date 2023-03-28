# PowerProfile

## Run `measure.py`

## Requirements

```
$pip install -r requirements.txt
```
## Configure `intel-rapl`

Modify the following list with your power zones, pls check permissions

```
powerzones=[PowerZone("/sys/class/powercap/intel-rapl:0:0"),
            PowerZone("/sys/class/powercap/intel-rapl:1:0"),
            PowerZone("/sys/class/powercap/intel-rapl:0"),
            PowerZone("/sys/class/powercap/intel-rapl:1")]
```


## Run

```
$ python3 measure.py --file output.hdf5 --time 100 --dt 0.1
Start profiling
Profile time: 100.0 s, N* samples 1000, dt 0.1 s
Zones:
	dram
	dram
	package-0
	package-1
```