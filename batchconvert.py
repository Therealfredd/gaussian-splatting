#
# Copyright (C) 2023, Inria
# GRAPHDECO research group, https://team.inria.fr/graphdeco
# All rights reserved.
#
# This software is free for non-commercial, research and evaluation use
# under the terms of the LICENSE.md file.
#
# For inquiries contact  george.drettakis@inria.fr
#

import os
import logging
from argparse import ArgumentParser
import shutil

# This Python script is based on the shell converter script provided in the MipNerF 360 repository.
parser = ArgumentParser("Colmap converter")
parser.add_argument("--no_gpu", action='store_true')
parser.add_argument("--skip_matching", action='store_true')
parser.add_argument("--source_path", "-s", required=True, type=str)
parser.add_argument("--camera", default="OPENCV", type=str)
parser.add_argument("--colmap_executable", default="", type=str)
parser.add_argument("--resize", action="store_true")
parser.add_argument("--magick_executable", default="", type=str)
args = parser.parse_args()

# Update args.source_path to point to the first subfolder
subfolders = [f.path for f in os.scandir(args.source_path) if f.is_dir()]
if subfolders:
    args.source_path = sorted(subfolders)[0]  # Assuming alphanumeric sorting
else:
    logging.error("No subdirectories found in the specified source path.")
    exit(1)

colmap_command = '"{}"'.format(args.colmap_executable) if len(args.colmap_executable) > 0 else "colmap"
magick_command = '"{}"'.format(args.magick_executable) if len(args.magick_executable) > 0 else "magick"
use_gpu = 1 if not args.no_gpu else 0

if not args.skip_matching: # If we are not skipping matching, we need to do feature extraction and matching.
    os.makedirs(args.source_path + "/distorted/sparse", exist_ok=True) # Make the sparse directory if it doesn't exist.

    ## Feature extraction #

        # THEO HERER - TAKEN THSESE OUT
       # --ImageReader.single_camera 1 \
      #  --ImageReader.camera_model " + args.camera + " \
    feat_extracton_cmd = colmap_command + " feature_extractor "\
        "--database_path " + args.source_path + "/distorted/database.db \
        --image_path " + args.source_path + "/input \
        --SiftExtraction.use_gpu " + str(use_gpu)
    exit_code = os.system(feat_extracton_cmd)
    if exit_code != 0:
        logging.error(f"Feature extraction failed with code {exit_code}. Exiting.")
        exit(exit_code)

    ## Feature matching
    feat_matching_cmd = colmap_command + " exhaustive_matcher \
        --database_path " + args.source_path + "/distorted/database.db \
        --SiftMatching.use_gpu " + str(use_gpu)
    exit_code = os.system(feat_matching_cmd)
    if exit_code != 0:
        logging.error(f"Feature matching failed with code {exit_code}. Exiting.")
        exit(exit_code)

    ### Bundle adjustment
    # The default Mapper tolerance is unnecessarily large,
    # decreasing it speeds up bundle adjustment steps.
    mapper_cmd = (colmap_command + " mapper \
        --database_path " + args.source_path + "/distorted/database.db \
        --image_path "  + args.source_path + "/input \
        --output_path "  + args.source_path + "/distorted/sparse")
   #  ALSO TOOK THIS OUT  --Mapper.ba_global_function_tolerance=0.000001")
    exit_code = os.system(mapper_cmd)
    if exit_code != 0:
        logging.error(f"Mapper failed with code {exit_code}. Exiting.")
        exit(exit_code)




for subfolder in subfolders:
    print(f"Processing subfolder: {subfolder}")

    ### Image undistortion for each subfolder
    img_undist_cmd = (colmap_command + " image_undistorter \
        --image_path " + os.path.join(subfolder, "input") + " \
        --input_path " + os.path.join(args.source_path, "distorted/sparse/0") + " \
        --output_path " + subfolder + " \
        --output_type COLMAP")
    exit_code = os.system(img_undist_cmd)
    if exit_code != 0:
        logging.error(f"Image undistortion failed for {subfolder} with code {exit_code}. Exiting.")
        continue  # Continue to next subfolder instead of exiting the entire script

    # Handle files within the 'sparse' directory of each subfolder
    sparse_folder = os.path.join(subfolder, "sparse")
    if not os.path.exists(os.path.join(sparse_folder, "0")):
        os.makedirs(os.path.join(sparse_folder, "0"), exist_ok=True)
    files = os.listdir(sparse_folder)
    for file in files:
        if file == '0':
            continue
        source_file = os.path.join(sparse_folder, file)
        destination_file = os.path.join(sparse_folder, "0", file)
        shutil.move(source_file, destination_file)

    if args.resize:
        print(f"Copying and resizing images in {subfolder}...")
        # Assume the existence of a "/images" subdirectory in each subfolder for the resizing logic
        image_source_path = os.path.join(subfolder, "images")
        if not os.path.exists(image_source_path):
            print(f"No images directory found in {subfolder}, skipping resizing.")
            continue

        for resize_factor, subfolder_suffix in [(2, "images_2"), (4, "images_4"), (8, "images_8")]:
            resized_images_path = os.path.join(subfolder, subfolder_suffix)
            os.makedirs(resized_images_path, exist_ok=True)
            files = os.listdir(image_source_path)

            for file in files:
                source_file = os.path.join(args.source_path, "images", file)

                destination_file = os.path.join(args.source_path, "images_2", file)
                shutil.copy2(source_file, destination_file)
                exit_code = os.system(magick_command + " mogrify -resize 50% " + destination_file)
                if exit_code != 0:
                    logging.error(f"50% resize failed with code {exit_code}. Exiting.")
                    exit(exit_code)

                destination_file = os.path.join(args.source_path, "images_4", file)
                shutil.copy2(source_file, destination_file)
                exit_code = os.system(magick_command + " mogrify -resize 25% " + destination_file)
                if exit_code != 0:
                    logging.error(f"25% resize failed with code {exit_code}. Exiting.")
                    exit(exit_code)

                destination_file = os.path.join(args.source_path, "images_8", file)
                shutil.copy2(source_file, destination_file)
                exit_code = os.system(magick_command + " mogrify -resize 12.5% " + destination_file)
                if exit_code != 0:
                    logging.error(f"12.5% resize failed with code {exit_code}. Exiting.")
                    exit(exit_code)

print("Done.")
