#!/usr/bin/env python3

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

from attrs import evolve
from lumifit.cluster import ClusterJobManager
from lumifit.config import load_params_from_file
from lumifit.general import DirectorySearcher, envPath, getGoodFiles
from lumifit.gsi_virgo import create_virgo_job_handler
from lumifit.himster import create_himster_job_handler
from lumifit.paths import generateAbsoluteROOTDataPath, generateCutKeyword
from lumifit.scenario import (
    LumiDeterminationState,
    Scenario,
    SimulationDataType,
    SimulationState,
    SimulationTask,
)
from lumifit.types import (
    AlignmentParameters,
    ClusterEnvironment,
    DataMode,
    ExperimentParameters,
    ReconstructionParameters,
    SimulationParameters,
)
from wrappers.createRecoJob import create_reconstruction_job
from wrappers.createSimRecoJob import create_simulation_and_reconstruction_job

"""

Determines the luminosity of a set of Lumi_TrksQA_* files.

    This is pretty complicated and uses a lot of intermediate steps.
    Many of them have to be run on a cluster system, which is done
    with a slurm job handler.

This file needs one major rewrite, thats for sure.
- the logic is implemented as a GIANT state machine
- because job submission doesn't block
- job supervision is based on number of files;
- AND number of running jobs, even if these jobs belong to some other function
- but its not monitored if a given job has crashed
- and the entire thing is declarative, when object orientation would be better suited

For this rewrite, a better job supervision is needed. It would suffice already to
accept the jobID (or job Array ID) and simply poll once a minute if the jobs for that ID 
are still running.

If not, proceed.
If the needed files aren't there (but the jobs don't run anymore either), there is a runtime error.

"""


# TODO: add jobID or jobArrayID check here
def wasSimulationSuccessful(
    thisExperiment: ExperimentParameters,
    directory: Path,
    glob_pattern: str,
    min_filesize_in_bytes: int = 10000,
    is_bunches: bool = False,
) -> int:
    print(f"checking if job was successful. checking in path {directory}, glob pattern {glob_pattern}")
    # return values:
    # 0: everything is fine
    # >0: its not finished processing, just keep waiting
    # <0: something went wrong...
    required_files_percentage = 0.8
    return_value = 0

    files_percentage = getGoodFiles(
        directory,
        glob_pattern,
        min_filesize_in_bytes=min_filesize_in_bytes,
        is_bunches=is_bunches,
    )[1]

    print(f"files percentage (depends on getGoodFiles) is {files_percentage}")

    if files_percentage < required_files_percentage:
        if job_handler.get_active_number_of_jobs() > 0:
            print(f"there are still {job_handler.get_active_number_of_jobs()} jobs running")
            return_value = 1
        else:
            print(
                "WARNING: "
                + str((1 - files_percentage) * 100)
                + "% of input files ("
                + str(glob_pattern)
                + ") missing and no jobs on himster remaining..."
                + " Something went wrong here..."
            )
            return_value = -1

    return return_value


# ----------------------------------------------------------------------------
# ok we do it in such a way we have a step state for each directory and stacks
# we try to process
active_scenario_stack: List[Scenario] = []
waiting_scenario_stack: List[Scenario] = []


