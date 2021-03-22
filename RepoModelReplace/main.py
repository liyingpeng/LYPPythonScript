
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

key_words = "model"

def _read_and_replace(_trace_file):
    for exclude in excludeFiles:
        if exclude in _trace_file:
            return

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
            # for key in startwith_keypare.keys():
            #     value = startwith_keypare[key]
            #     if s.startswith(key):
            #         s = value
            # for key in replace_kaypare.keys():
            #     value = replace_kaypare[key]
            #     if key in s:
            #         s = s.replace(key, value)

            if s.startswith("#import"):
                importLines.append(s)
                importIndex = lines.index(s)
                newLines.append(s)
                continue

            #deal with function
            it = re.finditer(r'([a-zA-Z]+\.)*'+key_words+' [a-zA-Z]+', s)
            for match in it:
                match_string = match.group()
                splitArray_funtion = match_string.split(' ')
                match_string_function = splitArray_funtion[-1]
                match_string_pre = splitArray_funtion[0]
                splitArray = match_string_pre.split('.')
                # indexOfPublishModel = splitArray.index('publishModel')
                # remove 'inputData'
                # if indexOfPublishModel > 0 and splitArray[indexOfPublishModel - 1] == 'inputData':
                #     splitArray.remove('inputData')
                # indexOfPublishModel = splitArray.index('publishModel')
                # splitArray[indexOfPublishModel] = "repository"
                if match_string_function in function_keypare.keys():
                    function_value = function_keypare[match_string_function]
                    import_key = repo_keypare[function_value]
                    if is_cameraclient:
                        import_str = "#import " + '"' + import_key + '.h"\n'
                    else:
                        import_str = "#import <CameraClient/" + import_key + '.h>\n'

                    if (import_str not in importLines):
                        newLines.insert(importIndex + 1, import_str)
                        importIndex = importIndex+1
                        importLines.append(import_str)
                    splitArray.append(function_value)
                    replace_string = ".".join(splitArray) + " " + match_string_function
                    s = s.replace(match_string, replace_string, 1)

            #deal with property
            it = re.finditer(r'([a-zA-Z]+\.)*'+key_words+'(\.[a-zA-Z]+)*', s)
            for match in it:
                match_string = match.group()
                splitArray = match_string.split('.')
                indexOfPublishModel = splitArray.index(key_words)
                # # remove 'inputData'
                # if indexOfPublishModel > 0 and splitArray[indexOfPublishModel - 1] == 'inputData':
                #     splitArray.remove('inputData')
                # indexOfPublishModel = splitArray.index('publishModel')
                # if indexOfPublishModel + 1 < len(splitArray) and splitArray[indexOfPublishModel + 1].startswith('repo'):
                #     splitArray.pop(indexOfPublishModel + 1)
                # splitArray[indexOfPublishModel] = "repository"
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

def dealing_with_dir(root_path):
    dir_or_files = os.listdir(root_path)
    for dir_file in dir_or_files:
        dir_file_path = os.path.join(root_path, dir_file)
        if os.path.isdir(dir_file_path):
            dealing_with_dir(dir_file_path)
        else:
            if os.path.splitext(dir_file_path)[-1] == ".h" or os.path.splitext(dir_file_path)[-1] == ".m":
                _read_and_replace(dir_file_path)

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
