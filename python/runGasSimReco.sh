#!/bin/bash  
  
for file in expConfigs/PANDA/8.9_lumi/*;  
do  
echo $file; 
./runSimulationReconstruction.py -e $file;
done
