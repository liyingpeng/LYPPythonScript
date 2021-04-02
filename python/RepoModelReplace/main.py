
"""
RepoModelReplacement
Authors: liyinggpeng
"""

import os
import re
from re import search
import sys
import time
import argparse
import codecs
from keypare import key_pare
from keypare import function_keypare
from keypare import replace_kaypare
from keypare import startwith_keypare, excludeFiles, repo_keypare

key_words = "[self publishModel]"
key_words_re = "\[self publishModel\]"

key_words_array = [
    # {"[self publishModel]": "\[self publishModel\]"},
    # {"[self publishViewModel]": "\[self publishViewModel\]"},

    # {"originalPublishModel": "originalPublishModel"},
    # {"originPublishModel": "originPublishModel"},
    {"publishModel": "publishModel"},
    # {"originalModel": "originalModel"},
    # {"sourceModel": "sourceModel"},
    {"publishViewModel": "publishViewModel"},
    {"model": "model"},
    {"origin": "origin"},

    # {"originUploadPublishModel": "originUploadPublishModel"},
    # {"originalPublishViewModel": "originalPublishViewModel"},
    # {"imagePublishModel": "imagePublishModel"},


    # {"providedPublishModel": "providedPublishModel"},
    # {"currentPublishModel": "currentPublishModel"},
    # {"willTransforToPublishModel": "willTransforToPublishModel"},
    # {"mvPublishViewModel": "mvPublishViewModel"},
    # {"mvPublishModel": "mvPublishModel"},
    # {"_mvPublishModel": "_mvPublishModel"},
    # {"textPublishModel": "textPublishModel"},
    # {"_textPublishModel": "_textPublishModel"},

]

def _read_and_replace(_trace_file, key_words, key_words_re):
    is_cameraclient = False
    if 'CameraClient' in _trace_file:
        is_cameraclient = True

    if os.path.exists(_trace_file):
        fp = open(_trace_file, "r")
        lines = fp.readlines()
        fp.close()

        fp = open(_trace_file, 'w')
        newLines = []
        importLines = []
        importIndex = 0
        for s in lines:
            if s.startswith("#import"):
                importLines.append(s)
                importIndex = lines.index(s)
                newLines.append(s)
                continue

            #deal with function
            it = re.finditer(r'([a-zA-Z]+\.)*'+key_words_re+' [a-zA-Z]+[:\]]', s)
            for match in it:
                match_string = match.group()
                splitArray_funtion = match_string.split(' ')
                match_string_function = splitArray_funtion[-1]
                match_string_function_key = match_string_function.strip(']')
                splitArray_funtion.pop()
                match_string_pre = ' '.join(splitArray_funtion)
                if match_string_function_key in function_keypare.keys():
                    function_value = function_keypare[match_string_function_key]
                    import_key = repo_keypare[function_value]
                    if is_cameraclient:
                        import_str = "#import " + '"' + import_key + '.h"\n'
                    else:
                        import_str = "#import <CameraClient/" + import_key + '.h>\n'

                    if (import_str not in importLines):
                        newLines.insert(importIndex + 1, import_str)
                        importIndex = importIndex+1
                        importLines.append(import_str)
                    replace_string = match_string_pre + "." + function_value + " " + match_string_function
                    s = s.replace(match_string, replace_string, 1)
                elif match_string_function_key in key_pare.keys():
                    function_value = key_pare[match_string_function_key]
                    import_key = repo_keypare[function_value]
                    if is_cameraclient:
                        import_str = "#import " + '"' + import_key + '.h"\n'
                    else:
                        import_str = "#import <CameraClient/" + import_key + '.h>\n'

                    if (import_str not in importLines):
                        newLines.insert(importIndex + 1, import_str)
                        importIndex = importIndex + 1
                        importLines.append(import_str)
                    replace_string = match_string_pre + "." + function_value + " " + match_string_function
                    s = s.replace(match_string, replace_string, 1)

            #deal with property
            it = re.finditer(r'([a-zA-Z]+\.)*'+key_words_re+'(\.[a-zA-Z]+)*', s)
            for match in it:
                match_string = match.group()
                if len(match_string) <= 0:
                    continue
                splitArray = match_string.split('.')
                indexOfPublishModel = splitArray.index(key_words)
                if indexOfPublishModel + 1 < len(splitArray):
                    match_key = splitArray[indexOfPublishModel + 1]
                    if match_key in key_pare.keys():
                        match_value = key_pare[match_key]
                        import_key = repo_keypare[match_value]
                        if is_cameraclient:
                            import_str = "#import " + '"' + import_key + '.h"\n'
                        else:
                            import_str = "#import <CameraClient/" + import_key + '.h>\n'
                        if (import_str not in importLines):
                            newLines.insert(importIndex + 1, import_str)
                            importIndex = importIndex + 1
                            importLines.append(import_str)
                        splitArray.insert(indexOfPublishModel+1, match_value)
                    elif match_key in function_keypare.keys():
                        match_value = function_keypare[match_key]
                        import_key = repo_keypare[match_value]
                        if is_cameraclient:
                            import_str = "#import " + '"' + import_key + '.h"\n'
                        else:
                            import_str = "#import <CameraClient/" + import_key + '.h>\n'
                        if (import_str not in importLines):
                            newLines.insert(importIndex + 1, import_str)
                            importIndex = importIndex + 1
                            importLines.append(import_str)
                        splitArray.insert(indexOfPublishModel + 1, match_value)
                replace_string = ".".join(splitArray)
                s = s.replace(match_string, replace_string, 1)

            newLines.append(s)
        fp.write("".join(newLines))
        fp.close()
    else:
        print('file not exist')


def dealing_with_dir_loop(dir_file_path):
    for exclude in excludeFiles:
        if exclude in dir_file_path:
            return
    if "AWEVideoPublishViewModel+" in dir_file_path:
        _read_and_replace(dir_file_path, "self", "self")
        return
    if "AWEOpenShareProviderIMP" in dir_file_path:
        _read_and_replace(dir_file_path, "model", "model")
        return
    for keypare in key_words_array:
        keywords = keypare.keys()[0]
        keywordsre = keypare.values()[0]
        _read_and_replace(dir_file_path, keywords, keywordsre)

def dealing_with_dir(root_path):
    dir_or_files = os.listdir(root_path)
    for dir_file in dir_or_files:
        dir_file_path = os.path.join(root_path, dir_file)
        if os.path.isdir(dir_file_path):
            dealing_with_dir(dir_file_path)
        else:
            if os.path.splitext(dir_file_path)[-1] == ".h" or os.path.splitext(dir_file_path)[-1] == ".m":
                dealing_with_dir_loop(dir_file_path)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Model Replacement Tools")
    parser.add_argument("-c", "--cameraClient", help="replace file")
    parser.add_argument("-s", "--studio", help="replace file")
    args = parser.parse_args()

    c_trace_file = args.cameraClient
    s_trace_file = args.studio

    if os.path.isdir(c_trace_file):
        dealing_with_dir(c_trace_file)
    else:
        _read_and_replace(c_trace_file)

    # if os.path.isdir(s_trace_file):
    #     dealing_with_dir(s_trace_file)
    # else:
    #     _read_and_replace(s_trace_file)


    # _read_and_replace(_trace_file)
    # _read_and_replace(_trace_file)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
