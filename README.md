<p align="center">
  <img src="https://github.com/Radwa516/silicon_sprint_auc_verification/blob/main/silicon_sprint_logo/ASIC-Hub.png" width="200">
</p>

<h1 align="center">Silicon Sprint AUC Module (6) </h1>
</p>

# Verification for AES Design using Verilator, Cocotb, and PyUVM

This project focuses on building a reusable UVM-inspired testbench with constrained-random testing and automated checking.

## Installation:
1. **Clone the repositry:**
```bash
git clone https://github.com/Radwa516/silicon_sprint_auc_verification.git  
```
2. **Using a virtual environment:**
 ```bash
python3 -m venv .venv && source .venv/bin/activate
```
3. **Install crypto library:** <br/>
It will be used as a golden model to verify the functionality of the AES design. <br/>
```bash
sudo apt update
```
```bash
pip install pycryptodome
```
4. **Install the tools**: <br/>
Run the scripts inside the Installation folder:
```bash
bash ./silicon_sprint_auc_verification/Installation/install_cocotb.sh
bash ./silicon_sprint_auc_verification/Installation/install_pyuvm.sh
bash ./silicon_sprint_auc_verification/Installation/install_verilator.sh
```
## AES Design
AES stands for ***Advanced Encryption Standard.*** We begin by using the open-source RTLs for AES by [Joachim Strömbergson](https://github.com/secworks/aes).  <br/> 

```bash
git clone https://github.com/secworks/aes
```

In summary, AES mainly performs the following five steps:
- Convert the input text into a state matrix using ASCII code.
- XOR the state matrix with the key.
> [!NOTE]
   > The key can be 128 bits, or 256 bits in this design: <br/>
   > If key is 128 bits, steps 2 to 5 are repeated for 10 rounds. <br/>
   > If key is 256 bits, steps 2 to 5 are repeated for 14 rounds. <br/>
- Substitution <br/>
Each element in the state matrix is a byte represented in hexadecimal (0x00 - 0xFF). It is replaced with the corresponding value from the S-box (substitution box). <br/>
Example: (0x01 is replaced by 0x7C)
<p align="center">
  <img src="https://captanu.wordpress.com/wp-content/uploads/2015/04/aes_sbox.jpg" width="550">
</p>

- Shift Rows <br/>
Each row is shifted (left circular shift) by its row index.
- Mix Columns <br/>
The resulting state matrix is multiplied by a fixed matrix called the Mix Columns matrix. <br/>
For more details [Click Here](https://csrc.nist.gov/files/pubs/fips/197/final/docs/fips-197.pdf).

### Some Specifications about the Design
These are the inputs and outputs of the AES module.
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
As shown above, the design has only 32-bit data access for both the plaintext and the key. Therefore, the text and key are controlled through the address mapping as follows:

   |   Address    | Purpose    |
   | ------------ | -------    |
   | 0x10 to 0x17 | Writing the key into the design (128-bit or 256-bit key). |
   | 0x20 to 0x23 | Writing the plaintext in ASCII format. |
   |     0x0A     | Selects the operation mode (encryption or decryption) and defines the key length. |
   |     0x08     | Control register: the first bit loads the key, and the second bit loads the text. |
   |     0x09     | Status register indicating the AES state (operation done or in progress). |
   | 0x30 to 0x33 | Reading the encrypted/decrypted output. |

## Why using cocotb + pyuvm?
cocotb is a Python-based verification framework used to test digital RTL designs. Instead of writing testbenches in SystemVerilog
PyUVM is a Python implementation of UVM (Universal Verification Methodology).
It brings the structure of SystemVerilog UVM into Python.
Using them together gives you the best of both:
- Cocotb as a simulation control layer which talks to the simulator (Verilator, etc.)
- PyUVM as a verification architecture layer which provides reusable UVM-style components
## UVM Environment 
A UVM environment is a modular verification structure used to verify RTL designs in a scalable and reusable way. It organizes the testbench into components that generate stimulus, drive the DUT, monitor behavior, and check correctness. <br/>
<p align="center">
  <img src="https://asicwhale.github.io/2018/07/09/201807-2018-07-09-uvm-env/uvm_example.png" width="550">
</p>

### uvm_test
It is the top-level component that configures the environment and starts the verification scenario, acting as the entry point of the simulation.
### uvm_env 
It is the container that builds and connects all verification components like agents, scoreboards, and coverage blocks. 
### uvm_agent
It groups together the driver, sequencer, and monitor to handle one communication path.
### uvm_driver
It drives the inputs to the DUT. 
### uvm_monitor 
It passively observes DUT signals and converts them back into transactions, then send the transaction to the scoreboard and the coverage classes. 
### uvm_sequencer 
controls the flow of transactions by supplying them to the driver in an organized manner.
### uvm_transaction 
It is a data object that carries stimulus and response information between components.
### uvm_sequence 
It defines the actual test scenarios by generating transactions, whether directed or random, to stimulate different design behaviors. 
### uvm_scoreboard 
It checks correctness by comparing the DUT output with a reference or golden model and reporting mismatches. 
### uvm_coverage 
It measures how much of the design functionality has been exercised to ensure thorough testing. 

## Simulation Setup
### Asynchronous Reset
In the AES design, the reset signal is an active-low asynchronous reset, which means it does not depend on the clock signal. Therefore, we use a Timer (a cocotb function) to advance the simulation time. First, we assert the reset and wait for a specific duration. Then, we deassert the reset and allow some additional time for the reset signal to propagate through the DUT logic.
  
```python

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
To generate a clock in cocotb, we use the Clock class from the cocotb clock library. Then, start_soon() is used to run it in parallel with the test (i.e., in the background).

  
```python
# generating the clock
    clk_period = 2
    clock = Clock(dut.clk, clk_period, unit="ns")
    cocotb.start_soon(clock.start())
```


### @cocotb.test
`@cocotb.test` is a decorator in cocotb used to define a test coroutine. In this test, the clock is generated and the run_test() function is called to start the UVM testbench.

```python
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
The interface is passed through the configuration database. In UVM, the top module is the only module that has visibility of the interface, which is then shared with the driver and monitor to drive or observe signals.

In cocotb and pyuvm, the DUT can be accessed directly using `cocotb.top.<signal_name>`. However, in this tutorial, the configuration database is used to emulate the SystemVerilog UVM environment. In addition, it restricts which classes can access the interface, similar to UVM’s configuration mechanisms.

```python
# Sending the interface
self.dut = cocotb.top
ConfigDB().set(None, "*", "dut", self.dut)
```
```python
#Getting the interface
try:
   self.vif = ConfigDB().get(self, "", "dut")
   self.logger.info("Got the interface successfully")
except Exception:
   self.logger.error("Can't get the interface from ConfigDB")
```
### Golden Model
The golden model is used to verify the correctness of the design by comparing its output with a reference implementation. In this project, the Python `Crypto` library is used as the golden model for AES. It takes the key and plaintext in ASCII format and returns the ciphertext. Since the DUT output is 32-bit wide, the 128-bit ciphertext is split into four 32-bit words.

```python
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
You can find the environment code in: `uvm_env/uvm_env.py`
This file contains the environment setup. Run it to ensure that the environment is working correctly.
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
After retrieving the interface from the configuration database and receiving a transaction, the driver applies the input signals to the DUT. The **AES output** becomes ready after approximately ~55 clock cycles. Therefore, after driving the key and plaintext, the driver must wait for the output to be ready without sending new transactions during this period.
<details>
<summary> driver class </summary>
  
```python
self.vif.cs.value = txn.cs
self.vif.we.value = txn.we
self.vif.address.value = txn.address
self.vif.write_data.value = txn.write_data
# waiting for the result
if (txn.address == 0x08) and (txn.we == 0) and (txn.cs == 0):
   for _ in range(55):
      await FallingEdge(self.vif.clk) 
```
</details> 

### 2) Monitoring the output
After retrieving the interface from the configuration database, the monitor observes the DUT signals and sends them to the scoreboard for result checking.

<details>
<summary> monitor class </summary>
  
```python
txn.we = self.vif.we.value
txn.address = self.vif.address.value
txn.write_data = self.vif.write_data.value
txn.read_data = self.vif.read_data.value
self.ap.write(txn)
self.logger.info(f"From Monitor --> txn: {txn}")
await FallingEdge(self.vif.clk)
```
</details> 

### 3) Sending the Transaction
There are two methods to send transactions:
- Directed Test
- Random Test
### Directed Test
In this approach, test scenarios are defined manually as follows:
- Initialize the inputs
- Send the key
- Set the configuration
- Wait
- Send the text
- Set the configuration (encryption/decryption mode)
- Wait
- Receive the **result**
### Sequence:
This class generates and sends a sequence of AES test transactions to the DUT. It defines a list of test vectors representing register writes/reads (key setup, mode selection, plaintext input, start signal, and result read). Each tuple contains: (cs, we, address, write_data) which simulates a bus transaction. Each vector is converted into a transaction object and sent to the driver using: `start_item() → finish_item()`
<details>
<summary> sequence class </summary>
  
```python
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
</details> 

## scoreboard
The scoreboard receives the output when the address is in the range 0x30 to 0x33, and compares it with the golden model.
<details>
<summary> write function </summary>
  
```python

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
</details> 

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
In this method, the inputs are randomized. In the AES design, both the key and the plaintext take random values, while the address is not randomized since it is a control signal. First, a function is created to randomize the key and plaintext based on a given range and an optional seed.

<details>
<summary> transaction class </summary>
  
```python
class AES_Transaction(uvm_sequence_item):
    
    def __init__(self, name="AES_Transaction"):
        super().__init__(name)
        self.cs = 0
        self.we = 0
        self.address = 0
        self.write_data = 0
        self.key = 0
        self.text = 0

    def randomize_constrained(self, length_min=0, length_max=0xFF, seed=None):
        if seed is not None:
            random.seed(seed)

        self.key = random.randint(length_min, length_max)
        self.text = random.randint(length_min, length_max)
    
    def __str__(self):
        return (f"cs=0x{self.cs}, we=0x{self.we}, "
                f"address={self.address}, "
                f"write_data={self.write_data}")

```
</details>

Then, the sequence uses these random values and sends them to the driver. For simplicity, two helper functions are used: `sending_key` and `sending_text`. They split the 128-bit values into four 32-bit words and send them to the DUT.

<details>
<summary> sending_key function </summary>
  
```python
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

</details>

<details>
<summary> sending_text function </summary>
  
```python

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

</details>

> [!NOTE]
> The whole code of sequence in path: Random_Test/uvm_env_rt.py <br/>

## scoreboard 
It will be slightly complex because it recieves inputs to send them to the golden model, then waiting for the result and comparing the actual result with the one from the golden model.<br/>


> [!NOTE]
> The whole code of sequence in path: Random_Test/uvm_env_rt.py

### coverage
In this class, the values taken by each signal in the design are tracked during the test to decide whether the current test cases are sufficient or need to be extended. In pyuvm, this process is simplified by collecting all sampled data and counting the number of unique values each signal takes. The coverage is then calculated by dividing the number of unique observed values by the total possible values for that signal. In real designs, achieving 100% coverage is difficult, so the goal is to reach the highest possible coverage while ensuring that any missing cases do not affect the correctness of the design.

It receives transactions from the monitor and records the unique values of address and write enable (we) in dictionaries while counting how often each value appears. In the write() function, every incoming transaction is sampled and used to update the coverage data. In the report_phase(), it calculates the number of unique values seen and converts them into simple coverage percentages based on the possible value range (8-bit address and 1-bit control signal). Finally, it prints a summary report showing how much of the design space has been exercised, helping evaluate whether the test is sufficient or needs more stimulus.

<details>
<summary> coverage class </summary>
  
```python
  class AES_Coverage(uvm_subscriber):
    
    def __init__(self, name="AdgerCoverage", parent=None):
        super().__init__(name, parent)
        self.coverage_we = {}
        self.coverage_address = {}
    
    def build_phase(self):
        # uvm_subscriber automatically creates analysis_export, no need to create manually
        pass
    
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
        self.logger.info("=" * 60)
        self.logger.info(f"[{self.get_name()}] Coverage Report")
        self.logger.info("=" * 60)
        
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
```

</details>
        
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




