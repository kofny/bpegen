import argparse
import bisect
import os
import random
import re
import sys
import math
import pickle
from collections import defaultdict
from typing import Dict, Tuple, Any, Set, List


def check_path_exists(_path: str):
    if not os.path.exists(_path):
        print(f"{_path} not exists, exit.", file=sys.stderr)
        sys.exit(-1)
    pass


def lets_log(d: Dict[Any, float]):
    for k in d:
        d[k] = -math.log2(d[k])
    pass


def read_tag(tag_path: str, tag: str) -> Dict[Tuple[str, int], Dict[str, float]]:
    check_path_exists(tag_path)
    tag_dict = defaultdict(lambda: defaultdict(float))
    for root, dirs, files in os.walk(tag_path):
        for file in files:
            dot_idx = file.find(".")
            tag_len = (tag, int(file[:dot_idx]))
            fd = open(os.path.join(root, file))
            for line in fd:
                _tag, prob = line.strip("\r\n").split("\t")
                tag_dict[tag_len][_tag] = float(prob)
            fd.close()
    return tag_dict


def read_grammars(gram_path: str):
    fd = open(gram_path)
    structure_prob_dict = {}
    re_tag_len = re.compile(r"([A-Z]+[0-9]+)")
    re_tag = re.compile(r"[A-Z]+")
    re_len = re.compile(r"[0-9]+")
    for line in fd:
        raw_structure, prob = line.strip("\r\n").split("\t")
        structure = tuple(
            [(re_tag.search(t).group(), int(re_len.search(t).group())) for t in re_tag_len.split(raw_structure) if
             len(t) > 0])
        structure_prob_dict[structure] = float(prob)

    fd.close()
    return structure_prob_dict


def read_bpe(model_path: str) -> Tuple[Dict[Any, float], Dict[Tuple[str, int], Dict[Any, float]]]:
    """
    param model_path:
    return: (grammars, terminals)
        the grammars is a dict of structures and corresponding probabilities, such as
        ((D, 10), (D, 1), (L, 3)): 1.556e-7
        the terminals is a dict of tag (such as (D, 10)) and corresponding replacements
        and probabilities, such as (D, 10): {1234567890, 1.556e-7}
    """
    check_path_exists(model_path)
    grammars = read_grammars(os.path.join(model_path, "grammar", "structures.txt"))
    _dicts = []
    lower = read_tag(os.path.join(model_path, "lower"), "L")
    upper = read_tag(os.path.join(model_path, "upper"), "U")
    double_m = read_tag(os.path.join(model_path, "mixed_2"), "DM")
    triple_m = read_tag(os.path.join(model_path, "mixed_3"), "TM")
    four_m = read_tag(os.path.join(model_path, "mixed_4"), "FM")
    digits = read_tag(os.path.join(model_path, "digits"), "D")
    special = read_tag(os.path.join(model_path, "special"), "S")
    terminals = {**lower, **upper, **double_m, **triple_m, **four_m, **digits, **special}
    return grammars, terminals


def count_l_u_d_s(structures: Dict[Tuple, float]) -> (Dict[Any, Set], Dict[str, set]):
    skipped_list = []
    converts = defaultdict(set)
    for structure in structures:
        parsed_structure = []

        skip = False
        for tag, t_len in structure:
            if len(parsed_structure) > 0:
                prev_tag, prev_len = parsed_structure[-1]
                if prev_tag != tag:
                    parsed_structure.append((tag, t_len))
                else:
                    parsed_structure[-1] = (tag, prev_len + t_len)
            else:
                parsed_structure.append((tag, t_len))
            if 'M' in tag:
                skip = True
        parsed_structure = tuple(parsed_structure)
        if skip:
            skipped_list.append(structure)
            continue
        converts[parsed_structure].add(structure)
    novels = defaultdict(set)
    for k in converts.keys():
        novels[sum([s_len for _, s_len in k])].add(k)

    def the_same(struct_a, struct_b) -> bool:
        if len(struct_a) != len(struct_b):
            return False
        for s_a, s_b in zip(struct_a, struct_b):
            if s_a != s_b and 'M' not in s_a and 'M' not in s_b:
                return False
        return True

    struct_speedup = {}
    not_parsed = defaultdict(set)
    for skipped in skipped_list:
        len_skipped = sum([s_len for _, s_len in skipped])
        candidates = novels[len_skipped]
        speed_skipped = []
        for s_tag, s_len in skipped:
            speed_skipped.extend([s_tag] * s_len)

        for candidate in candidates:
            if candidate not in struct_speedup:
                backup = []
                for s_tag, s_len in candidate:
                    backup.extend([s_tag] * s_len)
                struct_speedup[candidate] = backup
            speed_candidate = struct_speedup[candidate]
            if the_same(speed_candidate, speed_skipped):
                converts[candidate].add(skipped)
        length = sum([_len for _, _len in skipped])
        not_parsed[length].add(skipped)

    return converts, not_parsed