def simulateDataOnHimster(thisExperiment: ExperimentParameters, thisScenario: Scenario) -> Scenario:
    """
    Start a SLURM job for every SimulationTask assigned to a scenario.
    A scenario may hold multiple SimulationTasks at the same time that
    can be run concurrently (like reconstruction of DPM data with cut
    while at the same time res/acc data is generated)

    The simStates determine what step is currently being run:

    1:  Simulate Data (so box/dpm)
        Runs RunLmdSim and RunLmdReco to get MC Data and reconstructed
        tracks. This is the same as what the runSimulationReconstruction
        script does.

    2:  create bunch data objects
        first thing it should do is create bunches/binning dirs.
        Then call createMultipleLmdData which looks for these dirs.
        This also finds the reconstructed IP position from the TrksQA files.

    3:  Merge bunched Data

    Because the job submission via Slurm doesn't block, the function is exited
    even though jobs are still running. The Scenario objects therefore hold this state
    info so that the waiting method knows where it left off.

    parameters:
        thisExperiment: ExperimentParameters
            the experiment parameters
        thisScenario: Scenario
            the scenario to run
    """

    for task in thisScenario.SimulationTasks:
        print(f"running simulation of type {str(task.simDataType)} and path ({task.dirPath} at states:")
        print(f"current state: {str(task.simState)}")
        print(f"last state:    {str(task.lastState)}")

        data_keywords = []
        data_pattern = ""

        cut_keyword = generateCutKeyword(thisExperiment.dataPackage.recoParams)

        print(f"cut keyword is {cut_keyword}")

        merge_keywords = ["merge_data", "binning_300"]
        # if "v" in task.simType:
        if task.simDataType == SimulationDataType.VERTEX:
            data_keywords = ["uncut", "bunches", "binning_300"]
            data_pattern = "lmd_vertex_data_"
        # elif "a" in task.simType:
        elif task.simDataType == SimulationDataType.ANGULAR:
            data_keywords = [cut_keyword, "bunches", "binning_300"]
            data_pattern = "lmd_data_"
        elif task.simDataType == SimulationDataType.EFFICIENCY_RESOLUTION:
            data_keywords = [cut_keyword, "bunches", "binning_300"]
            data_pattern = "lmd_res_data_"
        else:
            raise NotImplementedError(f"Simulation type {task.simDataType} is not implemented!")

        # 1. simulate data
        if task.simState == SimulationState.START_SIM:
            os.chdir(lmd_fit_script_path)
            status_code = 1
            # if "er" in task.simType:
            if task.simDataType == SimulationDataType.EFFICIENCY_RESOLUTION:
                """
                efficiency / resolution calculation.

                Takes the offset of the IP into account.

                TODO: This needs to know the misalignment of the detector.
                """

                assert thisExperiment.resAccPackage.simParams is not None

                found_dirs = []
                # what the shit, this should never be empty in the first place
                if (task.dirPath != "") and (task.dirPath is not None):
                    temp_dir_searcher = DirectorySearcher(
                        [
                            thisExperiment.resAccPackage.simParams.simGeneratorType.value,
                            data_keywords[0],
                        ]  # look for the folder name including sim_type_for_resAcc
                    )
                    temp_dir_searcher.searchListOfDirectories(task.dirPath, thisExperiment.trackFilePattern)
                    found_dirs = temp_dir_searcher.getListOfDirectories()
                    print(f"found dirs now: {found_dirs}")
                else:
                    # path may be empty, then the directory searcher tries to find it
                    pass

                if found_dirs:
                    status_code = wasSimulationSuccessful(
                        thisExperiment,
                        found_dirs[0],
                        thisExperiment.trackFilePattern + "*.root",
                    )
                elif task.lastState < SimulationState.START_SIM:
                    # then lets simulate!
                    # this command runs the full sim software with box gen data
                    # (or dpm gen data for KOALA)
                    # to generate the acceptance and resolution information
                    # for this sample
                    # note: beam tilt and divergence are not necessary here,
                    # because that is handled completely by the model

                    # because we can't change the experiment config or
                    # anything in the simParams, recoParam, alignParams,
                    # we'll create temp objects here.
                    # TODO: the fuck we do, we take the params from the resAcc package!

                    # TODO: alignment part
                    # if alignement matrices were specified, we used them as a mis-alignment
                    # and alignment for the box simulations

                    # returnPath is the absolute path to the directory where the newly created data is stored
                    # TODO: this should'n be in the task anyway
                    returnPath = generateAbsoluteROOTDataPath(thisExperiment.resAccPackage)
                    job = create_simulation_and_reconstruction_job(
                        thisExperiment,
                        dataMode=DataMode.RESACC,
                        use_devel_queue=args.use_devel_queue,
                    )
                    job_manager.append(job)

                    task.dirPath = returnPath
                    thisScenario.acc_and_res_dir_path = returnPath
                    task.lastState = SimulationState.START_SIM

            elif task.simDataType == SimulationDataType.ANGULAR:
                """
                a is the angular case. this is the data set onto which the luminosity fit is performed.
                it is therefore REAL digi data (or DPM data of course) that must be reconstructed again
                with the updated reco parameter (like the IP position, cuts applied and alignment).
                note: beam tilt and divergence are not used here because
                only the last reco steps are rerun of the track reco
                """
                found_dirs = []
                status_code = 1
                # what the shit, this should never be empty in the first place
                if (task.dirPath != "") and (task.dirPath is not None):
                    temp_dir_searcher = DirectorySearcher(["dpm_elastic", data_keywords[0]])
                    temp_dir_searcher.searchListOfDirectories(task.dirPath, thisExperiment.trackFilePattern)
                    found_dirs = temp_dir_searcher.getListOfDirectories()

                else:
                    # path may be empty, then the directory searcher tries to find it
                    # TODO: wait thats a shit way to do this, implicit magic functions wtf?!
                    pass

                if found_dirs:
                    status_code = wasSimulationSuccessful(
                        thisExperiment,
                        found_dirs[0],
                        thisExperiment.trackFilePattern + "*.root",
                    )

                # oh boi that's bound to be trouble
                elif task.lastState < task.simState:
                    # TODO: alignment part

                    # TODO: this should'n be in the task anyway
                    returnPath = generateAbsoluteROOTDataPath(thisExperiment.resAccPackage)

                    job = create_reconstruction_job(
                        thisExperiment,
                        dataMode=DataMode.RESACC,
                        use_devel_queue=args.use_devel_queue,
                    )
                    job_manager.append(job)

                    task.dirPath = returnPath
                    thisScenario.filteredTrackDirectory = returnPath

                    # Simulation is done, so update the last_state
                    task.lastState = SimulationState.START_SIM

            elif task.simDataType == SimulationDataType.VERTEX:
                # check if the sim data is already there

                assert thisExperiment.dataPackage.MCDataDir is not None
                mcDataDir = thisExperiment.dataPackage.MCDataDir

                status_code = wasSimulationSuccessful(thisExperiment, mcDataDir, "Lumi_MC_*.root")

                # so this may seem odd, but since there aren't any jobs running yet and theres still
                # no files, the return code will actually be -1. better job supervision fixes that,
                # but thats for later
                # TODO: better job supervision
                if status_code < 0:
                    # vertex data must always be created without any cuts first
                    tempRecoPars = evolve(
                        thisExperiment.dataPackage.recoParams,
                        use_xy_cut=False,
                        use_m_cut=False,
                    )

                    # TODO: misalignment is important here. the vertex data can have misalignment (because it's real data)
                    # but it has no alignment yet. that is only for the second reconstruction
                    tempAlignPars = evolve(
                        thisExperiment.dataPackage.alignParams,
                        alignment_matrices_path=None,
                    )

                    # remember, this needs the TEMP reco params, not the real ones!
                    tempExperiment = evolve(thisExperiment, recoParams=tempRecoPars, alignParams=tempAlignPars)

                    job = create_simulation_and_reconstruction_job(
                        tempExperiment,
                        dataMode=DataMode.DATA,
                        use_devel_queue=args.use_devel_queue,
                    )
                    job_manager.append(job)

                    # just to be sure that no modified config is used after here
                    del tempRecoPars, tempAlignPars, tempExperiment

            else:
                raise ValueError(f"This tasks simType is {task.simDataType}, which is invalid!")

            if status_code == 0:
                print("found simulation files, skipping")
                task.simState = SimulationState.MAKE_BUNCHES
                task.lastState = SimulationState.START_SIM
            elif status_code > 0:
                print(f"still waiting for himster simulation jobs for {task.simDataType} data to complete...")
            else:
                raise ValueError("status_code is negative, which means number of running jobs can't be determined. ")

        # 2. create data (that means bunch data, create data objects)
        if task.simState == SimulationState.MAKE_BUNCHES:
            # check if data objects already exists and skip!
            temp_dir_searcher = DirectorySearcher(data_keywords)
            temp_dir_searcher.searchListOfDirectories(task.dirPath, data_pattern)
            found_dirs = temp_dir_searcher.getListOfDirectories()
            status_code = 1
            if found_dirs:
                status_code = wasSimulationSuccessful(
                    thisExperiment,
                    found_dirs[0],
                    data_pattern + "*",
                    is_bunches=True,
                )

            elif task.lastState < task.simState:
                os.chdir(lmd_fit_script_path)
                # bunch data
                # TODO: pass experiment config, or better yet, make class instead of script
                multiFileListCommand = []
                multiFileListCommand.append("python")
                multiFileListCommand.append("makeMultipleFileListBunches.py")
                multiFileListCommand.append("--filenamePrefix")
                multiFileListCommand.append(f"{thisExperiment.trackFilePattern}")
                multiFileListCommand.append("--files_per_bunch")
                multiFileListCommand.append("10")
                multiFileListCommand.append("--maximum_number_of_files")

                # FIXME: wait, doesn't this have to be done for BOTH data and resAcc?!
                multiFileListCommand.append(str(thisExperiment.dataPackage.recoParams.num_samples))
                multiFileListCommand.append(str(task.dirPath))

                print(f"Bash command for bunch creation:\n{' '.join(multiFileListCommand)}\n")
                _ = subprocess.call(multiFileListCommand)

                # TODO: pass experiment config, or better yet, make class instead of script
                # create data
                if task.simDataType == SimulationDataType.ANGULAR:
                    el_cs = thisScenario.elastic_pbarp_integrated_cross_secion_in_mb
                    lmdDataCommand = []
                    lmdDataCommand.append("python")
                    lmdDataCommand.append("createMultipleLmdData.py")
                    lmdDataCommand.append("--dir_pattern")
                    lmdDataCommand.append(data_keywords[0])
                    lmdDataCommand.append("--jobCommand")
                    lmdDataCommand.append(thisExperiment.LMDDataCommand)
                    lmdDataCommand.append(f"{thisScenario.momentum:.2f}")
                    lmdDataCommand.append(str(task.simDataType.value))  # we have to give the value because the script expects a/er/v !
                    lmdDataCommand.append(str(task.dirPath))
                    lmdDataCommand.append("../dataconfig_xy.json")

                    if el_cs:
                        lmdDataCommand.append("--elastic_cross_section")
                        lmdDataCommand.append(str(el_cs))
                        # bashcommand += " --elastic_cross_section " + str(el_cs)
                else:
                    lmdDataCommand = []
                    lmdDataCommand.append("python")
                    lmdDataCommand.append("createMultipleLmdData.py")
                    lmdDataCommand.append("--dir_pattern")
                    lmdDataCommand.append(data_keywords[0])
                    lmdDataCommand.append("--jobCommand")
                    lmdDataCommand.append(thisExperiment.LMDDataCommand)
                    lmdDataCommand.append(f"{thisScenario.momentum:.2f}")
                    lmdDataCommand.append(str(task.simDataType.value))  # we have to give the value because the script expects a/er/v !
                    lmdDataCommand.append(str(task.dirPath))
                    lmdDataCommand.append("../dataconfig_xy.json")

                print(lmdDataCommand)
                _ = subprocess.call(lmdDataCommand)

                # was apparently bunches
                task.lastState = SimulationState.MERGE

                lmdDataCommand.clear()

            if status_code == 0:
                print("skipping bunching and data object creation...")
                # state = 3
                task.simState = SimulationState.MERGE
                task.lastState = SimulationState.MAKE_BUNCHES
            elif status_code > 0:
                print(f"status_code {status_code}: still waiting for himster simulation jobs for {task.simDataType} data to complete...")
            else:
                # ok something went wrong there, exit this scenario and
                # push on bad scenario stack
                task.simState = SimulationState.FAILED
                raise ValueError("Something went wrong with the cluster jobs! This scenario will no longer be processed.")

        # 3. merge data
        if task.simState == SimulationState.MERGE:
            # check first if merged data already exists and skip it!
            temp_dir_searcher = DirectorySearcher(merge_keywords)
            temp_dir_searcher.searchListOfDirectories(task.dirPath, data_pattern)
            found_dirs = temp_dir_searcher.getListOfDirectories()
            if not found_dirs:
                os.chdir(lmd_fit_script_path)
                # merge data
                # if "a" in task.simType:
                if task.simDataType == SimulationDataType.ANGULAR:
                    mergeCommand = []
                    mergeCommand.append("python")
                    mergeCommand.append("mergeMultipleLmdData.py")
                    mergeCommand.append("--dir_pattern")
                    mergeCommand.append(data_keywords[0])
                    mergeCommand.append("--num_samples")
                    mergeCommand.append(str(bootstrapped_num_samples))
                    mergeCommand.append(str(task.simDataType.value))  # we have to give the value because the script expects a/er/v !
                    mergeCommand.append(str(task.dirPath))

                else:
                    mergeCommand = []
                    mergeCommand.append("python")
                    mergeCommand.append("mergeMultipleLmdData.py")
                    mergeCommand.append("--dir_pattern")
                    mergeCommand.append(data_keywords[0])
                    mergeCommand.append(str(task.simDataType.value))  # we have to give the value because the script expects a/er/v !
                    mergeCommand.append(str(task.dirPath))

                print("working directory:")
                print(f"{os.getcwd()}")
                print(f"running command:\n{mergeCommand}")
                _ = subprocess.call(mergeCommand)

            task.simState = SimulationState.DONE

        if task.lastState == SimulationState.FAILED:
            thisScenario.is_broken = True
            break

    # remove done tasks
    thisScenario.SimulationTasks = [simTask for simTask in thisScenario.SimulationTasks if simTask.simState != SimulationState.DONE]

    return thisScenario


