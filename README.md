# Verification for AES design using Verilator, cocotb and pyuvm
This project focuses on building a reusable UVM-inspired testbench with constrained-random testing, and automated checking.
## Installation:
1. **install crypto library**: <br/>
We will use it as our golden model to check the functionality of the AES design.
```ruby
   pip install pycryptodome
```
  Using the virtual environment:
```ruby
   python3 -m venv .venv
   source .venv/bin/activate
```
2. **install the tools**: <br/>
Then run the script inside Installation file:
```ruby
   ./Installation/install_cocotb.sh
   ./Installation/install_pyuvm.sh
   ./Installation/install_verilator.sh
```
## AES Design
We will use the open-source RTLs for AES by [Joachim Strömbergson](https://github.com/secworks/aes). AES stands for standard Encription Standard. <br/> 
In summary AES do mainly five steps:
1) convert the text into a state matrix using ASKII code.
2) XORing for the state matrix with key.
> [!NOTE]
   > The key can be 128 bits, or 256 bits in our design <br/>
   > If key = 128 bits, then the steps from 2 to 5 will be repeated 10 rounds
   > If key = 256 bits, then the steps from 2 to 5 will be repeated 14 rounds
3) Substitutive <br/>
Each element in The state matrix is a byte which is written in hexa decimal (0x00 - 0xFF). We replace it with the corresponding number from the subbyte matrix. <br/>
example (0x01 replaced by 7C)
![subbyte matrix](https://captanu.wordpress.com/wp-content/uploads/2015/04/aes_sbox.jpg).
4) Shift Rows <br/>
Each row is shifted (shift left rotate) by its index.
5) Mix Columns
Multibly the result matrix with a fixed matrix called mix columns. <br/>
For more details [Click Here](https://csrc.nist.gov/files/pubs/fips/197/final/docs/fips-197.pdf).
### Some Specfications about the design
These are the inputs and the outputs.
```ruby
   module aes(
           // Clock and reset.
           input wire           clk,
           input wire           reset_n,

           // Control.
           input wire           cs, 
           input wire           we, // write enable (1 for write, 0 for read)

           // Data ports.
           input wire  [7 : 0]  address,
           input wire  [31 : 0] write_data,
           output wire [31 : 0] read_data
          );  
```
As you see there is only input for the text and the key with just 32 bits, Therfore either the text or the key is controled by the address as folowing:

   |   Address    | Purpose    |
   | ------------ | -------    |
   | From 0x10 to 0x17 | Writing the key into the design either 128 bits or 256 bits. |
   | From 0x20 to 0x23 | Writing the text in ASKII formate. |
   |     0x0A     | Choosing the operation (encription or decription) and also determine the length of the key. |
   |     0x08     | Assert the first bit to load the key, then assert the second bit to load the test. |
   |     0x09     | Knowing the state of the AES (if the result done or not). |
   | From 0x30 to 0x33 | Reading the output. |

## Why using cocotb + pyuvm?
cocotb is a Python-based verification framework used to test digital RTL designs. Instead of writing testbenches in SystemVerilog
PyUVM is a Python implementation of UVM (Universal Verification Methodology).
It brings the structure of SystemVerilog UVM into Python.
Using them together gives you the best of both:
- Cocotb as a simulation control layer which talks to the simulator (Verilator, etc.)
- PyUVM as a verification architecture layer which provides reusable UVM-style components
## UVM Environment 
A UVM environment is a modular verification structure used to verify RTL designs in a scalable and reusable way. It organizes the testbench into components that generate stimulus, drive the DUT, monitor behavior, and check correctness. <br/>
![UVM Environment](https://asicwhale.github.io/2018/07/09/201807-2018-07-09-uvm-env/uvm_example.png)
### Achynchronous Reset
In AES design, the Reset signal is active low asyncronous reset, which means we can't depend on the clock. Therfore we will use Timer (Function in python to advance the simulation time). First asserting the reset and wait for a specfic time, then deassert the reset and wait for reset signal to propagate through DUT logic.
```ruby
async def async_reset(dut, duration_ns=100, propagation_delay_ns=10):
    """ Asynchronous reset sequence. """
    print("Asserting async reset...")
    
    dut.reset_n.value = 0
    await Timer(duration_ns, units="ns")
    
    print("Deasserting async reset...")
    dut.reset_n.value = 1
    # This ensures all flip-flops have stabilized before continuing
    await Timer(propagation_delay_ns, units="ns")
    print("Reset complete")
```
### Generating Clock Signal
To generate a clock in cocotb. Use Clock function in clock library, then use start_soon() to make it run parallel with the test (run in the background).
```ruby
# generating the clock
    clk_period = 2
    clock = Clock(dut.clk, clk_period, unit="ns")
    cocotb.start_soon(clock.start())
```
### @cocotb.test
It is a decorator in cocotb. Here the clock is generate and run_test() function is called to start the uvm.
```ruby
# Cocotb test function to run the pyuvm test
@cocotb.test()
async def test_AES(dut):
    """Cocotb test wrapper for AES_Test."""
    # generating the clock
    clk_period = 2
    clock = Clock(dut.clk, clk_period, unit="ns")
    cocotb.start_soon(clock.start())
    await async_reset(dut, 5, 3)
    # await FallingEdge(dut.clk)

    # Register the test class with uvm_root so run_test can find it
    if not hasattr(uvm_root(), 'm_uvm_test_classes'):
        uvm_root().m_uvm_test_classes = {}
    uvm_root().m_uvm_test_classes["AES_Test"] = AES_Test

    # Use uvm_root to run the test properly (executes all phases in hierarchy)
    await uvm_root().run_test("AES_Test")
```
### 1. uvm_test
It is the top-level component that configures the environment and starts the verification scenario, acting as the entry point of the simulation. 
```ruby
class AES_Test(uvm_test):
    """Test class for AES_."""
    
    def build_phase(self):
        """Build phase - create environment."""
        self.env = AES_Env.create("env", self)
        #sending the DUT signals to the driver and the monitor
        self.dut = cocotb.top
        ConfigDB().set(None, "*", "dut", self.dut)
    
    async def run_phase(self):
        self.raise_objection()
        self.logger.info("Running AES_Test") 
        print("=*" * 100)      
        
        # Start sequence
        seq = AES_Sequence.create("seq")
        await seq.start(self.env.agent.seqr)
        
        await Timer(10, unit="ns")
        self.drop_objection()
    
    def report_phase(self):
        self.logger.info("=" * 60)
        self.logger.info("AES_Test completed")
        self.logger.info("=" * 60)
```
### 2. uvm_env 
It is the container that builds and connects all verification components like agents, scoreboards, and coverage blocks. 
### 3. uvm_agent
It groups together the driver, sequencer, and monitor to handle one communication path.
### 4. uvm_driver
It drives the inputs to the DUT. 
### 5. uvm_monitor 
It passively observes DUT signals and converts them back into transactions, then send the transaction to the scoreboard and the coverage classes. 
### 6. uvm_sequencer 
controls the flow of transactions by supplying them to the driver in an organized manner.
### 7. uvm_transaction 
It is a data object that carries stimulus and response information between components.
### 8. uvm_sequence 
It defines the actual test scenarios by generating transactions, whether directed or random, to stimulate different design behaviors. 
### 9. uvm_scoreboard 
It checks correctness by comparing the DUT output with a reference or golden model and reporting mismatches. 
### 10. uvm_coverage 
It measures how much of the design functionality has been exercised to ensure thorough testing. 



