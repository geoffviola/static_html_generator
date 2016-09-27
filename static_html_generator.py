#!/usr/bin/env python

import os.path
import shutil
import sys
import re

from bs4 import BeautifulSoup
import patched_beautiful_soup
from PIL import Image
from bs4 import BeautifulSoup
from optparse import OptionParser

Image.warnings.simplefilter('ignore', Image.DecompressionBombWarning)


def check_folder_structure(skeleton_dir_name, output_dir_name, output_temp_dir_name):
    if not os.path.isdir(skeleton_dir_name):
        raise Exception("Need skeleton folder")
    if os.path.isfile(output_dir_name):
        raise Exception("There is an output filename.",
                        "This program creates an output folder")
    if os.path.isfile(output_temp_dir_name):
        raise Exception("There is an output_temp filename.",
                        "This program creates an output_temp folder")


def delete_files_in_dir(dir_name):
    for the_file in os.listdir(dir_name):
        file_path = os.path.join(dir_name, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(e)


def copy_files_in_dir(src_dir_name, dst_dir_name, symlinks=False, ignore=None):
    for item in os.listdir(src_dir_name):
        full_src_name = os.path.join(src_dir_name, item)
        full_dst_name = os.path.join(dst_dir_name, item)
        if os.path.isdir(full_src_name):
            shutil.copytree(full_src_name, full_dst_name, symlinks, ignore)
        else:
            shutil.copy2(full_src_name, full_dst_name)


def load_resources(global_ignore_filenames, resources_dir_name):
    resources = {}
    for resource_filename in os.listdir(resources_dir_name):
        if resource_filename not in global_ignore_filenames:
            full_resource_filename = os.path.join(resources_dir_name, resource_filename)
            with open(full_resource_filename, 'r') as current_file:
                resources[resource_filename] = current_file.read()
    return resources


def handle_file_replace(page_contents, resources):
    percentage_pattern = re.compile("%(\w|\.)+%")
    current_match = re.search(percentage_pattern, page_contents)
    while current_match:
        pattern_start_reversed = page_contents[:current_match.start()][::-1]
        whitespace_match = re.search("[ \t]+", pattern_start_reversed)
        beginning = pattern_start_reversed[whitespace_match.end():][::-1]
        resource_data = resources[current_match.group()[1:-1]]
        consistent_whitespace = whitespace_match.group()
        middle = consistent_whitespace + resource_data.replace("\n",
                                                               "\n" + consistent_whitespace)
        end = page_contents[current_match.end():]
        page_contents = beginning + middle + end
        current_match = re.search(percentage_pattern, page_contents)
    return page_contents


def get_pixel_value(img_tag):
    pixel_value_pattern = re.compile("[0-9]+(px)?")
    match = re.fullmatch(pixel_value_pattern, img_tag)
    if match:
        if match.group(1):
            return int(match.group(0)[:-2])
        else:
            return int(match.group(0))
    else:
        raise Exception("Could not parse \"" + img_tag + "\" as a pixel value")


def determine_indentation(indented_string):
    indentation_pattern = re.compile("( |\t)+<")
    indentation_match = re.search(indentation_pattern, indented_string)
    return indentation_match.group(1)


def get_list_ierators(iterators):
    output = []
    for iter in iterators:
        output.append(iter)
    return output


def create_thumbnails(page_contents, filename, all_filenames, skeleton_dir_name, output_temp_dir_name, thumbnail_bias):
    parsed_html = BeautifulSoup(page_contents, "lxml")
    thumbnail_pattern = re.compile("(.*)(_[0-9]+_[0-9]+)(.*)")
    for img_tag_data in parsed_html.find_all("img"):
        image_names_ref = [img_tag_data.get("src")]
        srcset_refs = img_tag_data.get("srcset")
        if srcset_refs:
            for srcset_ref in srcset_refs.split(","):
                srcset = srcset_ref.strip().split()[0]
                image_names_ref.append(srcset)
        new_img_texts = create_thumnail_and_get_replacement_text(all_filenames, filename, image_names_ref, img_tag_data,
                                                 output_temp_dir_name, skeleton_dir_name, thumbnail_bias,
                                                 thumbnail_pattern)
        if "" != new_img_texts[0]:
            img_tag_data["src"] = new_img_texts[0]
        for i in range(1, len(new_img_texts)):
            if "" != new_img_texts[i]:
                img_tag_data["srcset"] = img_tag_data["srcset"].replace(image_names_ref[i], new_img_texts[i])
    return parsed_html.prettify(formatter="html")


def create_thumnail_and_get_replacement_text(all_filenames, filename, image_names_ref, img_tag_data,
                                             output_temp_dir_name, skeleton_dir_name, thumbnail_bias,
                                             thumbnail_pattern):
    new_image_texts = []
    for image_name_ref in image_names_ref:
        if image_name_ref[0:4] != "http":
            # check image in skeleton
            image_base_name = os.path.basename(image_name_ref)
            thumbnail_match = thumbnail_pattern.search(image_base_name)
            image_base_name_root = thumbnail_match.group(1) + thumbnail_match.group(3) if thumbnail_match else None
            found_image = False
            found_image_root = False
            image_name_source = ""
            for possible_image in all_filenames:
                possible_image_basename = os.path.basename(possible_image)
                if possible_image_basename == image_base_name:
                    found_image = True
                    image_name_source = possible_image
                    break
                elif possible_image_basename == image_base_name_root:
                    found_image = True
                    found_image_root = True
                    image_name_source = possible_image
                    break
            if not found_image:
                raise Exception(
                    filename + ": could create thumbnail for " + image_name_ref + " in " + str(all_filenames))
            image_name_source_rel_path = skeleton_dir_name + "/" + image_name_source

            if found_image_root:
                tokenized_name = thumbnail_match.group(2)[1:].split('_')
                width_data = tokenized_name[0]
                height_data = tokenized_name[1]
                image_base_name = image_base_name_root
                used_thumbnail_bias = 1.0
            else:
                width_data = img_tag_data.get("width")
                height_data = img_tag_data.get("height")
                used_thumbnail_bias = thumbnail_bias
            if width_data and height_data:
                initial_width = get_pixel_value(width_data)
                width = int(int(initial_width) * used_thumbnail_bias + 0.5)
                initial_height = get_pixel_value(height_data)
                height = int(int(initial_height) * used_thumbnail_bias + 0.5)
                thumbnail_filename = get_thumbnail_name(image_base_name,
                                                        image_name_source_rel_path,
                                                        skeleton_dir_name, str(width),
                                                        str(height))
                thumbnail_filename_temp = output_temp_dir_name + "/" + thumbnail_filename
                create_thumbnail(image_name_source_rel_path, thumbnail_filename_temp, width, height)

                new_img_tag = "/" + thumbnail_filename
                new_image_texts.append(new_img_tag)
            else:
                new_image_texts.append("")
    return new_image_texts


def get_thumbnail_name(image_base_name, image_name_source_rel_path, skeleton_dir_name, width_str,
                       height_str):
    image_file_dir = "thumbnails/"
    thumbnail_subdir = os.path.dirname(image_name_source_rel_path)[len(skeleton_dir_name) + 1:]
    if thumbnail_subdir:
        image_file_dir += thumbnail_subdir + "/"
    image_base_names = os.path.splitext(image_base_name)
    thumbnail_filename = image_file_dir + image_base_names[0] + "_" + width_str + "_" + height_str + \
                         ".png"
    return thumbnail_filename


def create_thumbnail(image_name_source_rel_path, thumbnail_filename, width, height):
    if not os.path.isfile(thumbnail_filename):
        os.makedirs(os.path.dirname(thumbnail_filename), exist_ok=True)
        image_data = Image.open(image_name_source_rel_path)
        image_data.thumbnail((width, height))
        image_data.save(thumbnail_filename)


def compile_page(page_contents, resources, filename, all_filenames, skeleton_dir_name, output_temp_dir_name,
                 thumbnail_bias):
    page_contents = handle_file_replace(page_contents, resources)
    page_contents = create_thumbnails(page_contents, filename, all_filenames, skeleton_dir_name, output_temp_dir_name,
                                      thumbnail_bias)
    return page_contents


def create_clean_directory(output_temp_dir_name):
    if os.path.isdir(output_temp_dir_name):
        shutil.rmtree(output_temp_dir_name)
    os.makedirs(output_temp_dir_name)


def get_list_of_files_in_directory(directory_name, global_ignore_filenames):
    skeleton_filenames = []
    for (dirpath, dirnames, filenames) in os.walk(directory_name):
        usable_filenames = []
        for filename in filenames:
            if filename not in global_ignore_filenames:
                relative_path = dirpath[len(directory_name):]
                if relative_path:
                    relative_path = relative_path[1:]
                    relative_path += "/"
                usable_filenames.append(relative_path + filename)
        skeleton_filenames.extend(usable_filenames)
    return skeleton_filenames


def move_temp_folder_to_other_folder(temp_folder, new_folder):
    if os.path.isdir(new_folder):
        delete_files_in_dir(new_folder)
    if not os.path.exists(new_folder):
        os.makedirs(new_folder)
    copy_files_in_dir(temp_folder, new_folder)
    if os.path.isdir(temp_folder):
        shutil.rmtree(temp_folder)


def get_program_options():
    parser = OptionParser()
    parser.add_option("-b", "--thumbnail-bias", dest="thumbnail_bias",
                      default=1.5, type="float",
                      help="multiplier on thumbnail pixel size")
    parser.add_option("-w", "--working-directory", dest="working_directory",
                      default=".", type="str",
                      help="directory where a \"skeleton\" folder is input and an \"output\" folder is output")
    (options, args) = parser.parse_args()
    return options


def compile_directory():
    global_ignore_filenames = [".DS_Store"]

    program_options = get_program_options()

    skeleton_dir_name = program_options.working_directory + "/skeleton"
    output_dir_name = program_options.working_directory + "/output"
    output_temp_dir_name = program_options.working_directory + "/output_temp"
    resources_dir_name = program_options.working_directory + "/resources"

    check_folder_structure(skeleton_dir_name, output_dir_name, output_temp_dir_name)
    create_clean_directory(output_temp_dir_name)

    skeleton_filenames = get_list_of_files_in_directory(skeleton_dir_name, global_ignore_filenames)

    for skeleton_filename in skeleton_filenames:
        full_src_name = os.path.join(skeleton_dir_name, skeleton_filename)
        full_dst_name = os.path.join(output_temp_dir_name, skeleton_filename)
        relative_dir = os.path.dirname(full_dst_name)
        if relative_dir != output_temp_dir_name:
            os.makedirs(os.path.dirname(full_dst_name), exist_ok=True)
        filename_ext = os.path.splitext(full_src_name)[1]
        if filename_ext == ".html":
            with open(full_src_name, 'r') as current_file:
                file_contents = current_file.read()
            compiled_page = compile_page(file_contents, load_resources(global_ignore_filenames, resources_dir_name),
                                         skeleton_filename, skeleton_filenames, skeleton_dir_name, output_temp_dir_name,
                                         program_options.thumbnail_bias)
            with open(full_dst_name, 'w') as current_file:
                current_file.write(compiled_page)
        else:
            shutil.copy2(full_src_name, full_dst_name)

    move_temp_folder_to_other_folder(output_temp_dir_name, output_dir_name)


compile_directory()
