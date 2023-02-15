#!/bin/bash
#for file in /lustre/miifs05/scratch/him-specf/paluma/jinxin/Lmddata/plab_8.90GeV/box_theta_*/*/*/*/*
script="/home/lijinxin/LuminosityFit/build/bin"
recopath="1-50_xy_m_cut_real/no_alignment_correction/bunches_5/binning_300"
recopath4="1-50_xy_m_cut_real/no_alignment_correction/bunches_4/binning_300"
recopath1="1-50_xy_m_cut_real/no_alignment_correction/bunches_1/binning_300"
recopath2="1-50_xy_m_cut_real/no_alignment_correction/bunches_2/binning_300"
recopath3="1-50_xy_m_cut_real/no_alignment_correction/bunches_3/binning_300"
for file1 in /lustre/miifs05/scratch/him-specf/paluma/jinxin/Lmddata/plab_1.50GeV/box_theta_*/*/*/*/*
do
path="${file1}"
#echo $path
#python makeMultipleFileListBunches.py --filenamePrefix Lumi_TrksQA_ --files_per_bunch 10 --maximum_number_of_files 100 ${path}/1-50_xy_m_cut_real/no_alignment_correction/
#mkdir ${path}/${recopath}
#cp -r ../dataconfig_xy.json ${path}/${recopath}/dataconfig.json
#done
#${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_1.txt -o ${path}/${recopath} -n 0 -e 1.0 && ${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_2.txt -o ${path}/${recopath} -n 0 -e 1.0 && ${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_3.txt -o ${path}/${recopath} -n 0 -e 1.0 && ${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_4.txt -o ${path}/${recopath} -n 0 -e 1.0 && ${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_5.txt -o ${path}/${recopath} -n 0 -e 1.0
${script}/mergeLmdData -p ${path}/${recopath} -t e -n 1 -s 0 -f "lmd_acc_data_\d*.root"
#${script}/mergeLmdData -p ${path}/${recopath4} -t e -n 1 -s 0 -f "lmd_acc_data_\d*.root"
#${script}/mergeLmdData -p ${path}/${recopath1} -t e -n 1 -s 0 -f "lmd_acc_data_\d*.root"
#${script}/mergeLmdData -p ${path}/${recopath2} -t e -n 1 -s 0 -f "lmd_acc_data_\d*.root"
#${script}/mergeLmdData -p ${path}/${recopath3} -t e -n 1 -s 0 -f "lmd_acc_data_\d*.root"
${script}/mergeLmdData -p ${path}/${recopath} -t h -n 1 -s 0 -f "lmd_res_data_\d*.root"
#${script}/mergeLmdData -p ${path}/${recopath4} -t h -n 1 -s 0 -f "lmd_res_data_\d*.root"
#${script}/mergeLmdData -p ${path}/${recopath1} -t h -n 1 -s 0 -f "lmd_res_data_\d*.root"
#${script}/mergeLmdData -p ${path}/${recopath2} -t h -n 1 -s 0 -f "lmd_res_data_\d*.root"
#${script}/mergeLmdData -p ${path}/${recopath3} -t h -n 1 -s 0 -f "lmd_res_data_\d*.root"
#for file2 in /lustre/miifs05/scratch/him-specf/paluma/jinxin/Lmddata/plab_8.90GeV/box_theta_2.7-13.0mrad_recoil_corrected/*/*/*/*
#do
#path="${file2}"
#echo $path
#echo sbatch -A m2_him_exp -p himster2_exp --constraint=skylake --array=1-5 --job-name=createFitData -N 1 -n 1 -c 2 --mem-per-cpu=2500mb --time=0-03:00 --output=${path}/${recopath}/createFitData-%a.log --export=ALL,numEv=0,pbeam=8.9,input_path=${path}/1-50_xy_m_cut_real/no_alignment_correction,filelist_path=${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5,output_path=${path}/${recopath},config_path=${path}/${recopath}/dataconfig.json,type=er,elastic_cross_section=1.0  /home/lijinxin/LuminosityFit/python/singularityJob.sh /home/lijinxin/LuminosityFit/python/createLumiFitData.sh
done
#path="/lustre/miifs05/scratch/him-specf/paluma/jinxin/Lmddata/plab_8.90GeV/box_theta_2.7-13.0mrad_recoil_corrected/ip_offset_XYZDXDYDZ_0.0_0.0_0.0_0.0_0.0_0.0/beam_grad_XYDXDY_0.0_0.0_0.0_0.0/no_geo_misalignment/100000"
#echo ${path}/${recopath}
#python makeMultipleFileListBunches.py --filenamePrefix Lumi_TrksQA_ --files_per_bunch 10 --maximum_number_of_files 100 ${path}/1-50_xy_m_cut_real/no_alignment_correction/
#mkdir ${path}/${recopath}
#cp -r ../dataconfig_xy.json ${path}/${recopath}/dataconfig.json
#${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_1.txt -o ${path}/${recopath} -n 0 -e 1.0 && ${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_2.txt -o ${path}/${recopath} -n 0 -e 1.0 && ${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_3.txt -o ${path}/${recopath} -n 0 -e 1.0 && ${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_4.txt -o ${path}/${recopath} -n 0 -e 1.0 && ${script}/createLmdFitData -m 8.9 -t er -c ${path}/${recopath}/dataconfig.json -d ${path}/1-50_xy_m_cut_real/no_alignment_correction/ -f ${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5/filelist_5.txt -o ${path}/${recopath} -n 0 -e 1.0
#${script}/mergeLmdData -p ${path}/${recopath} -t e -n 1 -s 0 -f "lmd_acc_data_\d*.root"
#echo sbatch -A m2_him_exp -p himster2_exp --constraint=skylake --array=1-5 --job-name=createFitData -N 1 -n 1 -c 2 --mem-per-cpu=2500mb --time=0-03:00 --output=${path}/${recopath}/createFitData-%a.log --export=ALL,numEv=0,pbeam=8.9,input_path=${path}/1-50_xy_m_cut_real/no_alignment_correction,filelist_path=${path}/1-50_xy_m_cut_real/no_alignment_correction/bunches_5,output_path=${path}/${recopath},config_path=${path}/${recopath}/dataconfig.json,type=er,elastic_cross_section=1.0  /home/lijinxin/LuminosityFit/python/singularityJob.sh /home/lijinxin/LuminosityFit/python/createLumiFitData.sh
