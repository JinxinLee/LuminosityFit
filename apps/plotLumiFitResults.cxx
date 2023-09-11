#include "data/PndLmdAcceptance.h"
#include "data/PndLmdAngularData.h"
#include "data/PndLmdFitDataBundle.h"
#include "ui/PndLmdDataFacade.h"
#include "ui/PndLmdPlotter.h"

#include <iostream>
#include <iterator>
#include <map>
#include <sstream>
#include <vector>

#include "boost/filesystem.hpp"
#include "boost/property_tree/json_parser.hpp"
#include <boost/algorithm/string.hpp>

#include "TGaxis.h"
#include "TVectorD.h"

void plotLumiFitResults(std::vector<std::string> paths, int type,
                        const std::string &filter_string,
                        const std::string &output_directory_path,
                        TString filename_suffix) {
  std::cout << "Generating lumi plots for fit results....\n";

  // overwrite the default theta plot range if possible
  // plotter.setThetaPlotRange(0.5, 16.0);

  bool make_1d_plots(false);
  bool make_2d_plots(false);
  bool make_single_scenario_bookies(false);
  bool make_offset_overview_plots(false);
  bool make_ipspot_overview_plots(false);
  bool make_tilt_overview_plots(false);
  bool make_div_overview_plots(false);
  bool make_fit_range_dependency_plots(false);
  bool make_total_overview_result_file(false);

  if (type == 1)
    make_2d_plots = true;
  else if (type == 2)
    make_ipspot_overview_plots = true;
  else if (type == 3)
    make_offset_overview_plots = true;
  else if (type == 4)
    make_tilt_overview_plots = true;
  else if (type == 5)
    make_div_overview_plots = true;
  else if (type == 6)
    make_total_overview_result_file = true;

  // ================================= END CONFIG
  // ================================= //

  // A small helper class that helps to construct lmd data objects
  PndLmdDataFacade lmd_data_facade;

  LumiFit::PndLmdPlotter lmd_plotter;

  //	lmd_plotter.primary_dimension_plot_range.range_low = 0.5;
  //	lmd_plotter.primary_dimension_plot_range.range_high = 16.0;

  // get all data first
  std::vector<PndLmdFitDataBundle> all_data;

  PndLmdRuntimeConfiguration &lmd_runtime_config =
      PndLmdRuntimeConfiguration::Instance();

  lmd_runtime_config.setGeneralConfigDirectory(
      std::string(std::getenv("HOME")) + "/LuminosityFit");

  // lmd_runtime_config.readAcceptanceOffsetTransformationParameters(
  //    "offset_trafo_matrix.json");

  std::vector<std::string> ip_files;

  for (unsigned int i = 0; i < paths.size(); i++) {
    // ------ get files -------------------------------------------------------
    std::vector<std::string> file_paths = lmd_data_facade.findFilesByName(
        paths[i], filter_string, "lmd_fitted_data.root");
    std::cout << "found " << file_paths.size() << " file paths!\n";
    for (unsigned int j = 0; j < file_paths.size(); j++) {
      // FIXME: next lines are dirty... very unsafe
      // LOL WTF
      std::string ip_path(file_paths[j]);
      boost::replace_all(ip_path, "xy_m_cut_real", "uncut");
      boost::replace_all(ip_path, "lmd_fitted_data.root", "reco_ip.json");
      ip_files.push_back(ip_path);

      std::string fullpath = file_paths[j];
      TFile fdata(fullpath.c_str(), "READ");

      // read in data from a root file which will return a map of
      // PndLmdAngularData objects
      std::vector<PndLmdFitDataBundle> data_vec =
          lmd_data_facade.getDataFromFile<PndLmdFitDataBundle>(fdata);

      // append all data objects to the end of the corresponding data map
      // vectors
      all_data.insert(all_data.end(), data_vec.begin(), data_vec.end());
    }
  }

  for (unsigned int j = 0; j < all_data.size(); j++) {
    std::cout << "resolutions in object: "
              << all_data[j].getUsedResolutionsPool().size() << std::endl;
  }

  // =============================== BEGIN PLOTTING
  // =============================== //

  std::stringstream basepath;
  basepath << output_directory_path;

  if (!boost::filesystem::exists(output_directory_path)) {
    std::cout << "The output directory path you specified does not exist! "
                 "Please make sure you are pointing to an existing directory."
              << std::endl;
    return;
  }

  // now get all data bundles that are full phi
  std::vector<PndLmdFitDataBundle> full_phi_vec;
  std::vector<PndLmdElasticDataBundle> full_phi_reco_data_vec;

  LumiFit::LmdDimensionOptions phi_slice_dim_opt;
  phi_slice_dim_opt.dimension_type = LumiFit::PHI;
  phi_slice_dim_opt.track_param_type = LumiFit::LMD;
  phi_slice_dim_opt.track_type = LumiFit::MC;

  LumiFit::Comparisons::NegatedSelectionDimensionFilter filter(
      phi_slice_dim_opt);

  std::vector<PndLmdFitDataBundle>::iterator all_data_iter;
  for (all_data_iter = all_data.begin(); all_data_iter != all_data.end();
       ++all_data_iter) {

    std::vector<PndLmdElasticDataBundle> temp_full_phi_vec =
        lmd_data_facade.filterData(all_data_iter->getElasticDataBundles(),
                                   filter);

    if (temp_full_phi_vec.size() > 0)
      full_phi_vec.push_back(*all_data_iter);
    full_phi_reco_data_vec.reserve(full_phi_reco_data_vec.size() +
                                   temp_full_phi_vec.size());
    for (unsigned int i = 0; i < temp_full_phi_vec.size(); ++i)
      full_phi_reco_data_vec.push_back(temp_full_phi_vec[i]);
  }

  // if we just need the luminosity values and do not have to build the models
  // again
  // ---------- reco -- full phi stuff
  LumiFit::LmdDimensionOptions lmd_dim_opt;
  if (full_phi_reco_data_vec[0]
          .getPrimaryDimension()
          .dimension_options.dimension_type == LumiFit::THETA_X)
    lmd_dim_opt.dimension_type = LumiFit::THETA_X;

  LumiFit::Comparisons::DataPrimaryDimensionOptionsFilter dim_filter(
      lmd_dim_opt);
  full_phi_reco_data_vec =
      lmd_data_facade.filterData(full_phi_reco_data_vec, dim_filter);

  /*LumiFit::LmdDimensionOptions lmd_dim_opt2;
   lmd_dim_opt2.dimension_type = LumiFit::SECONDARY;
   lmd_dim_opt2.track_param_type = LumiFit::IP;
   lmd_dim_opt2.track_type = LumiFit::MC;

   LumiFit::Comparisons::NegatedSelectionDimensionFilter dim_filter2(
   lmd_dim_opt2);
   full_phi_reco_data_vec = lmd_data_facade.filterData(full_phi_reco_data_vec,
   dim_filter2);*/

  if (make_total_overview_result_file) {

    boost::property_tree::ptree all_scenario_tree;

    unsigned int counter(0);
    for (auto const &scenario : full_phi_reco_data_vec) {
      if (scenario.getFitResults().size() > 0 &&
          scenario.getSelectorSet().size() == 0) {
        PndLmdLumiFitResult fit_result;
        for (auto const &fit_res_pair : scenario.getFitResults()) {
          if (fit_res_pair.second.size() > 0) {
            bool div_smeared =
                fit_res_pair.first.getModelOptionsPropertyTree().get<bool>(
                    "divergence_smearing_active");
            if (div_smeared) {
              if (fit_res_pair.second[0].getFitStatus() == 0) {
                fit_result.setModelFitResult(fit_res_pair.second[0]);
                break;
              }
            } else {
              fit_result.setModelFitResult(fit_res_pair.second[0]);
            }
          }
        }
        // try to open ip measurement file... this is quite dirty but no time to
        // do it nice...
        boost::property_tree::ptree measured_values;
        read_json(ip_files[counter], measured_values);

        measured_values.put("lumi", fit_result.getLuminosity());
        measured_values.put("lumi_err", fit_result.getLuminosityError());
        for (auto const fit_param :
             fit_result.getModelFitResult().getFitParameters()) {
          if (fit_param.name.second.find("tilt_x") != std::string::npos) {
            measured_values.put("beam_tilt_x", fit_param.value);
            measured_values.put("beam_tilt_x_err", fit_param.error);
          } else if (fit_param.name.second.find("tilt_y") !=
                     std::string::npos) {
            measured_values.put("beam_tilt_y", fit_param.value);
            measured_values.put("beam_tilt_y_err", fit_param.error);
          } else if (fit_param.name.first.find("div") != std::string::npos) {
            if (fit_param.name.second.find("gauss_sigma_var1") !=
                std::string::npos) {
              measured_values.put("beam_divergence_x", fit_param.value);
              measured_values.put("beam_divergence_x_err", fit_param.error);
            } else if (fit_param.name.second.find("gauss_sigma_var2") !=
                       std::string::npos) {
              measured_values.put("beam_divergence_y", fit_param.value);
              measured_values.put("beam_divergence_y_err", fit_param.error);
            }
          }
        }
        std::stringstream label;
        label << "scenario_" << counter << ".measured";
        all_scenario_tree.add_child(label.str(), measured_values);

        label.str("");
        label << "scenario_" << counter << ".generated";
        // TODO: boost::property_tree::ptree gen_values(read from json file);
        // gen_values.put("lumi", scenario.getReferenceLuminosity());
        // all_scenario_tree.add_child(label.str(), gen_values);

        label.str("");
        label << "scenario_" << counter << ".momentum";
        all_scenario_tree.put(label.str(), scenario.getLabMomentum());

        std::pair<double, double> lumi = lmd_plotter.calulateRelDiff(
            fit_result.getLuminosity(), fit_result.getLuminosityError(),
            scenario.getReferenceLuminosity());
        std::cout << "lumi: " << lumi.first << " +- " << lumi.second
                  << std::endl;
        ++counter;
      }
    }
    std::stringstream filename;
    filename << basepath.str() << "/lumi_scenarios_overview.json";
    write_json(filename.str(), all_scenario_tree);
  }

  if (make_offset_overview_plots && full_phi_reco_data_vec.size() > 1) {
    std::stringstream filename;
    filename << basepath.str() << "/";
    filename << "plab_" << full_phi_reco_data_vec.begin()->getLabMomentum()
             << "/lumifit_result_ip_overview.root";

    TGraph2DErrors *graph =
        lmd_plotter.makeXYOverviewGraph(full_phi_reco_data_vec);

    TFile newfile(filename.str().c_str(), "RECREATE");
    graph->Write("overview_graph");
  }
  if (make_ipspot_overview_plots && full_phi_reco_data_vec.size() > 1) {
    std::stringstream filename;
    filename << basepath.str() << "/";
    filename << "plab_" << full_phi_reco_data_vec.begin()->getLabMomentum()
             << "/lumifit_result_ip_spot_overview.root";

    TGraph2DErrors *graph =
        lmd_plotter.makeIPSpotXYOverviewGraph(full_phi_reco_data_vec);

    TFile newfile(filename.str().c_str(), "RECREATE");
    graph->Write("overview_graph");
  }

  if (make_tilt_overview_plots && full_phi_reco_data_vec.size() > 1) {
    std::stringstream filename;
    filename << basepath.str() << "/";
    filename << "plab_" << full_phi_reco_data_vec.begin()->getLabMomentum()
             << "/lumifit_result_tilt_overview.root";

    std::cout << "build overview histogram with "
              << full_phi_reco_data_vec.size() << " values!" << std::endl;

    std::vector<PndLmdElasticDataBundle> filtered_reco_data_objects;

    // filter reco_data_ip_map for tilts below some threshold
    double threshold = 0.0007;
    std::vector<PndLmdElasticDataBundle>::iterator reco_data_object_iter;
    for (reco_data_object_iter = full_phi_reco_data_vec.begin();
         reco_data_object_iter != full_phi_reco_data_vec.end();
         reco_data_object_iter++) {
      /*TODO: if
      (reco_data_object_iter->getSimulationParametersPropertyTree().get<
          double>("beam_tilt_x") < threshold
          && reco_data_object_iter->getSimulationParametersPropertyTree().get<
              double>("beam_tilt_y") < threshold) {
        filtered_reco_data_objects.push_back(*reco_data_object_iter);
      }*/
    }

    TGraph2DErrors *graph =
        lmd_plotter.makeTiltXYOverviewGraph(filtered_reco_data_objects);
    TFile newfile(filename.str().c_str(), "RECREATE");
    graph->Write("overview_graph");

    std::pair<TGraphAsymmErrors *, TGraphAsymmErrors *> graphs =
        lmd_plotter.makeTiltXYOverviewGraphs(filtered_reco_data_objects);

    filename.str("");
    filename << basepath.str() << "/";
    filename << "plab_" << full_phi_reco_data_vec.begin()->getLabMomentum()
             << "/fit_results_tiltxy_overview.root";
    TFile newfile2(filename.str().c_str(), "RECREATE");
    graphs.first->Write("tilt_xy_reco_fit");
    graphs.second->Write("tilt_xy_truth");
  }

  if (make_div_overview_plots && full_phi_reco_data_vec.size() > 1) {
    std::stringstream filename;
    filename << basepath.str() << "/";
    filename << "plab_" << full_phi_reco_data_vec.begin()->getLabMomentum()
             << "/lumifit_result_div_overview.root";

    std::cout << "build overview histogram with "
              << full_phi_reco_data_vec.size() << " values!" << std::endl;

    std::vector<PndLmdElasticDataBundle> filtered_reco_data_objects;

    // filter reco_data_ip_map for tilts below some threshold
    double threshold = 0.0004;
    std::vector<PndLmdElasticDataBundle>::iterator reco_data_object_iter;
    for (reco_data_object_iter = full_phi_reco_data_vec.begin();
         reco_data_object_iter != full_phi_reco_data_vec.end();
         reco_data_object_iter++) {
      /*TODO: if
      (reco_data_object_iter->getSimulationParametersPropertyTree().get<
          double>("beam_divergence_x") < threshold
          && reco_data_object_iter->getSimulationParametersPropertyTree().get<
              double>("beam_divergence_y") < threshold) {
        filtered_reco_data_objects.push_back(*reco_data_object_iter);
      }*/
    }

    TGraph2DErrors *graph =
        lmd_plotter.makeDivXYOverviewGraph(filtered_reco_data_objects);
    TFile newfile(filename.str().c_str(), "RECREATE");
    graph->Write("overview_graph");

    std::pair<TGraphAsymmErrors *, TGraphAsymmErrors *> graphs =
        lmd_plotter.makeDivXYOverviewGraphs(filtered_reco_data_objects);

    filename.str("");
    filename << basepath.str() << "/";
    filename << "plab_" << full_phi_reco_data_vec.begin()->getLabMomentum()
             << "/fit_results_divxy_overview.root";
    TFile newfile2(filename.str().c_str(), "RECREATE");
    graphs.first->Write("div_xy_reco_fit");
    graphs.second->Write("div_xy_truth");
  }

  // now the stuff that really need to generate the model
  for (unsigned int fit_data_bundle_index = 0;
       fit_data_bundle_index < full_phi_vec.size(); ++fit_data_bundle_index) {
    std::stringstream filepath_base;
    filepath_base << basepath.str() << "/";
    filepath_base << "plab_"
                  << full_phi_vec[fit_data_bundle_index]
                         .getElasticDataBundles()[0]
                         .getLabMomentum()
                  << "/";
    filepath_base << lmd_plotter.makeDirName(
        full_phi_vec[fit_data_bundle_index].getElasticDataBundles()[0]);

    boost::filesystem::create_directories(filepath_base.str());

    // ok before doing anything just print out some stats about the fit bundle
    full_phi_vec[fit_data_bundle_index].printInfo();

    std::stringstream filepath;
    TCanvas c("", "", 1000, 700);

    lmd_plotter.setCurrentFitDataBundle(full_phi_vec[fit_data_bundle_index]);

    /*if (make_fit_range_dependency_plots) {
     NeatPlotting::PlotBundle plot_bundle =
     lmd_plotter.createLowerFitRangeDependencyPlotBundle(
     full_phi_reco_data_vec, lmd_dim_opt);

     filepath << filepath_base.str() << "/reco_lower_fit_range_dependency.pdf";

     NeatPlotting::PlotStyle plot_style;
     plot_bundle.drawOnCurrentPad(plot_style);
     c.SaveAs(filepath.str().c_str());
     }*/

    // create a vector of graph bundles (one entry for each fit option)
    if (make_single_scenario_bookies) {
      /*if (make_1d_plots) {
       filepath.str("");
       filepath << filepath_base.str() << "/fit_result_overview_booky.pdf";

       NeatPlotting::Booky booky = lmd_plotter.makeLumiFitResultOverviewBooky(
       full_phi_vec);
       booky.createBooky(filepath.str());
       }*/
      if (make_2d_plots) {
        filepath.str("");
        filepath << filepath_base.str() << "/fit_result_overview_booky_2d.pdf";

        NeatPlotting::Booky booky2 = lmd_plotter.create2DFitResultPlots(
            full_phi_vec[fit_data_bundle_index]);
        booky2.createBooky(filepath.str());
      }
    }

    // single reco plots
    NeatPlotting::PlotStyle single_plot_style;
    single_plot_style.x_axis_style.axis_text_style.text_size = 0.06;
    single_plot_style.y_axis_style.axis_text_style.text_size = 0.06;
    single_plot_style.z_axis_style.axis_text_style.text_size = 0.06;
    single_plot_style.x_axis_style.axis_title_text_offset = 0.95;
    single_plot_style.y_axis_style.axis_title_text_offset = 0.95;
    single_plot_style.z_axis_style.axis_title_text_offset = 0.95;

    NeatPlotting::PlotStyle diff_plot_style(single_plot_style);
    diff_plot_style.palette_color_style = 1;

    single_plot_style.z_axis_style.log_scale = true;

    // ---------- reco -- full phi stuff
    LumiFit::LmdDimensionOptions lmd_dim_opt;
    if (full_phi_vec[fit_data_bundle_index]
            .getElasticDataBundles()[0]
            .getPrimaryDimension()
            .dimension_options.dimension_type == LumiFit::THETA_X)
      lmd_dim_opt.dimension_type = LumiFit::THETA_X;

    LumiFit::Comparisons::DataPrimaryDimensionOptionsFilter filter(lmd_dim_opt);
    full_phi_reco_data_vec = lmd_data_facade.filterData(
        full_phi_vec[fit_data_bundle_index].getElasticDataBundles(), filter);

    for (unsigned int reco_data_obj_index = 0;
         reco_data_obj_index < full_phi_reco_data_vec.size();
         ++reco_data_obj_index) {

      // get rid of other cuts (i.e. on primary particles...)
      if (full_phi_reco_data_vec[reco_data_obj_index].getSelectorSet().size() >
          0)
        continue;

      const std::map<PndLmdFitOptions, std::vector<ModelFitResult>>
          &fit_results =
              full_phi_reco_data_vec[reco_data_obj_index].getFitResults();

      std::map<PndLmdFitOptions, std::vector<ModelFitResult>>::const_iterator
          fit_result_iter;
      for (fit_result_iter = fit_results.begin();
           fit_result_iter != fit_results.end(); ++fit_result_iter) {
        c.Clear();
        if (make_1d_plots &&
            fit_result_iter->first.getModelOptionsPropertyTree()
                    .get<unsigned int>("fit_dimension") == 1) {
          NeatPlotting::PlotBundle reco_plot_bundle =
              lmd_plotter.makeGraphBundle(
                  full_phi_reco_data_vec[reco_data_obj_index],
                  fit_result_iter->first, true, true, false);
          reco_plot_bundle.drawOnCurrentPad(single_plot_style);
          filepath.str("");
          filepath << filepath_base.str() << "/fit_result_reco.pdf";
          c.SaveAs(filepath.str().c_str());

          unsigned int used_acc_index =
              full_phi_reco_data_vec[reco_data_obj_index]
                  .getUsedAcceptanceIndices()[0];

          NeatPlotting::PlotBundle acc_bundle_1d =
              lmd_plotter.makeAcceptanceBundle1D(
                  full_phi_vec[fit_data_bundle_index]
                      .getUsedAcceptancesPool()[used_acc_index]);
          acc_bundle_1d.drawOnCurrentPad(single_plot_style);
          filepath.str("");
          filepath << filepath_base.str() << "/acceptance1d.pdf";
          c.SaveAs(filepath.str().c_str());
        }

        c.Clear();
        if (make_2d_plots &&
            fit_result_iter->first.getModelOptionsPropertyTree()
                    .get<unsigned int>("fit_dimension") == 2) {

          filepath.str("");
          filepath << filepath_base.str() << "/fit_result_reco_2d.root";

          lmd_plotter.makeFitBundle(full_phi_reco_data_vec[reco_data_obj_index],
                                    fit_result_iter->first, filepath.str());

          /*NeatPlotting::PlotBundle reco_plot_bundle =
           lmd_plotter.makeGraphBundle(
           full_phi_reco_data_vec[reco_data_obj_index],
           fit_result_iter->first, true, false, true);
           reco_plot_bundle.drawOnCurrentPad(single_plot_style);
           filepath.str("");
           filepath << filepath_base.str() << "/fit_result_reco_data_2d.pdf";
           c.SaveAs(filepath.str().c_str());

           reco_plot_bundle = lmd_plotter.makeGraphBundle(
           full_phi_reco_data_vec[reco_data_obj_index],
           fit_result_iter->first, false, true, true);
           reco_plot_bundle.drawOnCurrentPad(single_plot_style);
           filepath.str("");
           filepath << filepath_base.str() << "/fit_result_reco_model_2d.pdf";
           c.SaveAs(filepath.str().c_str());

           reco_plot_bundle = lmd_plotter.makeGraphBundle(
           full_phi_reco_data_vec[reco_data_obj_index],
           fit_result_iter->first, true, true, true);
           reco_plot_bundle.drawOnCurrentPad(diff_plot_style);
           filepath.str("");
           filepath << filepath_base.str() << "/fit_result_reco_diff_2d.pdf";
           c.SaveAs(filepath.str().c_str());

           unsigned int used_acc_index =
           full_phi_reco_data_vec[reco_data_obj_index].getUsedAcceptanceIndices()[0];

           NeatPlotting::PlotBundle acc_bundle_2d =
           lmd_plotter.makeAcceptanceBundle2D(
           full_phi_vec[fit_data_bundle_index].getUsedAcceptancesPool()[used_acc_index]);
           //acc_bundle_2d.plot_axis.x_axis_range.active = true;
           //acc_bundle_2d.plot_axis.x_axis_range.low = 0.002;
           //acc_bundle_2d.plot_axis.x_axis_range.high = 0.01;
           single_plot_style.z_axis_style.log_scale = false;
           acc_bundle_2d.drawOnCurrentPad(single_plot_style);
           single_plot_style.z_axis_style.log_scale = true;
           filepath.str("");
           filepath << filepath_base.str() << "/acceptance2d.png";
           c.SaveAs(filepath.str().c_str());*/
        }
      }
    }

    lmd_dim_opt.track_type = LumiFit::MC;

    LumiFit::Comparisons::DataPrimaryDimensionOptionsFilter filter_mc(
        lmd_dim_opt);
    std::vector<PndLmdElasticDataBundle> full_phi_mc_data_vec =
        lmd_data_facade.filterData(
            full_phi_vec[fit_data_bundle_index].getElasticDataBundles(),
            filter_mc);

    if (full_phi_mc_data_vec.size() == 1) {
      const std::map<PndLmdFitOptions, std::vector<ModelFitResult>>
          &fit_results = full_phi_mc_data_vec[0].getFitResults();
      if (fit_results.size() > 0) {

        if (make_2d_plots) {
          c.Clear();
          NeatPlotting::PlotBundle mc_plot_bundle = lmd_plotter.makeGraphBundle(
              full_phi_mc_data_vec[0], fit_results.begin()->first, true, false,
              false);
          mc_plot_bundle.drawOnCurrentPad(single_plot_style);
          filepath.str("");
          filepath << filepath_base.str() << "/fit_result_mc_data_2d.pdf";
          c.SaveAs(filepath.str().c_str());
        }
      }
    }

    std::cout << "mc accepted case..." << std::endl;
    lmd_dim_opt.track_type = LumiFit::MC_ACC;

    LumiFit::Comparisons::DataPrimaryDimensionOptionsFilter filter_mc_acc(
        lmd_dim_opt);
    std::vector<PndLmdElasticDataBundle> full_phi_mc_acc_data_vec =
        lmd_data_facade.filterData(
            full_phi_vec[fit_data_bundle_index].getElasticDataBundles(),
            filter_mc_acc);

    if (full_phi_mc_acc_data_vec.size() == 1) {
      const std::map<PndLmdFitOptions, std::vector<ModelFitResult>>
          &fit_results = full_phi_mc_acc_data_vec[0].getFitResults();

      if (make_2d_plots) {
        std::cout << "we have " << fit_results.size() << " fit results!\n";
        for (auto const &fit_result : fit_results) {
          filepath.str("");
          filepath << filepath_base.str() << "/fit_result_mc_acc_2d.root";
          std::cout << filepath.str() << std::endl;

          lmd_plotter.makeFitBundle(full_phi_mc_acc_data_vec[0],
                                    fit_result.first, filepath.str());
        }

        /*c.Clear();
         NeatPlotting::PlotBundle mc_acc_plot_bundle =
         lmd_plotter.makeGraphBundle(full_phi_mc_acc_data_vec[0],
         fit_results.begin()->first, true, false, false);
         mc_acc_plot_bundle.drawOnCurrentPad(single_plot_style);
         filepath.str("");
         filepath << filepath_base.str() << "/fit_result_mc_acc_data_2d.pdf";
         c.SaveAs(filepath.str().c_str());

         mc_acc_plot_bundle = lmd_plotter.makeGraphBundle(
         full_phi_mc_acc_data_vec[0], fit_results.begin()->first, false,
         true, false);
         mc_acc_plot_bundle.drawOnCurrentPad(single_plot_style);
         filepath.str("");
         filepath << filepath_base.str() << "/fit_result_mc_acc_model_2d.pdf";
         c.SaveAs(filepath.str().c_str());

         mc_acc_plot_bundle = lmd_plotter.makeGraphBundle(
         full_phi_mc_acc_data_vec[0], fit_results.begin()->first, true,
         true, false);
         mc_acc_plot_bundle.drawOnCurrentPad(diff_plot_style);
         filepath.str("");
         filepath << filepath_base.str() << "/fit_result_mc_acc_diff_2d.pdf";
         c.SaveAs(filepath.str().c_str());*/
      }
    }
  }
  // ================================ END PLOTTING
  // ================================ //
}

