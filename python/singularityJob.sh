#!/bin/bash

#* usage: the first argument of this script is being run via Singularity
#* in the lmdfit-mini.sif container. Neccessary env variables are set
#* from the PandaRoot / KoalaSoft config.sh scripts (set $VMCWORKPATH
#* accordingly). Shell expansion works as expected, even in the argument.

#Load the Singularity module
module load tools/Singularity

#if image is >250MB, change the TMP dir to prevent a overfull /tmp directory on node 
SINGULARITY_TMPDIR=/localscratch/${SLURM_JOB_ID}/singularity_tmp/
export SINGULARITY_TMPDIR
mkdir -p $SINGULARITY_TMPDIR
LMDPATH=${LMDFIT_BUILD_DIR}/..

# TODO: this can pass only one argument, but there may be others.
# change it so an arbitrary number of args can be passed
singularity exec --env-file ${HOME}/LuminosityFit/lmdEnvFile.env ${HOME}/lmdfitNov22p1.sif bash -c ". \$VMCWORKDIR/build/config.sh -a ; ${1}"