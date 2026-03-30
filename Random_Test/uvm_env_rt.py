"""
Module 3 Test Case 3.1: Simple UVM Test
Complete UVM testbench for simple adder.
"""

import cocotb
import random
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from pyuvm import *
from Crypto.Cipher import AES
# In pyuvm, use uvm_seq_item_port vifead of uvm_seq_item_pull_port
# uvm_seq_item_port is available from pyuvm import * and works the same way
# Create an alias for compatibility with code that expects uvm_seq_item_pull_port

# Use uvm_seq_item_port as it's the correct class in pyuvm
uvm_seq_item_pull_port = uvm_seq_item_port
    
class AES_Transaction(uvm_sequence_item):
    """Transaction for AES_ test."""
    
    def __init__(self, name="AES_Transaction"):
        super().__init__(name)
        self.cs = 0
        self.we = 0
        self.address = 0
        self.write_data = 0
        self.key = 0
        self.text = 0

    def randomize_constrained(self, length_min=0, length_max=0xFF, seed=None):
        """Randomize with constraints."""
        if seed is not None:
            random.seed(seed)

        self.key = random.randint(length_min, length_max)
        self.text = random.randint(length_min, length_max)
    
    def __str__(self):
        return (f"cs=0x{self.cs}, we=0x{self.we}, "
                f"address={self.address}, "
                f"write_data={self.write_data}")


class AES_Sequence(uvm_sequence):
    """Sequence generating AES_ test vectors."""
    
    async def body(self):
        """Generate test vectors."""

        for _ in range(50):
            txn = AES_Transaction()
            txn.cs = 0
            txn.we = 0
            txn.address = 0x00
            txn.write_data = 0x00000000
            await self.start_item(txn)
            await self.finish_item(txn)
            # Write key
            seed = random.getrandbits(32)
            txn.randomize_constrained(0, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF, seed)
            await self.sending_key(txn)

            # Set config FIRST (encrypt, 128-bit)
            #(1, 1, 0x0A, 0x00000000),
            #txn = AES_Transaction()
            txn.cs = 1
            txn.we = 1
            txn.address = 0x0A
            txn.write_data = 0x00000000
            await self.start_item(txn)
            await self.finish_item(txn)

            # INIT (build key schedule)
            #(1, 1, 0x08, 0x00000001),
            #txn = AES_Transaction()
            txn.cs = 1
            txn.we = 1
            txn.address = 0x08
            txn.write_data = 0x00000001
            await self.start_item(txn)
            await self.finish_item(txn)

            #(0, 0, 0x08, 0x00000001),
            #txn = AES_Transaction()
            txn.cs = 0
            txn.we = 0
            txn.address = 0x08
            txn.write_data = 0x00000001
            await self.start_item(txn)
            await self.finish_item(txn)

            # Write plaintext
            await self.sending_text(txn)

            # Set config FIRST (encrypt, 128-bit)
            #(1, 1, 0x0A, 0x00000001),
            #txn = AES_Transaction()
            txn.cs = 1
            txn.we = 1
            txn.address = 0x0A
            txn.write_data = 0x00000001
            await self.start_item(txn)
            await self.finish_item(txn)

            # START encryption
            #(1, 1, 0x08, 0x00000002),
            #txn = AES_Transaction()
            txn.cs = 1
            txn.we = 1
            txn.address = 0x08
            txn.write_data = 0x00000002
            await self.start_item(txn)
            await self.finish_item(txn)
            #(0, 0, 0x08, 0x00000002),

           #txn = AES_Transaction()
            txn.cs = 0
            txn.we = 0
            txn.address = 0x08
            txn.write_data = 0x00000002
            await self.start_item(txn)
            await self.finish_item(txn)

            # Read result
            #(1, 0, 0x30, 0x00000002),
            for i in range(4):
                #txn = AES_Transaction()
                txn.cs = 1
                txn.we = 0
                txn.address = 0x30 + i
                await self.start_item(txn)
                await self.finish_item(txn)

    async def sending_key (self, txn: AES_Transaction):

        key_words = [
            (txn.key >> 96) & 0xffffffff,
            (txn.key >> 64) & 0xffffffff,
            (txn.key >> 32) & 0xffffffff,
            txn.key & 0xffffffff, 0x00000000,
            0x00000000, 0x00000000, 0x00000000
        ]

        for i in range(len(key_words)):
            txn.cs = 1
            txn.we = 1
            txn.address = 0x10 + i
            txn.write_data = key_words[i]
            await self.start_item(txn)
            await self.finish_item(txn)
            #(1, 1, 0x11, 0x28aed2a6),
            #txn = AES_Transaction()
        

    async def sending_text (self, txn: AES_Transaction):
        text_words = [
            (txn.text >> 96) & 0xffffffff,
            (txn.text >> 64) & 0xffffffff,
            (txn.text >> 32) & 0xffffffff,
            txn.text & 0xffffffff,
        ]

        for i in range(len(text_words)):
            #txn = AES_Transaction()
            txn.cs = 1
            txn.we = 1
            txn.address = 0x20 + i
            txn.write_data = text_words[i]
            await self.start_item(txn)
            await self.finish_item(txn)
            