def lumiDetermination(thisExperiment: ExperimentParameters, thisScenario: Scenario) -> None:
    lumiTrksQAPath = thisScenario.trackDirectory

    # open cross section file (this was generated by apps/generatePbarPElasticScattering
    # TODO: no, this is now in the experiment directory
    elastic_cross_section_file_path = lumiTrksQAPath.parent.parent / "elastic_cross_section.txt"
    if elastic_cross_section_file_path.exists():
        print("Found an elastic cross section file!")
        with elastic_cross_section_file_path.open() as f:
            content = f.readlines()
            thisScenario.elastic_pbarp_integrated_cross_secion_in_mb = float(content[0])
    elif thisScenario.lumiDetState == LumiDeterminationState.SIMULATE_VERTEX_DATA:
        print("No elastic cross section file found. This is ok if you are first simulating vertex data!")
    else:
        raise FileNotFoundError("ERROR! Can not find elastic cross section file! The determined Luminosity will be wrong!\n")

    print(f"processing scenario {lumiTrksQAPath} at step {thisScenario.lumiDetState}")

    finished = False

    # if lumiDetState == 1:
    if thisScenario.lumiDetState == LumiDeterminationState.SIMULATE_VERTEX_DATA:
        """
        State 1 simulates vertex data from which the IP can be determined.
        """
        if len(thisScenario.SimulationTasks) == 0:
            thisScenario.SimulationTasks.append(
                SimulationTask(dirPath=lumiTrksQAPath, simDataType=SimulationDataType.VERTEX, simState=SimulationState.START_SIM)
            )

        thisScenario = simulateDataOnHimster(thisExperiment, thisScenario)
        if thisScenario.is_broken:
            raise SystemError(f"ERROR! Scenario is broken! debug scenario info:\n{thisScenario}")

        # when all sim Tasks are done, the IP can be determined
        if len(thisScenario.SimulationTasks) == 0:
            thisScenario.lumiDetState = LumiDeterminationState.DETERMINE_IP
            thisScenario.lastLumiDetState = LumiDeterminationState.SIMULATE_VERTEX_DATA

    # if lumiDetState == 2:
    if thisScenario.lumiDetState == LumiDeterminationState.DETERMINE_IP:
        """
        state 2 only handles the reconstructed IP. If use_ip_determination is set,
        the IP is reconstructed from the uncut data set and written to a reco_ip.json
        file. The IP position will only be used from this file from now on.

        If use_ip_determination is false, the reconstruction will use the IP as
        specified from the reco params of the experiment config.

        Therefore, this is the ONLY place where thisScenario.ip[X,Y,Z] may be set.
        """
        if thisExperiment.dataPackage.recoParams.use_ip_determination:
            assert thisExperiment.resAccPackage.simParams is not None
            assert thisExperiment.dataPackage.recoIPpath is not None

            temp_dir_searcher = DirectorySearcher(["merge_data", "binning_300"])
            temp_dir_searcher.searchListOfDirectories(lumiTrksQAPath, "reco_ip.json")
            found_dirs = temp_dir_searcher.getListOfDirectories()
            #! FIXME: wait this can't be, if NOT found_dirs, the bash command can't use found_dirs[0]!
            # wait I think I know whats happening. If the reco_ip.json is not found, the bash command
            # will be called with some path?!, but will create the reco_ip.json
            # if the reco_ip.json is found, the bash command doen't have to be called,
            # because the reco_ip.json is already there.
            if not found_dirs:
                # 2. determine offset on the vertex data sample
                os.chdir(lmd_fit_bin_path)
                temp_dir_searcher = DirectorySearcher(["merge_data", "binning_300"])
                temp_dir_searcher.searchListOfDirectories(lumiTrksQAPath, ["lmd_vertex_data_", "of1.root"])
                found_dirs = temp_dir_searcher.getListOfDirectories()
                bashCommand = []
                bashCommand.append("./determineBeamOffset")
                bashCommand.append("-p")
                bashCommand.append(str(found_dirs[0]))
                bashCommand.append("-c")
                bashCommand.append("../../vertex_fitconfig.json")
                bashCommand.append("-o")
                bashCommand.append(thisExperiment.resAccPackage.recoIPpath)

                _ = subprocess.call(bashCommand)

            with open(str(thisExperiment.resAccPackage.recoIPpath), "r") as f:
                ip_rec_data = json.load(f)

            newRecoIPX = float("{0:.3f}".format(round(float(ip_rec_data["ip_x"]), 3)))  # in cm
            newRecoIPY = float("{0:.3f}".format(round(float(ip_rec_data["ip_y"]), 3)))
            newRecoIPZ = float("{0:.3f}".format(round(float(ip_rec_data["ip_z"]), 3)))

            # FIXME: I don't like this. Actually I hate this.
            # The experiment config is frozen for a reason.
            # But unfortunately there doesn't seem to be a better way

            # so, three param sets must be updated with the new IP:
            # - the dataPackage recoParams
            # - the resAccPackage simParams (both IP and theta min/max)
            # - the resAccPackage recoParams
            #
            # at least we know it can happen ONLY here

            max_xy_shift = math.sqrt(newRecoIPX**2 + newRecoIPY**2)
            max_xy_shift = float("{0:.2f}".format(round(float(max_xy_shift), 2)))

            resAccThetaMin = thisExperiment.resAccPackage.simParams.theta_min_in_mrad - max_xy_shift
            resAccThetaMax = thisExperiment.resAccPackage.simParams.theta_max_in_mrad + max_xy_shift

            thisExperiment.dataPackage.recoParams.setNewIPPosition(newRecoIPX, newRecoIPY, newRecoIPZ)
            thisExperiment.resAccPackage.simParams.setNewIPPosition(newRecoIPX, newRecoIPY, newRecoIPZ)
            thisExperiment.resAccPackage.simParams.setNewThetaAngles(resAccThetaMin, resAccThetaMax)
            thisExperiment.resAccPackage.recoParams.setNewIPPosition(newRecoIPX, newRecoIPY, newRecoIPZ)

            print("============================================================")
            print("                       Attention!                           ")
            print("     Experiment Config has been changed in memory!          ")
            print("This MUST only happen if you are using the IP determination!")
            print("============================================================")
            print("")
            print("Finished IP determination for this scenario!")
        else:
            print("Skipped IP determination for this scenario, using values from config.")

        thisScenario.lumiDetState = LumiDeterminationState.RECONSTRUCT_WITH_NEW_IP
        thisScenario.lastLumiDetState = LumiDeterminationState.DETERMINE_IP

    # if lumiDetState == 3:
    if thisScenario.lumiDetState == LumiDeterminationState.RECONSTRUCT_WITH_NEW_IP:
        # state 3a:
        # the IP position is now reconstructed. filter the DPM data again,
        # this time using the newly determined IP position as a cut criterion.
        # (that again means bunch -> create -> merge)
        # 3b. generate acceptance and resolution with these reconstructed ip values
        # (that means simulation + bunching + creating data objects + merging)
        # because this data is now with a cut applied, the new directory is called
        # something 1-100_xy_m_cut_real
        if len(thisScenario.SimulationTasks) == 0:
            thisScenario.SimulationTasks.append(SimulationTask(simDataType=SimulationDataType.ANGULAR, simState=SimulationState.START_SIM))
            thisScenario.SimulationTasks.append(SimulationTask(simDataType=SimulationDataType.EFFICIENCY_RESOLUTION, simState=SimulationState.START_SIM))

        # remember, the experiment config may now contain the updated IP
        thisScenario = simulateDataOnHimster(thisExperiment, thisScenario)

        if thisScenario.is_broken:
            raise ValueError(f"ERROR! Scenario is broken! debug scenario info:\n{thisScenario}")

        # when all simulation Tasks are done, the Lumi Fit may start
        if len(thisScenario.SimulationTasks) == 0:
            thisScenario.lumiDetState = LumiDeterminationState.RUN_LUMINOSITY_FIT
            thisScenario.lastLumiDetState = LumiDeterminationState.RECONSTRUCT_WITH_NEW_IP

    # if lumiDetState == 4:
    if thisScenario.lumiDetState == LumiDeterminationState.RUN_LUMINOSITY_FIT:
        """
        4. runLmdFit!

        - look where the merged data is, find the lmd_fitted_data root files.
        """

        os.chdir(lmd_fit_script_path)
        print("running lmdfit!")

        cut_keyword = generateCutKeyword(thisExperiment.dataPackage.recoParams)

        lumiFitCommand = []
        lumiFitCommand.append("python")
        lumiFitCommand.append("doMultipleLuminosityFits.py")
        lumiFitCommand.append("--forced_resAcc_gen_data")
        lumiFitCommand.append(f"{thisScenario.acc_and_res_dir_path}")
        lumiFitCommand.append("-e")
        lumiFitCommand.append(f"{args.ExperimentConfigFile}")
        lumiFitCommand.append(f"{thisScenario.filteredTrackDirectory}")
        lumiFitCommand.append(f"{cut_keyword}")
        lumiFitCommand.append(f"{lmd_fit_script_path}/{thisExperiment.fitConfigPath}")

        print(f"Bash command is:\n{' '.join(lumiFitCommand)}")
        _ = subprocess.call(lumiFitCommand)

        print("this scenario is fully processed!!!")
        finished = True

    # if we are in an intermediate step then push on the waiting stack and
    # increase step state
    if not finished:
        waiting_scenario_stack.append(thisScenario)


