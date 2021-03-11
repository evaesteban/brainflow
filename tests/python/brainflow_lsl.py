# Example using brainflow to read data from Galea and send it as an LSL stream

import argparse
import time
import numpy as np
import sys
import getopt
from queue import Queue

import brainflow
from brainflow.board_shim import BoardShim, BrainFlowInputParams
from brainflow.data_filter import DataFilter, FilterTypes, AggOperations

from random import random as rand
from pylsl import StreamInfo, StreamOutlet, local_clock

def channel_select(board, board_id, data_type): 
    switcher = { 
        'EEG': board.get_eeg_channels(board_id),
        'EMG': board.get_emg_channels(board_id),
        'EOG': board.get_eog_channels(board_id),
        'EDA': board.get_eda_channels(board_id),
        'PPG': board.get_ppg_channels(board_id)

        # can add more
    } 
 
    return switcher.get(data_type, "error") 

def main():
    BoardShim.enable_dev_board_logger()

    parser = argparse.ArgumentParser()

    # brainflow params - use docs to check which parameters are required for specific board, e.g. for Cyton set serial port
    parser.add_argument('--timeout', type=int, help='timeout for device discovery or connection', required=False, default=0)
    parser.add_argument('--ip-address', type=str, help='ip address', required=True)
    parser.add_argument('--board-id', type=int, help='board id, check docs to get a list of supported boards',
                        required=True)
    parser.add_argument('--streamer-params', type=str, help='streamer params', required=False, default='')

    # LSL params 
    parser.add_argument('--name', type=str, help='name', required=True)
    parser.add_argument('--data-type', type=str, help='data type', required=True)
    parser.add_argument('--channel-names', type=str, help='channel names', required=True)
    parser.add_argument('--uid', type=str, help='uid', required=True)

    args = parser.parse_args()

    # brainflow initialization
    params = BrainFlowInputParams()
    params.ip_address = args.ip_address
    board = BoardShim(args.board_id, params)

    # LSL initialization  
    channel_names = args.channel_names.split(',')
    n_channels = len(channel_names)
    srate = board.get_sampling_rate(args.board_id)
    info = StreamInfo(args.name, args.data_type, n_channels, srate, 'double64', args.uid)
    outlet = StreamOutlet(info)
    fw_delay = 0

    # prepare session and start streaming
    board.prepare_session()
    board.start_stream(45000, args.streamer_params)
    time.sleep(1)
    start_time = local_clock()
    sent_samples = 0
    queue = Queue(maxsize = 5*srate)
    chans = channel_select(board, args.board_id, args.data_type)

    # read data with brainflow and send it via LSL
    print("Now sending data...")
    while True:
        data = board.get_board_data()[chans]
        for i in range(len(data[0])):
            queue.put(data[:,i].tolist())
        elapsed_time = local_clock() - start_time
        required_samples = int(srate * elapsed_time) - sent_samples
        if required_samples > 0 and queue.qsize() >= required_samples:    
            mychunk = []

            for i in range(required_samples):
                mychunk.append(queue.get())
            stamp = local_clock() - fw_delay 
            outlet.push_chunk(mychunk, stamp)
            sent_samples += required_samples
        #time.sleep(1)


if __name__ == "__main__":
    main()
