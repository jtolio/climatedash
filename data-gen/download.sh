#!/bin/bash

cd data;

for timerange in "2009-01-01T12:00:00Z/2012-01-01T12:00:00Z" \
	"2049-01-01T12:00:00Z/2052-01-01T12:00:00Z" \
	"2089-01-01T12:00:00Z/2092-01-01T12:00:00Z"; do

starttime=$(echo $timerange | sed 's|/| |g' | awk '{print $1}' )
  endtime=$(echo $timerange | sed 's|/| |g' | awk '{print $2}' )
  starttimefixed=$(echo $starttime | sed 's/:/%3A/g' )
  endtimefixed=$(echo $endtime | sed 's/:/%3A/g')

for driver in CanESM2 CNRM-CM5 ERA-Int EC-EARTH GFDL-ESM2M GEMatm-Can GEMatm-MPI MPI-ESM-LR MPI-ESM-MR; do # HadGEM2-ES
for model in CRCM5-UQAM CRCM5-OUR CanRCM4 HIRHAM5 RCA4 WRF; do # RegCM4 

for variable in rsds hurs sfcWind prec tmax tmin tmean; do
for experiment in rcp85; do
for frequency in day; do # ann mon seas day; do
for grid in NAM-22i; do # NAM-44i NAM-22i NAM-11; do

filenamebase=$variable.$experiment.$driver.$model.$frequency.$grid

if [ -e $filenamebase.mbcn-gridMET.$starttime.$endtime.nc ] || \
	[ -e $filenamebase.mbcn-Daymet.$starttime.$endtime.nc ] || \
	[ -e $filenamebase.raw.$starttime.$endtime.nc ]; then
	continue;
fi

for bias in mbcn-gridMET mbcn-Daymet raw; do

if wget -O $filenamebase.$bias.$starttime.$endtime.nc "https://tds.ucar.edu/thredds/ncss/grid/datazone/cordex/data/$bias/$grid/$frequency/$model/$driver/$experiment/$variable/$filenamebase.$bias.nc?var=$variable&time_start=$starttimefixed&time_end=$endtimefixed&timeStride=1&accept=netcdf3"; then
	break
else
	rm -f $filenamebase.$bias.$starttime.$endtime.nc
fi

done

done
done

done

done
done

done
done