#! --------------------------------------------------
#!             script part starts here
#! --------------------------------------------------

parser = argparse.ArgumentParser(description="Lmd One Button Script")

parser.add_argument(
    "--bootstrapped_num_samples",
    type=int,
    default=1,
    help="number of elastic data samples to create via bootstrapping (for statistical analysis)",
)

parser.add_argument(
    "-e",
    "--experiment_config",
    dest="ExperimentConfigFile",
    type=Path,
    help="The Experiment.config file that holds all info.",
    required=True,
)

parser.add_argument(
    "--use_devel_queue",
    action="store_true",
    help="If flag is set, the devel queue is used",
)

args = parser.parse_args()


# load experiment config
loadedExperimentFromConfig: ExperimentParameters = load_params_from_file(args.ExperimentConfigFile, ExperimentParameters)

# read environ settings
lmd_fit_script_path = envPath("LMDFIT_SCRIPTPATH")
lmd_fit_bin_path = envPath("LMDFIT_BUILD_PATH") / "bin"

# make scenario config
thisScenario = Scenario(
    trackDirectory=loadedExperimentFromConfig.dataPackage.baseDataDir,
)
thisScenario.momentum = loadedExperimentFromConfig.dataPackage.recoParams.lab_momentum

# set via command line argument, usually 1
bootstrapped_num_samples = args.bootstrapped_num_samples

