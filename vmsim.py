#!/usr/bin/env python3

import sys
import re
import math
import os.path
from collections import OrderedDict
from collections import defaultdict

# Global Variables  
algo = ""
num_frames = 0
page_size = 0
p0_num_frames = 0
p1_num_frames = 0
p0_memsplit_int = 0
p1_memsplit_int = 0
page_offset_bits = 0
page_address_bits = 0
num_page_faults = 0
num_mem_accesses = 0
num_disk_writes = 0
filename = ""
mem_ratio_regex = '\d+:\d+'
opt_hash_table_p0 = {}
opt_hash_table_p1 = {}
p0_page_table = OrderedDict()
p1_page_table = OrderedDict()

# Parses the command line arguments in following form:
# ./vmsim -a <opt|lru> n <numframes> -p <pagesize in KB(4)> -s <memory split> <tracefile>
# Sets up everything prior to reading trace file
def start_vmsim():

    # CL and other setup data
    global algo
    global num_frames
    global page_size
    global p0_memsplit_int
    global p1_memsplit_int
    global filename
    global p0_num_frames
    global p1_num_frames
    global page_offset_bits
    global page_address_bits
    global page_offset_bytes
    split_ratio = 0
    address_size = 32
    
    # Error Check CL input
    if sys.argv[1] != "-a":
        print("Invalid Algorithm Flag Arg")
        exit()
    if sys.argv[2] != "opt" and sys.argv[2] != "lru":
        print("Invalid Algorithm Arg")
        exit()
    if sys.argv[3] != "-n":
        print("Invalid Frame Number Flag Arg")
        exit()
    if not sys.argv[4].isdigit():
        print("Invalid Number of Frames Arg")
        exit()
    if sys.argv[5] != "-p":
        print("Invalid Page Size Flag Arg")
        exit()
    if not sys.argv[6].isdigit():
        print("Invalid Page Size Arg")
        exit()
    if sys.argv[7] != "-s":
        print("Invalid Memory Split Flag Arg")
        exit()

    match = re.search(mem_ratio_regex, sys.argv[8])
    if not match:
        print("Invalid Memory Split Arg")
        exit()

    p0_memsplit_int = int(match.string.split(":")[0])
    p1_memsplit_int = int(match.string.split(":")[1])
    if not match.string.split(":")[0].isdigit() and match.string.split(":")[1].isdigit():
        print("Memory Split Error - invalid int parsing")
        exit()
    
    if not os.path.isfile(sys.argv[9]):
        print("Invalid file")
        exit()

    # Initializes VM data
    algo = sys.argv[2]
    num_frames = int(sys.argv[4])
    page_size = int(sys.argv[6])
    filename = sys.argv[9]

    # BONUS 64 bit address (Implement if time)
    if("64" in filename):
        exit()
        #address_size = 64

    # Calculate # blocks of memory each process gets
    if(p0_memsplit_int/p1_memsplit_int == 1):
        split_ratio = .5
        p0_num_frames = num_frames/2
        p1_num_frames = num_frames/2
        
    if(p0_memsplit_int/p1_memsplit_int > 1):
        split_ratio = float(p1_memsplit_int)/float(p0_memsplit_int)
        p1_num_frames = int(math.floor(float(split_ratio) * float(num_frames)))
        p0_num_frames = int(num_frames) - p1_num_frames

    if((p0_memsplit_int/p1_memsplit_int < 1)):
        split_ratio = float(p0_memsplit_int)/float(p1_memsplit_int)
        p0_num_frames = int(math.floor(split_ratio * float(num_frames)))
        p1_num_frames = int(num_frames) - int(math.floor(split_ratio * float(num_frames)))

    # Get page offset and number in bytes
    page_offset_bits = math.log((float(int(page_size)*1024)),2)
    page_address_bits = address_size - int(page_offset_bits)

    page_offset_bytes = int(math.ceil(page_offset_bits/4))

################################################### LRU ########################################################

