# -*- coding: utf-8 -*-
from random import randint
import numpy as np
import sys
import commpy as comm
import commpy.channelcoding.convcode as check
from pip import main
import matplotlib.pyplot as plt
import math

def bits_to_symbols(bits: np.ndarray) -> np.ndarray:
    assert (len(bits) % 2) == 0, "bits not in pairs"
    out = np.zeros(len(bits) // 2, dtype=np.complex128)
    out += (bits.reshape(2, -1)[0] * 2) - 1
    out += (bits.reshape(2, -1)[1] * 2j) - 1j
    return out

def expected_output(state: int, in_bit: int) -> complex:
    """
    Computes the expected output the Viterbi algorithm given the current state
    and the current input bit
    :param state: the current state
    :param in_bit: the input bit
    :return: the QAM modulated expected output
    """
    assert state <= 3 and in_bit >= 0, "Input state was not in the correct range"
    assert in_bit <= 1 and in_bit >= 0, "Input bit was not binary"

    out: complex = 0
    # compute the real part (output bit 0)
    out += (((state & 1) ^ ((state & (1 << 1)) >> 1) ^ in_bit) * 2) - 1
    # compute the complex part (output bit 1)
    out += ((((state & (1 << 1)) >> 1) ^ in_bit) * 2j) - 1j
    return out

def viterbi_stage(states: list[dict],
                  recv: np.complex128,
                  expected_outputs: np.ndarray):
    """
    Computes a stage of the Viterbi algorithm.  Modifies states
    :param states: the current weights of the states (and how we got there)
    :param recv: the received signal for this stage
    :param expected_outputs: the expected outputs for every state, input combo
    """
    new_states = [{"weight": np.inf, "path": []} for _ in range(len(states))]

    # for each state
    for cur_state in range(4):
        # for each previous state
        in_bit = cur_state & 1
        p_state0 = (cur_state >> 1)
        p_state1 = (cur_state >> 1) | (1 << 1)
        # get the weight for transitions
        w0 = (expected_outputs[p_state0, in_bit] - recv)
        w0 = w0.imag ** 2 + w0.real ** 2
        w1 = (expected_outputs[p_state1, in_bit] - recv)
        w1 = w1.imag ** 2 + w1.real ** 2

        # set the new path and the new weight depending on the weights
        if w0 + states[p_state0]["weight"] < w1 + states[p_state1]["weight"]:
            new_states[cur_state]["weight"] = w0 + states[p_state0]["weight"]
            new_states[cur_state]["path"] = states[p_state0]["path"] + [in_bit]
        else:
            new_states[cur_state]["weight"] = w1 + states[p_state1]["weight"]
            new_states[cur_state]["path"] = states[p_state1]["path"] + [in_bit]
    states[:] = new_states            

def viterbi_soft_decode(input_signal: np.ndarray) -> np.ndarray:
    """
    Soft decoder for the Viterbi algorithm
    :param input_signal: the QAM modulated convolutional code
    """
    # compute expected outputs and the next state
    expected_symbols = np.zeros((4, 2), dtype=np.complex128)
    next_states = np.zeros((4, 2), dtype=np.uint8)
    for state in range(4):
        for in_bit in range(2):
            expected_symbols[state, in_bit] = expected_output(state, in_bit)
            next_states[state, in_bit] = ((state << 1) | in_bit) & 0b11
    
    # set initial states
    states = [
        {
            "weight": 0,
            "path": []
        },
        {
            "weight": np.inf,
            "path": []
        },
        {
            "weight": np.inf,
            "path": []
        },
        {
            "weight": np.inf,
            "path": []
        }
    ]
    for signal in input_signal:
        viterbi_stage(states, signal, expected_symbols)

    # should end on state 00. and we need to shave off the last two 0 bits
    return np.array(states[0]["path"][:-3])


def WifiReceiver(input_stream, level):

    nfft = 64
    Interleave_tr = np.reshape(np.transpose(np.reshape(np.arange(1, 2*nfft+1, 1),[4,-1])),[-1,])
    preamble = np.array([1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1,1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1])
    cc1 = check.Trellis(np.array([3]),np.array([[0o7,0o5]]))

    # set zero padding to be 0, by default
    begin_zero_padding = 0
    message=""
    length=0

    if level >= 4:
        print("asdf", input_stream)
        #Input QAM modulated + Encoded Bits + OFDM Symbols in a long stream
        #Output Detected Packet set of symbols
        # convert preamble to symbols
        kernel = bits_to_symbols(preamble)
        # perform IFFT on preamble symbols
        kernel = np.fft.ifft(kernel)
        # perform correlation to find the preamble index
        input_stream = input_stream[1]
        correlation = np.correlate(input_stream, kernel, mode='same')
        threshold = np.abs(np.sum(kernel ** 2)) * 0.975
        indices = np.where(np.abs(correlation) > threshold)[0]
        begin_zero_padding = 11
        begin_zero_padding += indices[0] if len(indices) else np.argmax(correlation)
        # trim the message
        input_stream = input_stream[begin_zero_padding-1:]
        input_stream=input_stream

    if level >= 3:
        #Input QAM modulated + Encoded Bits + OFDM Symbols
        #Output QAM modulated + Encoded Bits
        input_stream=input_stream
    
    if level >= 2:
        #Input QAM modulated + Encoded Bits
        #Output Interleaved bits + Encoded Length
        input_stream = viterbi_soft_decode(input_stream)
       
    if level >= 1:
        #Input Interleaved bits + Encoded Length
        #Output Deinterleaved bits

        # find length and convert to int

        #majority rules length_buts
        length_bits = []
        for i in range(0, 128, 3):
            length_bits.append(int(input_stream[i] + input_stream[i+1] + input_stream[i+2] >= 2))
        length_bits = np.array(length_bits)
        length = int(length_bits.dot(2**np.arange(length_bits.size)[::-1]))
        
        # get message bits and padding size
        message_bits = input_stream[128:]
        padding_size = 128 * math.ceil((length * 8)/128)
        deleaved_bits = []

        # deinterleave bits
        for i in range(padding_size//4): 
            block_start = (i // 32) * 128
            offset = i % 32
            deleaved_bits.append(int(message_bits[block_start + offset]))
            deleaved_bits.append(int(message_bits[block_start + offset + 32]))
            deleaved_bits.append(int(message_bits[block_start + offset + 64]))
            deleaved_bits.append(int(message_bits[block_start + offset + 96]))
            
        # convert message bits to ascii
        sorted_deleaved = np.packbits(deleaved_bits)
        for num in sorted_deleaved:
            message += chr(num)
            
        return begin_zero_padding, message, length

    raise Exception("Error: Unsupported level")


# for testing purpose
from wifitransmitter import WifiTransmitter
if __name__ == "__main__":
    # for testing the viterbi decoder
    # for i in range(100):
    #     test_msg = np.random.default_rng().integers(0, 2, size=1000)
    #     cc1 = check.Trellis(np.array([3]),np.array([[0o7,0o5]]))
    #     coded_message = check.conv_encode(test_msg.astype(bool), cc1)
    #     mod = comm.modulation.QAMModem(4)
    #     output = mod.modulate(coded_message.astype(bool))
    #     noise = (np.random.randn(len(output)) + 1j * np.random.randn(len(output))) * 0.5
    #     output += noise
    #     output = viterbi_soft_decode(output)
    #     assert np.array_equal(test_msg, output), "Failed"
    test_case = 'The Internet has transformed our everyday lives, bringing people closer together and powering multi-billion dollar industries. The mobile revolution has brought Internet connectivity to the last-mile, connecting billions of users worldwide. But how does the Internet work? What do oft repeated acronyms like "LTE", "TCP", "WWW" or a "HTTP" actually mean and how do they work? This course introduces fundamental concepts of computer networks that form the building blocks of the Internet. We trace the journey of messages sent over the Internet from bits in a computer or phone to packets and eventually signals over the air or wires. We describe commonalities and differences between traditional wired computer networks from wireless and mobile networks. Finally, we build up to exciting new trends in computer networks such as the Internet of Things, 5-G and software defined networking. Topics include: physical layer and coding (CDMA, OFDM, etc.); data link protocol; flow control, congestion control, routing; local area networks (Ethernet, Wi-Fi, etc.); transport layer; and introduction to cellular (LTE) and 5-G networks. The course will be graded based on quizzes (on canvas), a midterm and final exam and four projects (all individual). '
    symbols = [randint(0, 1) for i in range(32*8)]
    output = WifiTransmitter(test_case, 2)
    begin_zero_padding, message, length_y = WifiReceiver(output, 2)
    print(test_case)
    print(begin_zero_padding, message, length_y)
    print(test_case == message)