# * ----------------- find the path to the TracksQA files.
# the config only holds the base directory (i.e. where the first sim_params is)
dir_searcher = DirectorySearcher(["dpm_elastic", "uncut"])

# TODO: remember, we don't want to search, we want to HAVE the path in the config
dir_searcher.searchListOfDirectories(
    loadedExperimentFromConfig.dataPackage.baseDataDir,
    loadedExperimentFromConfig.trackFilePattern,
)
dirs = dir_searcher.getListOfDirectories()

print(f"\n\nINFO: found these dirs:\n{dirs}\n\n")

if len(dirs) > 1:
    raise ValueError(f"found {len(dirs)} directory candidates but it should be only one. something is wrong!")

elif len(dirs) < 1:
    # don't change thisScenario's trackDirectory, it was set during construction
    print("No dirs found, that means vertex data wasn't generated (or reconstructed) yet.")

else:
    # path has changed now for the newly found dir
    thisScenario.trackDirectory = dirs[0]


# * ----------------- create a scenario object. it resides only in memory and is never written to disk
print("creating scenario:", thisScenario.trackDirectory)

# * ----------------- check which cluster we're on and create job handler
if loadedExperimentFromConfig.cluster == ClusterEnvironment.VIRGO:
    job_handler = create_virgo_job_handler("long")
