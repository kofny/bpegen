"""
Passwords with different strength
"""
import argparse
import json
import sys
from typing import Tuple, Dict


def read_pw(rules_file: str, strength_dict: Dict[str, Tuple[int, int]]):
    with open(rules_file, 'r') as f_rules_file:
        for line in f_rules_file:
            line = line.strip('\r\n')
            result = json.loads(line)
            gn = result['guess_number']
            pw = result['pw']
            cnt = result['cnt']
            st = ''
            for strength, (il, ir) in strength_dict.items():
                if il <= gn < ir:
                    st = strength
                    break
            yield pw, cnt, gn, st
    pass


def wrapper():
    cli = argparse.ArgumentParser("Find weak passwords")
    cli.add_argument('-p', '--pw-file', type=str, help='Passwords file')
    cli.add_argument('--strengths', type=str, nargs='+', default=['weak', 'medium', 'strong'],
                     help='Name of different strengths')
    cli.add_argument('--intervals', type=float, nargs='+',
                     default=[1, 10 ** 6, 10 ** 6, 10 ** 14, 10 ** 14, sys.float_info.max],
                     help='the intervals for different strengths')
    cli.add_argument('-s', '--save', type=str, help='save results in this file')
    args = cli.parse_args()
    strengths, intervals = args.strengths, args.intervals
    strength_dict = {strengths[i]: (intervals[2 * i], intervals[2 * i + 1]) for i in range(len(strengths))}

    results = read_pw(rules_file=args.pw_file, strength_dict=strength_dict)
    strength_cnt_dict: Dict[str, Dict[str, int]] = {strength: {} for strength in strength_dict.keys()}
    total = 0
    for pw, cnt, gn, st in results:
        strength_cnt_dict[st][pw] = cnt
        total += cnt
        pass
    for strength in strengths:
        pw_cnt_dict = strength_cnt_dict[strength]
        sub_total = sum(pw_cnt_dict.values())
        print(f"{strength:7}: uniq {len(pw_cnt_dict):8}, total {sub_total:8}, {sub_total / total:9.4%}",
              file=sys.stderr, flush=True)
    if args.save is not None:
        with open(args.save, 'w') as f_save:
            json.dump(strength_cnt_dict, f_save, indent=2)
    pass


if __name__ == '__main__':
    wrapper()