def expand_2d(two_d_dict: Dict[Any, Dict[Any, float]], minus_log_based: bool = False) \
        -> Dict[Any, Tuple[Dict[Any, float], List[Any], List[float]]]:
    new_two_d_dict = {}
    for k, items in two_d_dict.items():
        if len(items) == 0:
            continue
        try:
            new_two_d_dict[k] = expand_1d(items, minus_log_based=minus_log_based)
        except ValueError:
            print(items)
            sys.exit(-1)
    return new_two_d_dict


def my_cum_sum(lst: List[float]):
    if len(lst) <= 0:
        return []
    acc = 0
    cum_sum = []
    for v in lst:
        acc += v
        cum_sum.append(acc)
    return cum_sum


def expand_1d(one_d_dict: Dict[Any, float], minus_log_based: bool = False) \
        -> Tuple[Dict[Any, float], List[Any], List[float]]:
    keys = list(one_d_dict.keys())
    cum_sums = my_cum_sum(list(one_d_dict.values()))
    n_one = one_d_dict
    if minus_log_based:
        n_one = {k: -math.log2(v) for k, v in one_d_dict.items()}
    new_one_d_dict = (n_one, keys, cum_sums)
    return new_one_d_dict


def pick_expand(expanded: Tuple[Dict[str, float], List[str], List[float]]) -> Tuple[float, str]:
    try:
        items, keys, cum_sums = expanded
    except TypeError:
        print(expanded)
        sys.exit(-1)
    if len(cum_sums) < 1:
        print(keys)
        pass
    total = cum_sums[-1]
    idx = bisect.bisect_right(cum_sums, random.uniform(0, total))
    k: str = keys[idx]
    return items.get(k), k


class BpePcfgSim(object):
    def sample1(self) -> (float, str):
        prob = .0
        p, struct = pick_expand(self.__grammars)
        prob += p
        for tag_len in struct:
            target_terminal = self.__terminals[tag_len]
            p, replacement = pick_expand(target_terminal)
            prob += p
        return prob

    def __init__(self, grammars, terminals):
        self.__grammars = expand_1d(grammars, minus_log_based=True)
        self.__terminals = expand_2d(terminals, minus_log_based=True)
        pass


def model2bin(model_path, dangerous_path, num_samples,
              model_pickle, intermediate_pickle, dangerous_chunks_pickle, samples_pickle):
    print("Loading model...", end='', file=sys.stderr)
    # count_luds and BpePcfgSim will log the prob
    # Therefore we do not log the prob here
    grammars, terminals = read_bpe(model_path)
    print("done!\n"
          "Loading chunks...", end='', file=sys.stderr)
    with open(dangerous_path, 'r') as f_danger:
        chunks = set(line.strip("\r\n") for line in f_danger)
    print("done!\n"
          "Counting intermediate results...", end='', file=sys.stderr)
    converted, not_parsed = count_l_u_d_s(grammars)
    print("done!\n"
          "Sampling probabilities...", end='', file=sys.stderr)
    bpe_simulator = BpePcfgSim(grammars, terminals)
    samples = [bpe_simulator.sample1() for _ in range(num_samples)]
    # Before saving, we log the grammars and terminals
    for k in grammars:
        grammars[k] = -math.log2(grammars[k])
    for _, v in terminals.items():
        for k in v:
            v[k] = -math.log2(v[k])
    print("done!", file=sys.stderr)

    with open(model_pickle, 'wb') as f_model_pickle, \
            open(intermediate_pickle, 'wb') as f_inter_pickle, \
            open(dangerous_chunks_pickle, 'wb') as f_danger_pickle, \
            open(samples_pickle, 'wb') as f_samples_pickle:
        pickle.dump((grammars, terminals), f_model_pickle)
        pickle.dump((converted, not_parsed), f_inter_pickle)
        pickle.dump(chunks, f_danger_pickle)
        pickle.dump(samples, f_samples_pickle)
    pass


def wrapper():
    cli = argparse.ArgumentParser("Model in plaintext to binary format")
    cli.add_argument("-m", '--model', required=True, help='BPE_PCFG model path')
    cli.add_argument("-d", '--danger', required=True, help='Dangerous chunks')
    cli.add_argument("-n", '--num-samples', default=1000000, type=int, help="Number of samples for Monte Carlo")
    cli.add_argument('-s', '--save-in-folder', required=True, help='Pickle files will be saved in this folder')
    args = cli.parse_args()
    folder = args.save_in_folder
    if not os.path.exists(folder):
        os.mkdir(folder)

    def gen_path(x: str):
        return os.path.join(folder, x)

    model_pickle, inter_pickle, danger_pickle, samples_pickle = \
        gen_path('bpemodel.pickle'), gen_path('intermediate_results.pickle'), \
        gen_path('dangerous_chunks.pickle'), gen_path('monte_carlo_sample.pickle')
    model2bin(model_path=args.model, dangerous_path=args.danger, num_samples=args.num_samples,
              model_pickle=model_pickle, intermediate_pickle=inter_pickle,
              dangerous_chunks_pickle=danger_pickle, samples_pickle=samples_pickle)
    pass


if __name__ == '__main__':
    wrapper()
    pass
