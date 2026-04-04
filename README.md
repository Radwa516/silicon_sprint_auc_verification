# AUC Silicon Sprint

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
### 1. uvm_test
It is the top-level component that configures the environment and starts the verification scenario, acting as the entry point of the simulation.
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
![UVM Environment](https://asicwhale.github.io/2018/07/09/201807-2018-07-09-uvm-env/uvm_example.png)
## Simulation Setup
### Achynchronous Reset
In AES design, the Reset signal is active low asyncronous reset, which means we can't depend on the clock. Therfore we will use Timer (Function in python to advance the simulation time). First asserting the reset and wait for a specfic time, then deassert the reset and wait for reset signal to propagate through DUT logic.

```ruby

async def async_reset(dut, duration_ns=100, propagation_delay_ns=10):
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
### Configration Data Base
The interface is sent throught it. In UVM, the top module is the only module that sees the interface, so the interface can be shared to the driver and the monitor to drive or observe the signals. But in cocotb and pyuvm, The interface ca be accessed by using **cocotb.top.<signal_name>**. However in the tutorial, configDB is used to simulate the SystemVerilog environment. In addtition, To limit the classed that can access the interface as in UVM.
```ruby
# Sending the interface
self.dut = cocotb.top
ConfigDB().set(None, "*", "dut", self.dut)
```
```ruby
try:
   self.vif = ConfigDB().get(self, "", "dut")
   self.logger.info("Got the interface successfully")
except Exception:
   self.logger.error("Can't get the interface from ConfigDB")
```
### Golden Model
It is important to compare the design with it. In library Crypto in python, there is an AES that can be used as a golden model. It takes the key and the text in ASKII format then return the result. After getting the result separate into four words because the output read_data is only 32 bits.
```ruby
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
```
## Running the code
You will find the code of the environment in: **uvm_env/uvm_env.py**
This is an environment setup. Run it to make sure that the environment is running fine. 
After running, you should see:
```
19.00ns INFO     cocotb.regression                  uvm_env.test_AES passed                                                                                             
19.00ns INFO     cocotb.regression                  
**************************************************************************************                                                                                  
** TEST                          STATUS  SIM TIME (ns)  REAL TIME (s)  RATIO (ns/s) **
**************************************************************************************                                                                                  
** uvm_env.test_AES               PASS          19.00           0.01       1580.84  ** 
**************************************************************************************
** TESTS=1 PASS=1 FAIL=0 SKIP=0                 19.00           0.01       1334.51  **
**************************************************************************************                                                                                                                                                                         
```
### 1) Driving the inputs
After retrieve the interface from the configration data base, waiting for the transaction, then driving the input signal.
The output of the AES be ready after about 55 clock cycle. After driving the key and the text, wait for the output to be ready 
without driving any new test cases. 
```ruby
self.vif.cs.value = txn.cs
self.vif.we.value = txn.we
self.vif.address.value = txn.address
self.vif.write_data.value = txn.write_data
# waiting for the result
if (txn.address == 0x08) and (txn.we == 0) and (txn.cs == 0):
   for _ in range(55):
      await FallingEdge(self.vif.clk) 
```
### 2) Monitoring the output
After retrieve the interface from the configration data base, observe the DUT signals and sent them to the scoreboard to check the output.
In addition
```ruby
txn.we = self.vif.we.value
txn.address = self.vif.address.value
txn.write_data = self.vif.write_data.value
txn.read_data = self.vif.read_data.value
self.ap.write(txn)
self.logger.info(f"From Monitor --> txn: {txn}")
await FallingEdge(self.vif.clk)
```
### 3) Sending the Transaction
There are two methods to send the transaction:
- Directed Test
- Random Test
### Directed Test
Put the test senarios maiually as the following:
- First Initialize the inputs
- Send the key
- Put the configration
- Wait
- Send the text
- Put the configration (encryption/decryption)
- Wait
- Recieve the **result**
```ruby
class AES_Sequence(uvm_sequence):
    """Sequence generating AES_ test vectors."""
    
    async def body(self):
        """Generate test vectors."""
        # (cs, we, address, write_data)
        test_vectors = [
            # Initialize the inputs
            (0, 0, 0x00, 0x00000000),
            # Write key
            (1, 1, 0x10, 0x2b7e1516),
            (1, 1, 0x11, 0x28aed2a6),
            (1, 1, 0x12, 0xabf71588),
            (1, 1, 0x13, 0x09cf4f3c),
            (1, 1, 0x14, 0x00000000),
            (1, 1, 0x15, 0x00000000),
            (1, 1, 0x16, 0x00000000),
            (1, 1, 0x17, 0x00000000),

            # Determine the length of the key (128-bit)
            (1, 1, 0x0A, 0x00000000),

            # Load the key (build key schedule)
            (1, 1, 0x08, 0x00000001),

            # Waiting for the key to be loaded
            (0, 0, 0x08, 0x00000001),

            # Write the plaintext
            (1, 1, 0x20, 0x6bc1bee2),
            (1, 1, 0x21, 0x2e409f96),
            (1, 1, 0x22, 0xe93d7e11),
            (1, 1, 0x23, 0x7393172a),

            # Set the operation (encryption)
            (1, 1, 0x0A, 0x00000001),

            # START encryption
            (1, 1, 0x08, 0x00000002),

            # Waiting for the result
            (0, 0, 0x08, 0x00000002),

            # Read the result
            (1, 0, 0x30, 0x00000002),
            (1, 0, 0x31, 0x00000002),
            (1, 0, 0x32, 0x00000002),
            (1, 0, 0x33, 0x00000002),
        ]
        
        for cs, we, address, write_data in test_vectors:
            txn = AES_Transaction()
            txn.cs = cs
            txn.we = we
            txn.address = address
            txn.write_data = write_data
            await self.start_item(txn)
            await self.finish_item(txn)
```
**scoreboard**
It receives output when address = 0x30 - 0x33, and comparing it with the golden model
```ruby
def write(self, txn):
   """Receive transactions from monitor."""
   self.logger.info(f"Scoreboard received: {txn}")
   key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
   plaintext = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
   match txn.address:
      case 0x30:
         self.actual.append(txn.read_data)
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
```
> [!NOTE]
> The whole code of sequence in path: Directed_Test/uvm_env_dt.py
## Running the directed test code
```ruby
====================================================================================================                                                                       
265.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(122) [uvm_test_top.env.agent.driver]: From Driver --> txn: cs=0x1, we=0x0, address=48, write_data=2                     
267.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(171) [uvm_test_top.env.scoreboard]: Scoreboard received: cs=0x1, we=0x0, address=00110000                                                                                                                                                         
267.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(178) [uvm_test_top.env.scoreboard]: expected_result = 0x[987200436, 226113120, 2828978931, 610725783]                   
267.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(215) [uvm_test_top.env.scoreboard]: Match: ciphertext = 0x3AD77BB4, actual data = 0x3AD77BB4                                           
267.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(150) [uvm_test_top.env.agent.monitor]: From Monitor --> txn: cs=0x1, we=0x0, address=00110000
====================================================================================================                                                                       
267.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(122) [uvm_test_top.env.agent.driver]: From Driver --> txn: cs=0x1, we=0x0, address=49, write_data=2                     
269.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(171) [uvm_test_top.env.scoreboard]: Scoreboard received: cs=0x1, we=0x0, address=00110001                                                                                                                                                          
269.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(215) [uvm_test_top.env.scoreboard]: Match: ciphertext = 0x D7A3660, actual data = 0x D7A3660                    
269.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(150) [uvm_test_top.env.agent.monitor]: From Monitor --> txn: cs=0x1, we=0x0, address=00110001                                             ====================================================================================================                                                                       
269.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(122) [uvm_test_top.env.agent.driver]: From Driver --> txn: cs=0x1, we=0x0, address=50, write_data=2                     
271.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(171) [uvm_test_top.env.scoreboard]: Scoreboard received: cs=0x1, we=0x0, address=00110010,                                                                                                                                                        
271.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(215) [uvm_test_top.env.scoreboard]: Match: ciphertext = 0xA89ECAF3, actual data = 0xA89ECAF3      
271.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(150) [uvm_test_top.env.agent.monitor]: From Monitor --> txn: cs=0x1, we=0x0, address=00110010
====================================================================================================                                                                       
271.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(122) [uvm_test_top.env.agent.driver]: From Driver --> txn: cs=0x1, we=0x0, address=51, write_data=2                     
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(171) [uvm_test_top.env.scoreboard]: Scoreboard received: cs=0x1, we=0x0, address=00110011                                                                                                                                                         
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(215) [uvm_test_top.env.scoreboard]: Match: ciphertext = 0x2466EF97, actual data = 0x2466EF97    
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(150) [uvm_test_top.env.agent.monitor]: From Monitor --> txn: cs=0x1, we=0x0, address=00110011                                             ====================================================================================================                                                                                      
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(307) [uvm_test_top]: Checking AES_Test results                                                                          
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(221) [uvm_test_top.env.scoreboard]: ============================================================                        
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(222) [uvm_test_top.env.scoreboard]: Scoreboard Check                                                                    
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(223) [uvm_test_top.env.scoreboard]: Total transactions: 1                                                               
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(224) [uvm_test_top.env.scoreboard]: Number of Mismatches: 0                                                             
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(225) [uvm_test_top.env.scoreboard]: Number of Matches: 4                                                                
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(310) [uvm_test_top]: ==================================================                                                 
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(311) [uvm_test_top]: AES_Test completed                                                                                 
273.00ns INFO     ../AES_ENV/uvm_env/uvm_env.py(312) [uvm_test_top]: ==================================================                                                 
273.00ns INFO     cocotb.regression                  uvm_env.test_AES passed                                                                                            
273.00ns INFO     cocotb.regression                  
**************************************************************************************                                                                                  
** TEST                          STATUS  SIM TIME (ns)  REAL TIME (s)  RATIO (ns/s) **
**************************************************************************************                                                                                  
** uvm_env.test_AES               PASS         273.00           0.06       4290.87  **
**************************************************************************************                                                                                  
** TESTS=1 PASS=1 FAIL=0 SKIP=0                273.00           0.06       4219.65  **
**************************************************************************************      
```
## Random Test
In this method the inputs is randomized. In AES design, the key and the text will take random values. Address can't be randomized as it is a control signal.
First build a function to random the key and the text based on a specifc size and a seed.
```ruby
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

```
Then the sequence is using those random values and sending it to the driver. For simplifity, sending_key function and sending_text are built. they receive the random 128 bits and separating them into four words, then send them:
```ruby
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
```
```ruby

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
```
> [!NOTE]
> The whole code of sequence in path: Random_Test/uvm_env_rt.py <br/>
**scoreboard** <br/>
It will be slightly complex because it recieves inputs to send them to the golden model, then waiting for the result and comparing the actual result with the one from the golden model.<br/>


> [!NOTE]
> The whole code of sequence in path: Random_Test/uvm_env_rt.py
### coverage
In this class, we count which values each pin in the design took during the test to decide, if we can stop here or increase that test cases. In pyuvm, It is too simple. It collect all the data then count the number of unique values that each pin took. after counting, It devides the number / total possible values for this signal. In real designs, it is hard to achieve 100% coverage, but they tried to reach the highst possible value and make sure that the missing test cases don't affect the design.
> [!NOTE]
> The whole code of sequence in path: Random_Test/uvm_env_rt.py
## Running the random test code
```ruby                                                                                                                                                  
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(450) [uvm_test_top]: Checking AES_Test results                                                                        
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(333) [uvm_test_top.env.scoreboard]: ============================================================                      
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(334) [uvm_test_top.env.scoreboard]: Scoreboard Check                                                                  
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(335) [uvm_test_top.env.scoreboard]: Total transactions: 50                                                            
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(336) [uvm_test_top.env.scoreboard]: Number of Mismatches: 0                                                           
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(337) [uvm_test_top.env.scoreboard]: Number of Matches: 200                                                            
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(453) [uvm_test_top]: ============================================================                                     
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(454) [uvm_test_top]: AES_Test completed                                                                               
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(455) [uvm_test_top]: ============================================================                                     
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(374) [uvm_test_top.env.coverage]: ============================================================                        
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(375) [uvm_test_top.env.coverage]: [coverage] Coverage Report                                                          
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(376) [uvm_test_top.env.coverage]: ============================================================                        
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(381) [uvm_test_top.env.coverage]: Address Coverage: 19 unique values                                                  
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(382) [uvm_test_top.env.coverage]: Write Enable Coverage: 2 unique values                                              
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(390) [uvm_test_top.env.coverage]: Address Coverage: 7.4%                                                              
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(391) [uvm_test_top.env.coverage]: Write Enable Coverage: 100.0%                                                       
13307.00ns INFO     ..e/AES_ENV/uvm_env/Random.py(392) [uvm_test_top.env.coverage]: ============================================================                        
13307.00ns INFO     cocotb.regression                  Random.test_AES passed                                                                                           
13307.00ns INFO     cocotb.regression                  
**************************************************************************************                                                                                  
** TEST                          STATUS  SIM TIME (ns)  REAL TIME (s)  RATIO (ns/s) **
**************************************************************************************                                                                                  
** Random.test_AES                PASS       13307.00           6.26       2125.08  **
**************************************************************************************                                                                                  
** TESTS=1 PASS=1 FAIL=0 SKIP=0              13307.00           6.26       2124.38  **
**************************************************************************************
```




