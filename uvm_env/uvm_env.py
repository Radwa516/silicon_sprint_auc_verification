"""
Complete UVM testbench for AES design.
"""

import cocotb
import random
from cocotb.clock import Clock
from cocotb.triggers import Timer, FallingEdge
from pyuvm import *
from Crypto.Cipher import AES
    
class AES_Transaction(uvm_sequence_item):
    """Transaction for AES test."""
    
    def __init__(self, name="AES_Transaction"):
        super().__init__(name)
        self.cs = 0
        self.we = 0
        self.address = 0
        self.write_data = 0
    
    def __str__(self):
        return (f"cs=0x{self.cs}, we=0x{self.we}, "
                f"address={self.address}, ")


class AES_Sequence(uvm_sequence):
    """Sequence generating AES test vectors."""
    
    async def body(self):
        """Generate test vectors."""

        for _ in range(1):
            #Intialize the inputs 
            txn = AES_Transaction()
            txn.cs = 0
            txn.we = 0
            txn.address = 0x00
            txn.write_data = 0x00000000
            await self.start_item(txn)
            await self.finish_item(txn)


class AES_Driver(uvm_driver):
    """Driver for AES DUT."""

    def build_phase(self):
        # Retrieve the interface and check if the process is successful
        self.vif = ConfigDB().get(self, "", "dut")
        if self.vif is not None:
            self.logger.info("Get the interface successfully")
        else:
            self.logger.error("Can't get the interface")
    
    async def run_phase(self):
        while True:
            txn = await self.seq_item_port.get_next_item()
            self.vif.cs.value = txn.cs
            
            print("=" * 100)
            self.logger.info(f"From Driver --> txn: {txn}")
            await FallingEdge(self.vif.clk)
            self.seq_item_port.item_done()


class AES_Monitor(uvm_monitor):
    """Monitor for AES DUT."""
    
    def build_phase(self):
        # broadcast tlm to send the transaction to the scoreboard and the coverage
        self.ap = uvm_analysis_port("ap", self)
        # Retrieve the interface and check if the process is successful
        self.vif = ConfigDB().get(self, "", "dut")
        if self.vif is not None:
            self.logger.info("Get the interface successfully")
        else:
            self.logger.error("Can't get the interface")
        
    
    async def run_phase(self):
        while True:
            txn = AES_Transaction()
            txn.cs = self.vif.cs.value

            # Sending the transaction to the scoreboard and the coverage
            self.ap.write(txn)
            self.logger.info(f"From Monitor --> txn: {txn}")
            await FallingEdge(self.vif.clk)


class AES_Scoreboard(uvm_subscriber):
    """Scoreboard for AES verification."""
    
    def build_phase(self):
        # Use uvm_subscriber which automatically implements write() method
        self.actual = []
        self.expected_result = []
        self.round_key_list = [] 
        self.text_list = [] 
        self.round_key = 0  
        self.text = 0
        self.count = 0
        self.mismatches = 0
        self.matches = 0

    def write(self, txn):
        """Receive transactions from monitor."""
        self.logger.info(f"Scoreboard received: {txn}")
              
    def golden_model(self, key, plaintext):
        expected_result = []
        cipher = AES.new(key, AES.MODE_ECB)
        ciphertext = cipher.encrypt(plaintext)
        self.count += 1

        w0 = int.from_bytes(ciphertext[0:4], byteorder='big')
        w1 = int.from_bytes(ciphertext[4:8], byteorder='big')
        w2 = int.from_bytes(ciphertext[8:12], byteorder='big')
        w3 = int.from_bytes(ciphertext[12:16], byteorder='big')

        expected_result = [w0, w1, w2, w3]
        return expected_result
    
    def check(self, index: int):
        actual_data = int(self.actual.pop(0)) 
        if (actual_data != self.expected_result[index]):
            self.logger.error(f"Mismatch: ciphertext = 0x{self.expected_result[index]:8X}, "
                              f"actual data = 0x{actual_data:8X}")
            self.mismatches += 1
        else:
            self.logger.info(f"Match: ciphertext = 0x{self.expected_result[index]:8X}, "
                             f"actual data = 0x{actual_data:8X}")
            self.matches += 1
        
    def check_phase(self):
        """Check phase - verify results."""
        self.logger.info("=" * 50)
        self.logger.info("Scoreboard Check")
        self.logger.info(f"Total transactions: {self.count}")
        self.logger.info(f"Number of Mismatches: {self.mismatches}")
        self.logger.info(f"Number of Matches: {self.matches}")

