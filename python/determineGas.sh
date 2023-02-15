#!/bin/bash  
  
for file in expConfigs/PANDA/8.9_lumi/xyz_0.3_*;  
do  
echo $file; 
./determineLuminosity.py -e $file;
done
