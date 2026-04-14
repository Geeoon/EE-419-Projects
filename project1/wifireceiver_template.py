# -*- coding: utf-8 -*-
from random import randint
import numpy as np
import sys
import commpy as comm
import commpy.channelcoding.convcode as check
from pip import main
import matplotlib.pyplot as plt

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

    print(expected_symbols)

    for state in range(4):
        for in_bit in range(2):
            print(f"In state {bin(state)} with input {in_bit}", expected_symbols[state, in_bit])

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
        #Input QAM modulated + Encoded Bits + OFDM Symbols in a long stream
        #Output Detected Packet set of symbols
        input_stream=input_stream

    if level >= 3:
        #Input QAM modulated + Encoded Bits + OFDM Symbols
        #Output QAM modulated + Encoded Bits
        input_stream=input_stream
    
    if level >= 2:
        #Input QAM modulated + Encoded Bits
        #Output Interleaved bits + Encoded Length
        viterbi_soft_decode(input_stream)
        input_stream = input_stream
       
    if level >= 1:
        #Input Interleaved bits + Encoded Length
        #Output Deinterleaved bits
        return begin_zero_padding, message, length

    raise Exception("Error: Unsupported level")


# for testing purpose
from wifitransmitter import WifiTransmitter
if __name__ == "__main__":
    test_case = 'The Internet has transformed our everyday lives, bringing people closer together and powering multi-billion dollar industries. The mobile revolution has brought Internet connectivity to the last-mile, connecting billions of users worldwide. But how does the Internet work? What do oft repeated acronyms like "LTE", "TCP", "WWW" or a "HTTP" actually mean and how do they work? This course introduces fundamental concepts of computer networks that form the building blocks of the Internet. We trace the journey of messages sent over the Internet from bits in a computer or phone to packets and eventually signals over the air or wires. We describe commonalities and differences between traditional wired computer networks from wireless and mobile networks. Finally, we build up to exciting new trends in computer networks such as the Internet of Things, 5-G and software defined networking. Topics include: physical layer and coding (CDMA, OFDM, etc.); data link protocol; flow control, congestion control, routing; local area networks (Ethernet, Wi-Fi, etc.); transport layer; and introduction to cellular (LTE) and 5-G networks. The course will be graded based on quizzes (on canvas), a midterm and final exam and four projects (all individual). '
    symbols = [randint(0, 1) for i in range(32*8)]
    print(test_case)
    output = WifiTransmitter(test_case, 2)
    begin_zero_padding, message, length_y = WifiReceiver(output, 2)
    print(begin_zero_padding, message, length_y)
    print(test_case == message)