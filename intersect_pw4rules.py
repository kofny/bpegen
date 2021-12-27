"""
Passwords following various rules are in various files.
We intersect passwords following several rules into a new file
"""
import argparse
import json
import os.path
import sys
from typing import List


def intersect(folder: str, rules: List[int]):
    rules_files = {rule_id: os.path.join(folder, f"rule-{rule_id}.txt") for rule_id in rules}
    universe = {}
    for rule_id, rules_file in sorted(rules_files.items(), key=lambda x: os.path.getsize(x[1])):
        join = {}
        with open(rules_file, 'r') as f_rules_file:
            idx = 0
            for line in f_rules_file:
                line = line.strip('\r\n')
                info = json.loads(line)
                pw = info['pw']
                if len(universe) == 0 or pw in universe:
                    join[pw] = info
                idx += 1
                if idx % 10000 == 0:
                    print(f"Rule {rule_id}: {len(join):10} passwords", end='\r', file=sys.stderr, flush=True)
                pass
        print(f"Rule {rule_id}: {len(join):10} passwords, Done!", file=sys.stderr, flush=True)
        del universe
        universe = join
    return universe.values()


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
