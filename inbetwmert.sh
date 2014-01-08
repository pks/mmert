#!/bin/bash

# mmert v0.2
# manipulate mert-moses.pl script
# Copyright 2011
# Patrick Simianer
# Heidelberg University, ICL
#
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


function usage()
{
    echo "Usage: $0 <suffix>"
    exit
}

if [ -z "$1" ]; then usage; fi


MMERTPKG=~/mmert/example/   	     # base directory
BIN=$MMERTPKG/bin/      	         # binaries (moses, mert, extractor)
DECODER=$BIN/moses                   # decoder
SCRIPTS=$MMERTPKG/scripts/           # moses scripts folder
FOLDER_PREFIX=mert_$1                # directory for logs (created in current directory)
WORKDIR=mmert_$1                     # working directory for mmert (created in current directory)
PARALLEL=2                           # number moses/mert processes to run in parallel
DECODER_FLAGS="-th 1"	             # additional decoder flags, e.g. '-th 8' for 8 threads per moses instance, needs moses with thread support
TASKS=(A B C D)                      # used to identify tasks
TASKL="A,B,C,D"                      # same as above as string, tasks ids separated by ','
NUMTASKS=${#TASKS[@]}                # for parallelization, number of tasks
INI=$MMERTPKG/ini/moses.ini          # one moses ini for all tasks (e.g. pooled model and/or same start weights)? or prefix for individual inis
SET=dev                              # dev or devtest (only used to build filenames)?
#declare -A INIS
#INIS[${TASKS[0]}]=$INI/$SET/${TASKS[0]}/moses.ini # individual inis (for individual models and/or individual start weights)
#INIS[${TASKS[1]}]=$INI/$SET/${TASKS[1]}/moses.ini
#INIS[${TASKS[2]}]=$INI/$SET/${TASKS[2]}/moses.ini
#INIS[${TASKS[3]}]=$INI/$SET/${TASKS[3]}/moses.ini
#INIS[${TASKS[4]}]=$INI/$SET/${TASKS[4]}/moses.ini
#INIS[${TASKS[5]}]=$INI/$SET/${TASKS[5]}/moses.ini
#INIS[${TASKS[6]}]=$INI/$SET/${TASKS[6]}/moses.ini

# the next variables enable the script to locate your dev set(s), please set accordingly
# see also run_mert_wrapper() function 
FR=de                          # source language
EN=en                          # target language
TUNEFILE_PREFIX=epmini-$SET    # to build filenames of dev(test) sets

MAX_ITER=100                   # max mert iterations
NBEST=100                      # n for nbest lists
INBETW=./regmtl.py             # script to run after MERT runs finished
NUM_WEIGHTS=14                 # dimension, length of weight vector
MIN_CHANGE=0.01                # minimum change in average vector, stopping criterion
LAMBDA=0.01                    # regularization parameter
FIRST_AVG=0                    # 0: zero vector, 1: provide run0.avector.txt yourself (in $WORKDIR)

# parameters
#  $1 FR tuning data
#  $2 EN tuning data
#  $3 /path/to/ini
#  $4 task id
#  $5 --continue
#
#
function run_mert()
{
    ./mert-moses.pl \
        $1 \
        $2 \
        $DECODER \
        $3 \
        --no-filter-phrase-table \
        --working-dir $FOLDER_PREFIX"_$4" \
        --rootdir $SCRIPTS \
        --decoder-flags "$DECODER_FLAGS" \
        --mertdir $BIN \
        --inputtype=0 \
        --maximum-iterations=9999 \
        --efficient_scorenbest_flag \
        --nocase \
        --nonorm \
        --nbest=$NBEST \
        $5
}

function run_mert_wrapper()
{
    T=$1
    echo -e "\n ===> $IT ========>\n\n" >> $WORKDIR/mert.$T.out >> $WORKDIR/mert.$T.err
    # replace $INI with ${INIS[$T]} to use separate inis
    run_mert $MMERTPKG/data/$TUNEFILE_PREFIX-$T.$FR $MMERTPKG/data/$TUNEFILE_PREFIX-$T.$EN $INI $T $CONT >> $WORKDIR/mert.$T.out 2>> $WORKDIR/mert.$T.err
}

function wait_for()
{
    echo "Waiting for ${#WAITFOR[@]} MERT procs..."
    for pid in ${WAITFOR[@]}; do
        wait $pid;
    done
}


if [ ! -d "$WORKDIR" ]; then
    mkdir $WORKDIR
fi

IT=0
while true; do
    IT=$(($IT+1))
    if [ $IT -eq 1 ]; then
        echo "First iteration"
        CONT="";
    else
        echo -e "\nContinue with $IT"
        CONT="--continue";
    fi

    # first half
    WAITFOR=()
    for (( i = 1; i <= $PARALLEL; i++ )); do
        echo "Start for ${TASKS[$i-1]}"
        run_mert_wrapper ${TASKS[$i-1]} &
        WAITFOR+=( $! )
    done
    wait_for $WAITFOR

    # second half
    WAITFOR=()
    for (( i = $PARALLEL+1; i <= $NUMTASKS; i++)); do
        echo "Start for ${TASKS[$i-1]}"
        run_mert_wrapper ${TASKS[$i-1]} &        
        WAITFOR+=( $! )
    done
    wait_for $WAITFOR

    echo "Running $INBETW ..."
    $INBETW $FOLDER_PREFIX $WORKDIR $TASKL $IT $NUM_WEIGHTS $MIN_CHANGE $LAMBDA $FIRST_AVG

    if [ -f "$WORKDIR/CONVERGED" ]; then break; fi
    if [ $IT -eq $MAX_ITER ]; then
    	echo "Reached global iteration limit ($MAX_ITER), stopping.";
        break;
    fi
done
echo 'done'

