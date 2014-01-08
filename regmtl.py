#!/usr/bin/env python2.6

"""
mmert v0.2
multi-task mert
Copyright 2011
Patrick Simianer
Heidelberg University, ICL
"""

# This file is part of MMERT.
#
# MMERT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MMERT is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MMERT.  If not, see <http://www.gnu.org/licenses/>.


import os, sys, shutil


def read_vec_from_file(fname):
    """ File looks like: "w1 w2 ... wn" (on one line). """
    return [float(el) for el in open(fname, 'r').read().strip().split()]

def vec2str(vector):
    """ vec looks like: [0., 1.1, 2.2, ..., d] """
    return " ".join([str(el) for el in vector])

def get_biggest_change(vector1, vector2):
    """ Biggest difference of two vectors (element-wise) in abs value. """
    biggest = 0
    idx_ = 0
    for element in vector1:
        diff = abs(element - vector2[idx_])
        if diff > biggest:
            biggest = diff
        idx_ += 1
    return biggest

def get_avg_vec(vecs, vec_len):
    """ 'vecs' is a list of vectors; calc arithmetic mean element-wise. """
    avg_vec = []
    num_vecs = len(vecs)
    for idx_ in range(vec_len):
        mysum = 0.
        for vector in vecs:
            mysum += vector[idx_]
        avg = mysum/num_vecs
        avg_vec.append(avg)
    return avg_vec

def get_best_points_line_idx(lines):
    """ Line number where to find best point in a mert.log. """
    idx_ = 0
    for line in lines:
        if line.startswith("Best point: "):
            break
        idx_ += 1
    return idx_

def get_weights_from_log(fname):
    """ Get weights from a mert.log. """
    logfile = open(fname, "r")
    lines = logfile.readlines()
    logfile.close()
    idx_ = get_best_points_line_idx(lines)
    return [float(el) for el in \
      lines[idx_].split("Best point: ")[1].split("=>")[0].split()]

def write_new_log_file(fname, vec_):
    """ Write a new mert.log file with weights found in vec. """
    logfile = open(fname, "r")
    lines = logfile.readlines()
    logfile.close()
    idx_ = get_best_points_line_idx(lines)
    log = "".join(lines[0:idx_])
    log += "Best point: "+vec2str(vec_)+" => 99\n"
    log += "".join(lines[idx_+1:])
    open(fname, "w+").write(log)




# parameters
DIR_PREFIX      = sys.argv[1]            # directory prefix
                                         # (for task specific directories)
WORKDIR         = sys.argv[2]            # work directory
TASKS           = sys.argv[3].split(",") # task list "a,b,c..."
CUR_IT          = int(sys.argv[4])       # current (global) iteration
NUM_WEIGHTS     = int(sys.argv[5])       # dimensionality of a weight vector?
MIN_CHANGE      = float(sys.argv[6])     # min change in a vector
                                         # to still continue
LAMBDA          = float(sys.argv[7])     # lambda for regularization
FIRST_AVERAGE   = bool(int(sys.argv[8])) # first average vector,
                                         # 0 or self provided

print " CUR_IT %s" % str(CUR_IT)
if CUR_IT == 1:
    print " DIR_PREFIX %s" % DIR_PREFIX
    print " WORKDIR %s" % WORKDIR
    print " TASKS %s" % str(TASKS)
    print " NUM_WEIGHTS %s" % str(NUM_WEIGHTS)
    print " MIN_CHANGE %s" % str(MIN_CHANGE)
    print " LAMBDA %s" % str(LAMBDA)
    print " FIRST_AVERAGE %s" % str(FIRST_AVERAGE)
    if not FIRST_AVERAGE:
        print " first average is 0 vector, creating file.."
        open(WORKDIR+"/run0.avector.txt", "w+").write(\
          " ".join(["0.0" for i in range(NUM_WEIGHTS)]))
    else:
        print " looking for pre-defined first average.."
        if not os.path.exists(WORKDIR+"/run0.avector.txt"):
            sys.stderr.write(sys.argv[0] + \
            " ERROR: You have to provide your own run0.avector.txt \
            containing the first average vector! arg FIRST_AVERAGE=" \
            +str(FIRST_AVERAGE)+"\n")
            sys.exit (1)

ITERATIONS = {} # current iteration(s)
CUR_VECS   = {} # current weight vectors (from latest mert iteration)
VEC_LEN    = 0  # check vector length
for t in TASKS:
    print " reading vector from task %s" % t
    ITERATIONS[t] = int(open(DIR_PREFIX + "_" + t +\
      "/finished_step.txt").read().strip())
    cur = get_weights_from_log(DIR_PREFIX+"_"+t+"/run"+str((ITERATIONS[t])) + \
                               ".mert.log")
    print cur
    VEC_LEN = len(cur)
    if VEC_LEN != NUM_WEIGHTS:
        sys.stderr.write(sys.argv[0] + \
        " ERROR: vector lengths differ! (task: "+t+", len: "+str(VEC_LEN) + \
        ", expected: "+str(NUM_WEIGHTS)+")\n")
    CUR_VECS[t] = cur

# get previous average vector
PREV_AVG_VEC = read_vec_from_file(WORKDIR+"/run"+str(CUR_IT-1)+".avector.txt")
print " Previous average vector (clip against):"
print PREV_AVG_VEC 

# new weight vecs
print " Calculating new weight vectors (clipping).."
NEXT_VECS = {}
for (t, vec) in CUR_VECS.items():
    print " Task %s, before (current)" % t
    print vec
    idx = 0
    nxt = []
    for w in vec:
        if w == 0:
            nxt.append(0.0)
            idx += 1
            continue
        if (w - PREV_AVG_VEC[idx] > 0):
            nxt.append(max(PREV_AVG_VEC[idx], w - LAMBDA))
        elif (w - PREV_AVG_VEC[idx] < 0):
            nxt.append(min(PREV_AVG_VEC[idx], w + LAMBDA))
        else:
            nxt.append(w)
        idx += 1
    NEXT_VECS[t] = nxt
    print " Task %s, after (next)" % t
    print nxt

# get current average vector
AVG_VEC = get_avg_vec(NEXT_VECS.values(), VEC_LEN)

print " Current average vector (after clipping):"
print AVG_VEC

# convergence?
print " Previous average:", PREV_AVG_VEC
print "  Current average:", AVG_VEC
BIGGEST_CHANGE = get_biggest_change(PREV_AVG_VEC, AVG_VEC)
print "  Biggest change:", BIGGEST_CHANGE 
# note: use weights from latest mert.log for eval!
if BIGGEST_CHANGE < MIN_CHANGE:
    print " Converged!"
    open(WORKDIR+"/CONVERGED", "w+").close()

# overwrite (and backup) mert.log
for t in TASKS:
    logfilename = DIR_PREFIX+"_"+t+"/run"+str(ITERATIONS[t])+".mert.log"
    shutil.copy(logfilename, logfilename+".bak")
    write_new_log_file(logfilename, NEXT_VECS[t])
    open(DIR_PREFIX+"_"+t+"/weightshist", "a+").write(str(ITERATIONS[t])+"\n"+ \
      "cur      "+str(CUR_VECS[t])+"\n"+ \
      "prev avg "+str(PREV_AVG_VEC)+"\n"+ \
      "next     "+str(NEXT_VECS[t])+"\n"+ \
      "cur avg  "+str(AVG_VEC)+"\n---\n")
    
# write out current avg vector
open(WORKDIR+"/run"+str(CUR_IT)+".avector.txt", "w+").write(vec2str(AVG_VEC))