elif loadedExperimentFromConfig.cluster == ClusterEnvironment.HIMSTER:
    if args.use_devel_queue:
        job_handler = create_himster_job_handler("devel")
    else:
        job_handler = create_himster_job_handler("himster2_exp")
else:
    raise NotImplementedError("This cluster type is not implemented!")

# job threshold of this type (too many jobs could generate to much io load
# as quite a lot of data is read in from the storage...)
job_manager = ClusterJobManager(job_handler, 2000, 3600)


# * ----------------- start the lumi function for the first time.
# it will be run again because it is implemented as a state machine (for now...)
lumiDetermination(loadedExperimentFromConfig, thisScenario)

# TODO: okay this is tricky, sometimes scenarios are pushed to the waiting stack,
# and then they are run again? let's see if we can do this some other way.
# while len(waiting_scenario_stack) > 0:
while len(active_scenario_stack) > 0 or len(waiting_scenario_stack) > 0:
    for scen in active_scenario_stack:
        lumiDetermination(loadedExperimentFromConfig, scen)

    # clear active stack, if the scenario needs to be processed again,
    # it will be placed in the waiting stack
    active_scenario_stack = []
    # if all scenarios are currently processed just wait a bit and check again
    # TODO: I think it would be better to wait for a real signal and not just "when enough files are there"
    if len(waiting_scenario_stack) > 0:
        print("currently waiting for 15 min to process scenarios again")
        print("press ctrl C (ONCE) to skip this waiting round.")

        try:
            time.sleep(900)  # wait for 15min
        except KeyboardInterrupt:
            print("skipping wait.")

        print("press ctrl C again withing 3 seconds to kill this script")
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            print("understood. killing program.")
            sys.exit(1)

        active_scenario_stack = waiting_scenario_stack
        waiting_scenario_stack = []
