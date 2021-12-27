"""
Passwords following various rules are in various files.
We intersect passwords following several rules into a new file
"""
import argparse
import json
import os.path
import sys
from collections import defaultdict
from typing import List


def intersect(folder: str, rules: List[int]):
    rules_files = {rule_id: os.path.join(folder, f"rule-{rule_id}.txt") for rule_id in rules}
    universe = defaultdict(int)
    files = sorted(rules_files.items(), key=lambda x: os.path.getsize(x[1]))
    for rule_id, rules_file in files:
        with open(rules_file, 'r') as f_rules_file:
            idx = 0
            for line in f_rules_file:
                line = line.strip('\r\n')
                info = json.loads(line)
                pw = info['pw']
                universe[pw] += 1
                idx += 1
                if idx % 10000 == 0:
                    print(f"Rule {rule_id}: parsed {idx:10} passwords", end='\r', file=sys.stderr, flush=True)
                pass
        print(f"Rule {rule_id}: Done!                                 ", file=sys.stderr, flush=True)
    with open(files[0][1], 'r') as f_files0:
        for line in f_files0:
            line = line.strip("\r\n")
            info = json.loads(line)
            pw = info['pw']
            if universe.get(pw, 0) == len(rules):
                yield info
    pass


def wrapper():
    cli = argparse.ArgumentParser("Intersecting passwords following various rules")
    cli.add_argument('-f', "--folder", type=str, help='folder containing passwords following various rules')
    cli.add_argument("-r", '--rule-ids', type=int, choices=[1, 2, 3, 4, 5, 6, 7], nargs='+',
                     help='rule ids to intersect')
    cli.add_argument("-s", "--save", type=str, help='save intersected passwords in this file')
    args = cli.parse_args()
    results = intersect(folder=args.folder, rules=args.rule_ids)
    with open(args.save, 'w') as f_save:
        for json_obj in results:
            f_save.write(f"{json.dumps(json_obj)}\n")
    pass


if __name__ == '__main__':
    wrapper()
