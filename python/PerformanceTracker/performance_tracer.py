#!/usr/bin/python

import os
import sys
import re
from re import search
import argparse
import json
import functools
import shutil

ADD_STACK_COUNT = 0
REMOVE_STACK_COUNT = 0
DIFF_STACK_COUNT = 0

class TraceItem(object):
    def __init__(self, name=None, pos=None, tid=None, ts=None, cls_method=None):
        self.name = name
        self.pos = pos
        self.tid = tid
        self.ts = ts
        self.cls_method = cls_method
        # 当前方法耗时，如果有重名方法 当前为总时长
        self.duration = None
        # 当前方法子方法列表
        self.sub_item_list = []
        # 父方法指针
        self.super_item = None
        # 重名方法耗时统计
        self.same_list = []
        # 标识该item 需要跟index 为merge_index的item merge
        self.merge_index = None

        # for diff
        self.diff_duration = None
        self.diff_count = None

    def is_done(self):
        return self.duration is not None

    def print_stack(self):
        print("总耗时" + str(self.duration))
        print("总次数" + str(len(self.same_list)))
        stack = self.name
        super = self.super_item
        while super is not None:
            stack += "->" + super.name
            super = super.super_item
        print("堆栈信息" + stack)
        print("--------------- isolation --------------")

def print_n(item_list, n):
    if n > len(item_list) - 1:
        n = len(item_list) - 1
    for item in item_list[:n]:
        item.print_stack()

def merge_item_to_item(merged_item, to_item):
    if to_item.same_list is None:
        to_item.same_list = [to_item.duration]
    else:
        to_item.same_list.append(to_item.duration)
    to_item.same_list.append(merged_item.duration)
    to_item.duration += merged_item.duration

    for to_item_enu in to_item.sub_item_list:
        for merged_item_enu in merged_item.sub_item_list:
            if to_item_enu.name == merged_item_enu.name:
                merge_item_to_item(merged_item_enu, to_item_enu)


def read_track_list_from_jsonfile(blame_filepath):
    with open(blame_filepath, 'r') as f:
        data = json.load(f)
        trace_list = []
        temp_trace_list = []
        for blame_dict in data:
            trace_item = TraceItem()
            trace_item.name = blame_dict['name']
            trace_item.pos = blame_dict['ph']
            trace_item.tid = blame_dict['pid']
            trace_item.ts = blame_dict['ts']
            write_trace_item_to(trace_item, trace_list, temp_trace_list)
        f.close()

        # 完备性校验
        pre_item = temp_trace_list[-1]
        while pre_item is not None:
            # if not pre_item.is_done():
                # print(pre_item)
            pre_item = pre_item.super_item
        return trace_list

def write_trace_item_to(trace_item, trace_list, temp_trace_list):

    pre_item = None
    super_item = None
    if len(trace_list) > 0:
        # 找到上一个没有结算完的item
        pre_item = temp_trace_list[-1]
        while pre_item is not None and pre_item.is_done():
            pre_item = pre_item.super_item
        if pre_item is not None:
            super_item = pre_item.super_item

    # 获取时间戳
    if pre_item is not None:
        # 上一个item 没有计算完
        if pre_item.pos == 'B':
            # 计算耗时
            if trace_item.name == pre_item.name and trace_item.pos == 'E':
                pre_item.duration = trace_item.ts - pre_item.ts

                if pre_item.merge_index is not None:
                    merge_item = None
                    remove_from_list = None
                    if super_item:
                        merge_item = super_item.sub_item_list[pre_item.merge_index]
                        remove_from_list = super_item.sub_item_list
                    else:
                        merge_item = trace_list[pre_item.merge_index]
                        remove_from_list = trace_list
                    if merge_item is not None:
                        merge_item_to_item(pre_item, merge_item)
                    if remove_from_list is not None:
                        remove_from_list.remove(pre_item)
                return
            else:
                if trace_item.pos == 'B':
                    trace_item.super_item = pre_item
                    if pre_item.sub_item_list is not None:
                        for index, item in enumerate(pre_item.sub_item_list):
                            if item.name == trace_item.name:
                                trace_item.merge_index = index
                        pre_item.sub_item_list.append(trace_item)
                    else:
                        pre_item.sub_item_list = [trace_item]
                else:
                    exit(-1)
        else:
            exit(-1)
    else:
        for index, item in enumerate(trace_list):
            if item.name == trace_item.name:
                trace_item.merge_index = index
        trace_list.append(trace_item)

    temp_trace_list.append(trace_item)

def parse_one_trace_log(source_file, output_file):
    write_dot = False
    for file_name in os.listdir(source_file):
        file_path = source_file + "/" + file_name
        print("Parsing " + file_path)

        output = open(output_file, 'w')
        output.write("[\n")
        with open(file_path, 'r') as f:
            for line in f:
                if line.isspace():
                    continue
                if not line.startswith("["):
                    continue
                components = line.rstrip().split(";")
                if len(components) != 5:
                    continue
                name = components[0]
                pos = components[1]
                tid = int(components[2], 10)
                ts = int(components[3], 10)
                cls_method = components[4]

                # 生成火焰图
                if len(cls_method) == 0:
                    continue
                is_cls_method = int(cls_method, 10)
                if is_cls_method:
                    name = "+" + name
                else:
                    name = "-" + name
                data = {"name": name, "cat": "objc_trace", "ph": pos, "pid": 0, "tid": tid, "ts": ts}
                content = json.dumps(data)
                if len(content) == 0:
                    continue
                if write_dot:
                    output.write(",\n")
                output.write(content)
                write_dot = True
        output.write("\n]")
        output.close()