# Simulates LRU algorithm
def simulate_lru():
    global num_mem_accesses
    global num_page_faults
    global num_disk_writes
    global filename
    global curr_line_number
    global page_offset_bits
    global num_frames
    global p0_num_frames
    global p1_num_frames
    
    input_file = open(filename, "r")

    # For every line in the input file
    for line in input_file:

        # Split the data (s 0x39c113f0 1)
        line_data = line.split()
        access_type = line_data[0]
        accessed_address = line_data[1]
        process_num = line_data[2]

        # Retreive page number from address and go to process's page table
        accessed_address = accessed_address[2:]
        accessed_address = (bin(int(accessed_address, 16))[2:]).zfill(32)
        page_num = accessed_address[:page_address_bits]
       
        if(process_num == "0"):
            enter_lru_page_table(page_num, access_type, p0_page_table, p0_num_frames)

        if(process_num == "1"):
            enter_lru_page_table(page_num, access_type, p1_page_table, p1_num_frames)
        
        # Increment number of memory accesses
        num_mem_accesses = num_mem_accesses + 1

    # Close tracefile
    input_file.close() 


# Processes the memory access 
def enter_lru_page_table(memory_address, access_type, page_table, num_frames):
    global num_page_faults
    global num_disk_writes
    
    # Sets dirty bit depending on current access type
    if(access_type == "s"):
        dirty_bit_new = 1
    else:
        dirty_bit_new = 0
    
    # If the page is already in memory (Memory Hit)
    if(memory_address in page_table):
        
        # Remove the entry
        updated_entry = page_table.pop(memory_address)

        # If the newest access is a store, check dirty bit and add to MRU 
        if(dirty_bit_new):
            page_table[memory_address] = 1
        else:
            page_table[memory_address] = updated_entry

    # If the page is not in memory (Page Fault)
    else:

        # Increment number of page faults
        num_page_faults = num_page_faults + 1

        # If space in page table, add entry
        if(len(page_table) < num_frames):
            page_table[memory_address] = dirty_bit_new
        
        # If no space, evict LRU entry
        else:
            key = next(iter(page_table))
            dirty_bit = page_table.pop(key)
        
            # Dirty Eviction 
            if(dirty_bit):
                num_disk_writes = num_disk_writes + 1

            # Add the new entry
            page_table[memory_address] = dirty_bit_new


################################################## OPT ################################################

# Simulates OPT algorithm
def create_opt_hash_tables():
    global filename
    global opt_hash_table_p0
    global opt_hash_table_p1
    
    opt_hash_table_p0 = defaultdict(list)
    opt_hash_table_p1 = defaultdict(list)

    input_file = open(filename, "r")

    accessed_line = 1
    
    # For every line in the input file
    for line in input_file:

        # Split and parse line data
        line_data = line.split()
        accessed_address = line_data[1]
        process_num = line_data[2]

        # Get page number from memory address
        accessed_address = accessed_address[2:]
        accessed_address = (bin(int(accessed_address, 16))[2:]).zfill(32)
        page_num = accessed_address[:page_address_bits]

        # Memory accessed by p0
        if(process_num == "0"):
            opt_hash_table_p0[page_num].append(accessed_line)

        # Memory accessed by p1
        else:
            opt_hash_table_p1[page_num].append(accessed_line)
        
        accessed_line = accessed_line + 1

    input_file.close()
    

def simulate_opt():
    global num_mem_accesses
    global page_offset_bits
    global p0_page_table  
    global p1_page_table 

    line_num = 1

    input_file = open(filename, "r")

    # Creates hash tables for P0 and P1
    create_opt_hash_tables()
  
    # For every line in the input file
    for line in input_file:

        # Split and parse line data
        line_data = line.split()
        access_type = line_data[0]
        accessed_address = line_data[1]
        process_num = line_data[2]

        # Obtain value of page address
        accessed_address = accessed_address[2:]
        accessed_address = (bin(int(accessed_address, 16))[2:]).zfill(32)
        page_num = accessed_address[:page_address_bits]
 
        if(process_num == "0"):
            enter_opt_page_table(page_num, access_type, line_num, p0_page_table, p0_num_frames, opt_hash_table_p0)

        else:
            enter_opt_page_table(page_num, access_type, line_num, p1_page_table, p1_num_frames, opt_hash_table_p1)
        
        # Increment number of memory accesses
        num_mem_accesses = num_mem_accesses + 1

        line_num = line_num + 1 
        
    # Close tracefile
    input_file.close()



