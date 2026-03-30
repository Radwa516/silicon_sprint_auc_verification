# Makefile for Module 3 pyuvm tests
# Usage: make SIM=verilator test_simple_uvm

# Default simulator
SIM ?= verilator
EXTRA_ARGS += -Wno-fatal -Wno-UNOPTFLAT

# Python files
PYTHON_FILES = uvm_env.py 

# Verilog files
VERILOG_SOURCES := $(wildcard ../rtl/*.v)
VERILOG_FILES = $(VERILOG_SOURCES)

# Test to run
TEST ?= uvm_env

# Cocotb variables
MODULE = $(TEST)
TOPLEVEL = aes
COCOTB_REDUCED_LOG_FMT = 1

# Include cocotb makefile
include $(shell cocotb-config --makefiles)/Makefile.sim