class AES_Coverage(uvm_subscriber):
    """Coverage for advanced test."""
    
    def __init__(self, name="AdgerCoverage", parent=None):
        super().__init__(name, parent)
        self.coverage_we = {}
    
    def write(self, txn):
        """Sample coverage"""
        address_we = int(txn.we)

        if address_we not in self.coverage_we:
            self.coverage_we[address_we] = 0
        self.coverage_we[address_we] += 1

        print("="*150)
        print(f"Coverage sampled for bin write enable: {address_we}, unique values: {len(self.coverage_we)}")
        print("="*150)

class AES_Agent(uvm_agent):
    """Agent for AES_."""
    
    def build_phase(self):
        self.driver = AES_Driver.create("driver", self)
        self.monitor = AES_Monitor.create("monitor", self)
        self.seqr = uvm_sequencer("sequencer", self)
    
    def connect_phase(self):
        # In pyuvm, connect the sequencer to the driver
        # The sequencer has the seq_item_export, driver has seq_item_port
        # Connect export -> port (sequencer provides, driver consumes)
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)


class AES_Env(uvm_env):
    """Environment for AES test."""
    
    def build_phase(self):
        self.logger.info("Building AES_Env")
        self.agent = AES_Agent.create("agent", self)
        self.scoreboard = AES_Scoreboard.create("scoreboard", self)
        self.coverage = AES_Coverage.create("coverage", self)
    
    def connect_phase(self):
        self.logger.info("Connecting AES_Env")
        self.agent.monitor.ap.connect(self.scoreboard.analysis_export)
        self.agent.monitor.ap.connect(self.coverage.analysis_export)


# Note: @uvm_test() decorator removed to avoid import-time TypeError
class AES_Test(uvm_test):
    """Test class for AES"""
    
    def build_phase(self):
        """Build phase - create environment."""
        self.logger.info("=" * 50)
        self.logger.info("Building AES_Test")
        self.logger.info("=" * 50)
        self.env = AES_Env.create("env", self)
        
        # Sending the interface
        self.dut = cocotb.top
        ConfigDB().set(None, "*", "dut", self.dut)
    
    async def run_phase(self):
        self.raise_objection()
        self.logger.info("Running AES_Test") 
        print("=*" * 50)      
        
        # Start sequence
        seq = AES_Sequence.create("seq")
        await seq.start(self.env.agent.seqr)
        self.drop_objection()
    
    def check_phase(self):
        self.logger.info("Checking AES_Test results")
    
    def report_phase(self):
        self.logger.info("=" * 50)
        self.logger.info("AES_Test completed")
        self.logger.info("=" * 50)

# asynchronous reset
async def async_reset(dut, duration_ns=100, propagation_delay_ns=10):
    """ Asynchronous reset sequence. """
    print("Asserting async reset...")
    
    dut.reset_n.value = 0
    await Timer(duration_ns, unit="ns")
    
    print("Deasserting async reset...")
    dut.reset_n.value = 1
    # Wait for reset signal to propagate through DUT logic
    # This ensures all flip-flops have stabilized before continuing
    await Timer(propagation_delay_ns, unit="ns")
    print("Reset complete")

# Cocotb test function to run the pyuvm test
@cocotb.test()
async def test_AES(dut):
    """Cocotb test wrapper for AES_Test."""

    clk_period = 2
    # generating the clock
    clock = Clock(dut.clk, clk_period, unit="ns")
    cocotb.start_soon(clock.start())
    # await init_inputs(dut)
    await async_reset(dut, 3*clk_period, clk_period)
    # await FallingEdge(dut.clk)

    # Register the test class with uvm_root so run_test can find it
    if not hasattr(uvm_root(), 'm_uvm_test_classes'):
        uvm_root().m_uvm_test_classes = {}
    uvm_root().m_uvm_test_classes["AES_Test"] = AES_Test

    # Use uvm_root to run the test properly (executes all phases in hierarchy)
    await uvm_root().run_test("AES_Test")


if __name__ == "__main__":
    # Note: This is a structural example
    # In practice, you would use cocotb to run this with a simulator
    print("This is a pyuvm test structure example.")
    print("To run with cocotb, use the Makefile in the test directory.")