class AES_Driver(uvm_driver):
    """Driver for AES_ DUT."""

    def build_phase(self):
        # pyuvm drivers already have seq_item_port by default
        # No need to create it manually
        self.vif = ConfigDB().get(self, "", "dut")
        if self.vif is not None:
            self.logger.info("Get the vif successfully")
        else:
            self.logger.error("Can't get the interface")
        # pass
    
    async def run_phase(self):
        while True:
            txn = await self.seq_item_port.get_next_item()
            self.vif.cs.value = txn.cs
            self.vif.we.value = txn.we
            self.vif.address.value = txn.address
            self.vif.write_data.value = txn.write_data
            # waiting for the result
            if (txn.address == 0x08) and (txn.we == 0) and (txn.cs == 0):
                for _ in range(55):
                    await FallingEdge(self.vif.clk) 

            print("=" * 100)
            self.logger.info(f"From Driver --> txn: {txn}")
            await FallingEdge(self.vif.clk)
            self.seq_item_port.item_done()


class AES_Monitor(uvm_monitor):
    """Monitor for AES_ DUT."""
    
    def build_phase(self):
        self.ap = uvm_analysis_port("ap", self)
        self.vif = ConfigDB().get(self, "", "dut")
        if self.vif is not None:
            self.logger.info("Get the vif successfully")
        else:
            self.logger.error("Can't get Vif")
        
    
    async def run_phase(self):
        while True:
            txn = AES_Transaction()
            txn.cs = self.vif.cs.value
            txn.we = self.vif.we.value
            txn.address = self.vif.address.value
            txn.write_data = self.vif.write_data.value
            txn.read_data = self.vif.read_data.value
            self.ap.write(txn)
            self.logger.info(f"From Monitor --> txn: {txn}")
            await FallingEdge(self.vif.clk)


class AES_Scoreboard(uvm_subscriber):
    """Scoreboard for AES_ verification."""
    
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
        match txn.address:
            case 0x10:
                self.round_key_list.append(int(txn.write_data))
            case 0x11:
                self.round_key_list.append(int(txn.write_data))
            case 0x12:
                self.round_key_list.append(int(txn.write_data))
            case 0x13:
                self.round_key_list.append(int(txn.write_data))

            case 0x20:
                self.text_list.append(int(txn.write_data))
            case 0x21:
                self.text_list.append(int(txn.write_data))
            case 0x22:
                self.text_list.append(int(txn.write_data))
            case 0x23:
                self.text_list.append(int(txn.write_data))

            case 0x30:
                self.actual.append(txn.read_data)
                key = self.round_key.to_bytes(16, 'big')
                plaintext = self.text.to_bytes(16, 'big')
                self.expected_result = self.golden_model(key, plaintext)     
                self.logger.info(f"expected_result = 0x{self.expected_result}")
                word = 0
                self.check(word)
            case 0x31:
                self.actual.append(txn.read_data)
                word = 1
                self.check(word)
            case 0x32:
                self.actual.append(txn.read_data)
                word = 2
                self.check(word)
            case 0x33:
                self.actual.append(txn.read_data)
                word = 3
                self.check(word)

            
        if len(self.round_key_list) == 4:
            self.round_key = 0
            for word in self.round_key_list:
                self.round_key = (self.round_key << 32) | word
            self.round_key_list = []
            txn.key = self.round_key
            
        if len(self.text_list) == 4:
            self.text = 0
            for word in self.text_list:
                self.text = (self.text << 32) | word
            self.text_list = []
            txn.text = self.text
        

                
    def golden_model(self, key, plaintext):
        expected_result = []
        cipher = AES.new(key, AES.MODE_ECB)
        ciphertext = cipher.encrypt(plaintext)
        self.count += 1

        w0 = int.from_bytes(ciphertext[0:4], byteorder='big')
        w1  = int.from_bytes(ciphertext[4:8], byteorder='big')
        w2  = int.from_bytes(ciphertext[8:12], byteorder='big')
        w3  = int.from_bytes(ciphertext[12:16], byteorder='big')

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
            self.logger.info(f"Number of Matches: {self.matches}")
        
    def check_phase(self):
        """Check phase - verify results."""
        self.logger.info("=" * 60)
        self.logger.info("Scoreboard Check")
        self.logger.info(f"Total transactions: {self.count}")
        self.logger.info(f"Number of Mismatches: {self.mismatches}")
        self.logger.info(f"Number of Matches: {self.matches}")


