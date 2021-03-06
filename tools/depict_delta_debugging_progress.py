#!/usr/bin/python

# output format, one line per subsequence where a bug was found:
# <Subsequence #> <# inputs> <event 1 included?> <event 2 included?> ...

import argparse
import json
import glob
import sys
import os
from trace_utils import parse_json, parse_event_trace

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sts.input_traces.log_parser import parse
from sts.util.tabular import Tabular
from sts.event_dag import EventDag

class InterReplayDirectory(object):
  def __init__(self, dir_str):
    self.dir_str = dir_str
    # Format example: interreplay_10_r_5/
    self.index = int(os.path.basename(dir_str).split("_")[1])

  def __str__(self):
    return self.dir_str

  def __repr__(self):
    return self.dir_str


class TraceFormatter(object):
  def __init__(self, full_trace):
    self.full_trace = full_trace
    self.all_input_events = set(full_trace.input_events)
    self.input_to_round_eliminated = {}

  def format_trace(self, label, trace):
    ''' Assumes that subsequences are processed in-order, and that each
    given subsequence resulted in a violation '''
    row = [label, len(trace.input_events)]
    isect = set(trace.input_events).intersection(self.all_input_events)
    for i, input_event in enumerate(self.full_trace.input_events):
      if input_event in isect:
        row.append(1)
      else:
        # An input is eliminated the first time a trace that does not include
        # it triggers a bug
        if i not in self.input_to_round_eliminated:
          self.input_to_round_eliminated[i] = label
        row.append(0)
    mcs_size = len(self.all_input_events) - len(self.input_to_round_eliminated)
    row.insert(2, mcs_size)
    return row

def main(args):
  # Grab JSON of which subsequences triggered a bug.
  replay_idx_to_violation = parse_json(args.subsequence_violations)

  subsequence_dirs = [ InterReplayDirectory(d) for d in
                       glob.glob(args.directory + "/interreplay_*") ]
  assert(subsequence_dirs != [])
  subsequence_dirs.sort(key=lambda d: d.index)

  # First, grab all inputs so we know how to format
  repro_dir = subsequence_dirs.pop(0)
  assert(os.path.basename(str(repro_dir)) == "interreplay_0_reproducibility")
  full_trace = parse_event_trace(str(repro_dir) + "/events.trace")
  trace_formatter = TraceFormatter(full_trace)

  # Now format each subsequence
  columns = []
  columns.append(["subsequence", lambda row: row[0]])
  columns.append(["# inputs", lambda row: row[1]])
  columns.append(["MCS size", lambda row: row[2]])
  for idx, e in enumerate(full_trace.input_events):
    # See: http://stackoverflow.com/questions/233673/lexical-closures-in-python
    def bind_closure(index):
      return lambda row: row[index+3]
    columns.append([e.label, bind_closure(idx)])
  t = Tabular(columns)
  rows = []
  for subsequence_dir in subsequence_dirs:
    try:
      if "_final_mcs" in str(subsequence_dir):
        # Make sure to always print the final MCS
        trace = parse_event_trace(str(subsequence_dir) + "/events.trace")
        rows.append(trace_formatter.format_trace("MCS", trace))
      elif replay_idx_to_violation[subsequence_dir.index]:
        # Otherwise only consider subsequences that resulted in a violation
        trace = parse_event_trace(str(subsequence_dir) + "/events.trace")
        rows.append(trace_formatter.format_trace(subsequence_dir.index, trace))
    except KeyError as e:
      print >> sys.stderr, "WARN: No such subsequence: %s" % str(e)

  t.show(rows)

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('-s', '--subsequence-violations', dest='subsequence_violations',
                      help=('''JSON file containing a dict of which subsequences'''
                           ''' resulted in a violation.'''),
                      required=True)
  parser.add_argument('-d', '--directory',
                      help='path to top-level MCS experiment results directory',
                      required=True)
  args = parser.parse_args()

  main(args)