def stack_diff_recursion(source_list, compare_list, stack_add, stack_remove, stack_diff):
    if source_list is None:
        stack_add += compare_list
        return
    if compare_list is None:
        stack_remove += source_list
        return

    for source_item in source_list:
        in_compare = False
        compare_pointer = 0
        for index, compare_item in enumerate(compare_list):
            if compare_item.name == source_item.name:
                in_compare = True
                compare_pointer = index
                break
        if not in_compare:
            stack_remove.append(source_item)
        else:
            if len(source_item.sub_item_list) == 0 and len(compare_list[compare_pointer].sub_item_list) == 0:
                source_item.diff_count = len(compare_list[compare_pointer].same_list) - len(source_item.same_list)
                source_item.diff_duration = compare_list[compare_pointer].duration - source_item.duration
                stack_diff.append(source_item)
            else:
                stack_diff_recursion(source_item.sub_item_list, compare_list[compare_pointer].sub_item_list, stack_add, stack_remove, stack_diff)

    for compare_item in compare_list:
        in_source = False
        for source_item in source_list:
            if compare_item.name == source_item.name:
                in_source = True
        if not in_source:
            stack_add.append(compare_item)


def stack_diff(source_list, compare_list):

    stack_add = []
    stack_remove = []
    stack_diff = []

    stack_diff_recursion(source_list, compare_list, stack_add, stack_remove, stack_diff)

    stack_add.sort(key=lambda k: -k.duration)
    stack_remove.sort(key=lambda k: -k.duration)
    stack_diff.sort(key=lambda k: -abs(k.diff_duration))

    total_add = 0
    total_remove = 0
    total_diff = 0
    if len(stack_add) > 0:
        total_add = functools.reduce(lambda a, b: a+b, list(map(lambda x: x.duration, stack_add)))
    if len(stack_remove) > 0:
        total_remove = functools.reduce(lambda a, b: a+b, list(map(lambda x: x.duration, stack_remove)))
    if len(stack_diff) > 0:
        total_diff = functools.reduce(lambda a, b: a+b, list(map(lambda x: x.diff_duration, stack_diff)))

    print("总新增耗时"+str(total_add))
    print("总减少耗时"+str(total_remove))
    print("总diff耗时"+str(total_add-total_remove+total_diff))

    print("--------------- isolation 新增耗时  --------------")
    print_n(stack_add, 2)
    print("--------------- isolation 减少耗时 --------------")
    print_n(stack_remove, 2)
    print("--------------- isolation Diff耗时 --------------")
    print_n(stack_diff, 2)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Trace Diff Tools")
    parser.add_argument("-c", "--compare", help="compare trace data file")
    parser.add_argument("-s", "--source", help="source trace data file")
    parser.add_argument("-at", "--add_stack", help="source trace data file")
    parser.add_argument("-rt", "--remove_stack", help="source trace data file")
    parser.add_argument("-dt", "--diff_stack", help="source trace data file")
    args = parser.parse_args()

    source_file = args.source
    compare_file = args.compare
    # ADD_STACK_COUNT = args.at
    # REMOVE_STACK_COUNT = args.rt
    # DIFF_STACK_COUNT = args.dt

    output_file_path = os.path.expanduser("~") + "/Desktop/trace_output"
    if os.path.exists(output_file_path):
        shutil.rmtree(output_file_path, ignore_errors=True)
    os.makedirs(output_file_path)

    source_json_file_path = output_file_path + "/trace_source.json"
    compare_json_file_path = output_file_path + "/trace_compare.json"
    trace_list_source = None
    trace_list_compare = None
    if os.path.isdir(source_file):
        print("正在进行 - parse source file")
        parse_one_trace_log(source_file, source_json_file_path)
        print("正在进行 - generate source trace list")
        trace_list_source = read_track_list_from_jsonfile(source_json_file_path)
    else:
        print("正在进行 - generate source trace list")
        trace_list_source = read_track_list_from_jsonfile(source_file)
    if os.path.isdir(compare_file):
        print("正在进行 - parse compare file")
        parse_one_trace_log(compare_file, compare_json_file_path)
        print("正在进行 - generate compare trace list")
        trace_list_compare = read_track_list_from_jsonfile(compare_json_file_path)
    else:
        print("正在进行 - generate compare trace list")
        trace_list_compare = read_track_list_from_jsonfile(compare_file)

    if trace_list_source is not None and trace_list_compare is not None:
        print("正在进行 - stack diff")
        stack_diff(trace_list_source, trace_list_compare)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