def enter_opt_page_table(memory_address, access_type, line_num, page_table , num_frames, hash_table):
    global num_page_faults
    global num_disk_writes
    
    # Sets dirty bit depending on access type
    if(access_type == "s"):
        dirty_bit_new = 1
    else:
        dirty_bit_new = 0

    # If the page is already in memory (Memory Hit)
    if(memory_address in page_table):

        # Move the entry to the back and update dirty bit
        updated_entry = page_table.pop(memory_address)

        if(dirty_bit_new):
            page_table[memory_address] = 1
        else:
            page_table[memory_address] = updated_entry

    # If the page is not in memory (Page Fault)
    else:
        # Increment page faults
        num_page_faults = num_page_faults + 1

        # If space, add entry
        if(len(page_table) < num_frames):
            page_table[memory_address] = dirty_bit_new

        # If no space, evict the optimal page
        else: 
            opt_evict_page = find_opt_page(line_num, memory_address, page_table, hash_table)
            dirty_bit = page_table.get(opt_evict_page)

            # Dirty Eviction
            if(page_table.get(opt_evict_page)):
                num_disk_writes = num_disk_writes + 1

            # Delete from the page table
            del page_table[opt_evict_page]

            # Add the new entry
            page_table[memory_address] = dirty_bit_new

    # Remove the line number from the hash list
    hash_table[memory_address].remove(line_num)

# Returns the optimal page for replacement in P0 table
def find_opt_page(curr_line, replacement_page, page_table, hash_table):

    # Keeps track of potential removal victims
    no_future_ref = []
    last_ref_dict = {}
    
    # For each page in memory
    for mem_addr in page_table:

        # If the memory page is in the hash table
        if(replacement_page == mem_addr):
            continue

        # If the length of list of future accesses is 0 (never used again)
        if(len(hash_table[mem_addr]) == 0):
            no_future_ref.append(mem_addr)

        # If the memory will be used again in the future 
        # Select the furthest of the next addresses
        else:
            future_mem_ref_list = hash_table[mem_addr]
            last_ref_dict[mem_addr] = future_mem_ref_list[0]
   
    # If 1 page is never used in the future, evict it
    if((len(no_future_ref) == 1)):
        return no_future_ref[0]
    
    # If 2+ pages are never used in the future, evict the LRU of them 
    elif(len(no_future_ref) >= 2):
        return lru_page(no_future_ref, page_table)

    # All pages will be used, returns the page used furthest in the future
    else:
        return max(last_ref_dict, key=last_ref_dict.get)

# Returns the LRU page of a page table from a given list
def lru_page(unused_page_list, page_table):
    # Retreive the LRU process from the page table to evict
    for proc in page_table:
        for unused_mem in unused_page_list:
            if(proc == unused_mem):
                return proc


###################################################################################
# Cleans up, prints stats, and exits
def close_vmsim():
    print("Algorithm: " + algo.upper())
    print("Number of frames: " + str(num_frames)) 
    print("Page size: " + str(page_size) + " KB")
    print("Total memory accesses: " + str(num_mem_accesses))
    print("Total page faults: " + str(num_page_faults))
    print("Total writes to disk: " + str(num_disk_writes))
    exit()

# Main function 
def main():
    start_vmsim()

    if(algo == "lru"):
        simulate_lru()
    else:
        simulate_opt()
    
    close_vmsim()

# Runs main()
if __name__ == "__main__":
    main()