class AES_Coverage(uvm_subscriber):
    """Coverage for advanced test."""
    
    def __init__(self, name="AdgerCoverage", parent=None):
        super().__init__(name, parent)
        self.coverage_we = {}
        self.coverage_address = {}
    
    def build_phase(self):
        """Build phase - uvm_subscriber already provides analysis export."""
        # uvm_subscriber automatically creates analysis_export, no need to create manually
        pass
    
    def write(self, txn):
        """Sample coverage."""
        address_cvg = int(txn.address)
        address_we = int(txn.we)
        #b_cvg = int(txn.write_data)
        if address_cvg not in self.coverage_address:
            self.coverage_address[address_cvg] = 0
        self.coverage_address[address_cvg] += 1

        if address_we not in self.coverage_we:
            self.coverage_we[address_we] = 0
        self.coverage_we[address_we] += 1

        print("="*150)
        print(f"Coverage sampled for bin address: {address_cvg}, unique values: {self.coverage_address}")
        print(f"Coverage sampled for bin write enable: {address_we}, unique values: {len(self.coverage_we)}")
        print("="*150)


    def report_phase(self):
        """Report phase - print coverage report."""
        self.logger.info("=" * 60)
        self.logger.info(f"[{self.get_name()}] Coverage Report")
        self.logger.info("=" * 60)
        
        """Get coverage statistics."""
        total_addr = len(self.coverage_address)
        total_we = len(self.coverage_we)
        self.logger.info(f"Address Coverage: {total_addr} unique values")
        self.logger.info(f"Write Enable Coverage: {total_we} unique values")
        
        #Coverage percentage (simplified)
        address_possible_values = 2**8  # 8-bit data
        we_possible_values = 2  # 8-bit command
        addr_percent = (total_addr / address_possible_values) * 100
        we_percent = (total_we / we_possible_values) * 100
        
        self.logger.info(f"Address Coverage: {addr_percent:.1f}%")
        self.logger.info(f"Write Enable Coverage: {we_percent:.1f}%")
        self.logger.info("=" * 60)


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
    """Environment for AES_ test."""
    
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
    """Test class for AES_."""
    
    def build_phase(self):
        """Build phase - create environment."""
        self.logger.info("=" * 60)
        self.logger.info("Building AES_Test")
        self.logger.info("=" * 60)
        self.env = AES_Env.create("env", self)
        
        self.dut = cocotb.top
        ConfigDB().set(None, "*", "dut", self.dut)
    
    async def run_phase(self):
        self.raise_objection()
        self.logger.info("Running AES_Test") 
        print("=*" * 100)      
        
        # Start sequence
        seq = AES_Sequence.create("seq")
        await seq.start(self.env.agent.seqr)
        self.drop_objection()
    
    def check_phase(self):
        self.logger.info("Checking AES_Test results")
    
    def report_phase(self):
        self.logger.info("=" * 60)
        self.logger.info("AES_Test completed")
        self.logger.info("=" * 60)

# asynchronous reset
async def async_reset(dut, duration_ns=100, propagation_delay_ns=10):
    """ Asynchronous reset sequence. """
    print("Asserting async reset...")
    
    dut.reset_n.value = 0
    await Timer(duration_ns, units="ns")
    
    print("Deasserting async reset...")
    dut.reset_n.value = 1
    # Wait for reset signal to propagate through DUT logic
    # This ensures all flip-flops have stabilized before continuing
    await Timer(propagation_delay_ns, units="ns")
    print("Reset complete")

# initialize the inputs
async def init_inputs (dut):
    print("Initializing the inputs...")
    dut.cs.value = 0
    dut.we.value = 0
    dut.write_data.value = 0

# Cocotb test function to run the pyuvm test
@cocotb.test()
async def test_AES(dut):
    """Cocotb test wrapper for AES_Test."""

    clk_period = 2
    # generating the clock
    clock = Clock(dut.clk, clk_period, unit="ns")
    cocotb.start_soon(clock.start())
    #await init_inputs(dut)
    await async_reset(dut, 5, 3)
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

