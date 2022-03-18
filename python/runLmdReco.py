import argparse
import json
import os

import alignment
import general
import reconstruction
from lumifit.alignment import AlignmentParameters
from lumifit.general import load_params_from_file
from lumifit.reconstruction import RecoParameters

parser.add_argument('force_level', metavar='force_level', type=int, default=0,
                    help='"force level 0: if directories exist with data\n"
                          "files no new simulation is started\n"
                          "force level 1: will do full reconstruction even if "
                          "this data already exists, but not geant simulation\n"
                          "force level 2: resimulation of everything!"')
parser.add_argument('dirname', metavar='dirname', type=str, nargs=1,
                    help='This directory for the outputfiles.')
parser.add_argument('pathname', metavar='pathname', type=str, nargs=1,
                    help='This the path to the outputdirectory')
parser.add_argument('macropath', metavar='macropath', type=str, nargs=1,
                    help='This the path to the macros')



if not os.path.isdir(args.pathname):
 os.system("mkdir -p args.pathname")

reco_params = RecoParameters(**load_params_from_file(path_mc_data + "/.."))
ali_params = AlignmentParameters(**load_params_from_file(path_mc_data + "/.."))

verbosityLevel: int = 0
start_evt: int = $((${num_evts} * ${filename_index}))
workpathname = "lokalscratch/" + ${SLURM_JOB_ID} + "/" + dirname
gen_filepath = workpathname + "/gen_mc.root"
scriptpath = os.getcwd()


#switch on "missing plane" search algorithm
misspl = True

#use cuts during trk seacrh with "CA". Should be 'false' if sensors missaligned!
trkcut = True
 if ali_params.alignment_matrices_path = "":
   trkcut = False

#merge hits on sensors from different sides. true=yes
mergedHits = True
## BOX cut before back-propagation
BoxCut = False
## Write all MC info in TrkQA array
WrAllMC = True

radLength = 0.32

prefilter = False
if reco_params.use_xy_cut :
  prefilter = True

check_stage_success "workpathname + "/Lumi_MC_${start_evt}.root""
if 0 == "$?" or  1 == "force_level":
  os.system("root -l -b -q 'runLumiPixel2Reco.C('{reco_params.num_events_per_sample}','${start_evt}',"'workpathname'", "'{ali_params.alignment_matrices_path}'", "'{ali_params.misalignment_matrices_path}'", '{ali_params.use_point_transform_misalignment}', 'verbositylvl')'")


check_stage_success "workpathname + "/Lumi_recoMerged_${start_evt}.root""
if 0 == "$?" or  1 == "force_level":
  os.system("root -l -b -q 'runLumiPixel2bHitMerge.C('{reco_params.num_events_per_sample}','${start_evt}',"'workpathname'",'verbositylvl')'")
  # copy Lumi_recoMerged_ for module aligner
  os.system("cp workpathname/Lumi_recoMerged_${start_evt}.root pathname/Lumi_recoMerged_${start_evt}.root")

os.system("cd scriptpath")
os.system("./runLmdPairFinder.sh")
os.system("./runLmdTrackFinder.sh")