void displayInfo() {
  // display info
  std::cout << "Required arguments are: " << std::endl;
  std::cout << "list of directories to be scanned for vertex data" << std::endl;
  std::cout << "Optional arguments are: " << std::endl;
  std::cout << "-t [plot type: 1 = 2d fit result plots (default),\n"
            << "               2 = ip spot overview plot,\n"
            << "               3 = ip overview plot,\n"
            << "               4 = beam tilt overview plot,\n";
  std::cout << "-f [output filename suffix]" << std::endl;
  std::cout << "-o [output directory]" << std::endl;
  std::cout << "-s [filtering string, which has to appear in the full "
               "directory path for all found paths]"
            << std::endl;
}

int main(int argc, char *argv[]) {
  bool is_filename_suffix_set = false;
  std::string filename_suffix("fitresults");
  std::string filter_string("");
  int type(1);
  std::stringstream tempstream;
  tempstream << std::getenv("HOME") << "/plots";
  std::string output_directory_path(tempstream.str());

  int c;

  while ((c = getopt(argc, argv, "hf:s:o:t:")) != -1) {
    switch (c) {
    case 'f':
      filename_suffix = optarg;
      is_filename_suffix_set = true;
      break;
    case 's':
      filter_string = optarg;
      break;
    case 'o':
      output_directory_path = optarg;
      break;
    case 't':
      type = std::atoi(optarg);
      break;
    case '?':
      if (optopt == 'f' || optopt == 's' || optopt == 'o' || optopt == 't')
        std::cerr << "Option -" << optopt << " requires an argument."
                  << std::endl;
      else if (isprint(optopt))
        std::cerr << "Unknown option -" << optopt << "." << std::endl;
      else
        std::cerr << "Unknown option character" << optopt << "." << std::endl;
      return 1;
    case 'h':
      displayInfo();
      return 1;
    default:
      return 1;
    }
  }

  int argoffset = optind;

  if (argc > 1) {
    std::vector<std::string> paths;
    for (unsigned int i = argoffset; i < argc; i++) {
      paths.push_back(std::string(argv[i]));
    }
    plotLumiFitResults(paths, type, filter_string, output_directory_path,
                       filename_suffix);
  }

  return 0;
}
