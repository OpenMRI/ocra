#!/usr/bin/env python3
# assembler.py

################################################################################
#
#   Author:     Suma Anand
#   Date:       -
#
#   An assember for the Red Pitaya.
# 	Generates machine code from code written in the assembly language.
# 	Outputs two files, out_bin.txt, which contains the commands in binary,
# 	and out_hex.txt, which contains the commands in hex.
# 	See sample usage at the bottom (commented out).
# 	Comments must be prefaced by //
# 	Variables must come first
# 	Numerical values of variables must be in base 16 (hexadecimal)
#
################################################################################

import pdb # Debugging
import numpy as np
import math
import logging # For errors
import struct

class Assembler:
	def __init__(self):
		self.pc = 0
		opcode_table = {
			'NOP' : ['000000'],
			'DEC' : ['000001', 'A'],
			'INC' : ['000010', 'A'],
			'LD64' : ['000100', 'A', 'ADDR'],
			'TXOFFSET' : ['001000', 'B'],
			'GRADOFFSET' : ['001001', 'B'],
			'JNZ' : ['010000', 'A', 'ADDR'],
			'BTR' : ['010100', 'A'],
			'RET' : ['010101', 'A'],
			'J' : ['010111', 'A'],
			'HALT' : ['011001'],
			'PI' : ['011100', 'A'],
			'PR' : ['011101', 'B', 'DELAY']
		}
		bit_table = {
            'TX_PULSE': '0x01',
            'RX_PULSE': '0x02',
            'GRAD_PULSE': '0x04',
			'TX_GATE': '0x10',
			'RX_GATE': '0x20',
			#'GRAD_GATE': '0x06'
		}
		self.opcode_table = opcode_table
		self.bit_table = bit_table
		self.var_table = {}

		# Logging
		self.logger = logging.getLogger()
		logging.basicConfig(filename = 'assembler.log', filemode = 'w', level = logging.DEBUG)


	def var_parser(self,line):
		''' Parses the variables '''
		line = line.replace(' ','') # Remove spaces
		equals_index = line.find('=') # Get everything to the right of the equals sign
		cmd = line[equals_index + 1:len(line)]
		var_name = line[0:equals_index] # name of variable
		cmds_bit = []
		cmd_split = cmd.split('|') # Parse bit patterns

		# Loop over words
		for word in cmd_split:
			# Check if the word is hex
			if any(str.isdigit(c) for c in word):
				try:
					var = format(int(word, 16), 'b') # NOTE: value of var must be in base 16
					cmd_out = var.zfill(64)
					# Add entry to var_table
					self.var_table[var_name] = self.pc # Indexed by address of the variable, for LD64
					self.pc += 1
					return cmd_out

				except ValueError:
					logger.exception("Invalid hexadecimal number {}".format(cmd), stack_info=True)

			else: # Must be a bit pattern
				cmd_byte = self.bit_table.get(word)
				# If not in the dictionary, it is an invalid command
				if not cmd_byte:
					logging.error("Unknown command {}".format(word), stack_info=True)
					raise ValueError("Unknown command {}".format(word))
				cmd_bit = int(cmd_byte, 16) # Convert to bits
				cmds_bit.append(cmd_bit)

		np_bits = np.array(cmds_bit) # Make numpy array to make bitwise computation easier
		cmd_out = format(np.bitwise_or.reduce(np_bits), 'b') # String in binary
		cmd_out = cmd_out.zfill(64) # Zero pad to make it 64 bits

		# Add entry to var_table
		self.var_table[var_name] = self.pc # Indexed by address of the variable, for LD64
		self.pc += 1
		return cmd_out

	def make_cmd(self, line):
		''' Synthesizes the command in binary '''
		line = line.split(' ') # Remove spaces
		opcode = line[0] # Get the opcode

		# Error checking
		if opcode not in self.opcode_table.keys():
			logging.error("Unknown opcode {}".format(opcode), stack_info=True)
			raise ValueError("Unknown opcode {} on line {}".format(opcode, line))

		opcode_bin = self.opcode_table[opcode][0] # Convert to binary from the dict

		# Cmds without format A or B - NOP and HALT
		if len(self.opcode_table[opcode]) < 2:
			remaining_bits = 64 - len(opcode_bin)
			cmd = opcode_bin + '0'.zfill(remaining_bits)

		# Format A
		elif self.opcode_table[opcode][1] == 'A':
			reg_addr = format(int(line[1], 10), 'b').zfill(5)
			#print(reg_addr)
			if opcode == 'LD64' or opcode == 'JNZ': # Reg and addr specified
				if line[2] in self.var_table.keys():
					addr = self.var_table[line[2]] # Look up address of variable
					#print(self.var_table)
					#print(addr)

				else:
					try:
						addr = int(line[2], 16) # Must be in hex
						#print(addr)
					except ValueError:
						logger.exception("Invalid hexadecimal number {}".format(line[2]), stack_info=True)

				dir_addr = format(int(addr), 'b').zfill(32)

			elif opcode == 'DEC' or opcode == 'INC': # Reg specified
				dir_addr = '0'.zfill(32)

			else: # Addr specified
				dir_addr = format(int(line[1], 16), 'b').zfill(32)
				reg_addr = '0'.zfill(5)

			# Make the command
			remaining_bits = 64 - len(opcode_bin) - len(reg_addr) - len(dir_addr) # Remaining bits
			remainder = '0'.zfill(remaining_bits)
			cmd = opcode_bin + remainder + reg_addr + dir_addr
			self.pc += 1 # Increment pc by 1

		# Format B
		elif self.opcode_table[opcode][1] == 'B':
			if opcode == 'PR': # PR
				conversion_factor = 1/(7e-3) # us to ns, assuming 7ns clock cycle
				num_cycles = math.floor(int(line[2]) * conversion_factor) # Round down
				const = format(num_cycles, 'b').zfill(40)
				reg_addr = format(int(line[1]), 'b')
				#print(reg_addr)
				remaining_bits = 64 - len(const) - len(opcode_bin) - len(reg_addr)
				remainder = '0'.zfill(remaining_bits)
				cmd = opcode_bin + remainder + reg_addr + const
				#print(cmd)
			else: # TXOFFSET and GRADOFFSET
				# const = format(int(line[1], 16), 'b').zfill(40)
				const = format(int(line[1], 10), 'b').zfill(40)
				remaining_bits = 64 - len(const) - len(opcode_bin)
				remainder = '0'.zfill(remaining_bits)
				cmd = opcode_bin + remainder + const
		return cmd

	def strip_lines(self, line):
		''' Takes a sequence of lines and strip comments and commas '''
		line = line.replace(',','') # Remove the comma
		line = line.replace('\n', '') # Remove newline characters
		comment_index = line.find("//") # Remove comments
		if comment_index >= 0:
			line = line[:comment_index]
			line = line.strip()
		#print(line)
		return line

	def assemble(self, inp_file):
		''' Converts an input txt file to binary and outputs a text file '''
		# Open the file
		f = open(inp_file)
		self.logger.info("Opening file")
		lines = f.readlines()

    	# Parse the lines
		cmds = []
		hex_cmds = []
		line_ctr = 1
		for line in lines:
			line_stripped = self.strip_lines(line)
			self.logger.info("Line {0} stripped = {1}".format(line_ctr, line_stripped))
    		# If line contains '=', call the var parser
			if '=' in line_stripped:
				cmd = self.var_parser(line_stripped)
			else:
				cmd = self.make_cmd(line_stripped)

			# Cut the line in half to convert to byte array, otherwise it is too large
			half_len = int(len(cmd)/2)
			cmd1 = cmd[0:half_len]
			cmd2 = cmd[half_len:len(cmd)]

			# Put hex command in log, for debugging
			# hex_cmd = hex(int(cmd,2))
			hex_cmd1 = hex(int(cmd1,2))
			hex_cmd2 = hex(int(cmd2,2))
			# self.logger.info("Hex cmd = {}".format(hex_cmd))
			cmds.append(cmd) # Append the command to an array
			# hex_cmds.append(hex_cmd)
			# Reorder them
			hex_cmds.append(hex_cmd2)
			hex_cmds.append(hex_cmd1)
			line_ctr += 1

			self.logger.info("Hex cmd1 = {}\n".format(hex_cmd1))
			self.logger.info("Hex cmd2 = {}\n".format(hex_cmd2))


		# Make a byte array of hex commands
		# hex_cmd = format(int(hex_cmd,16),'x') # remove the 0x at the beginning


		hex_ints = [int(hex_cmd, 16) for hex_cmd in hex_cmds]
		self.logger.info("Hex ints = {}\n".format(hex_ints))

		# Convert to byte array
		b = bytes()
		hex_bytes = [struct.pack('<I', hex_int) for hex_int in hex_ints]
		b = b.join(hex_bytes)

		# Logging
		self.logger.info("Hex bytes = {}\n".format(hex_bytes))
		self.logger.info("Length of hex bytes = {}\n".format(len(hex_bytes)))
		self.logger.info("b = {}".format(b))
		self.logger.info("Length of byte array = {}".format(len(b)))

		# # Binary file
		# with open('out_bin.txt', "w") as out_file:
		# 	[out_file.write("{}\n".format(cmd)) for cmd in cmds]
        #
		# # Hex file
		# with open('out_hex.txt', "w") as out_file:
		# 	[out_file.write("{}\n".format(hex_cmd)) for hex_cmd in hex_cmds]
		# self.logger.info('Done')

		# Machine code file
		output_filename = inp_file[0:-4] + '_hex.txt'
		with open(output_filename, "w") as out_file:
			idx = 0
			for hex_cmd in hex_cmds:
				# # for generating only machine cmd
				# if idx%2: # odd idx, even row num
				# 	out_file.write("pulseq_memory[{}] = {};\n\n".format(idx, hex_cmd))
				# else: # even idx, odd row num
				# 	out_file.write("pulseq_memory[{}] = {}; \n".format( idx, hex_cmd))

				# for generating readable machine code
				if idx%2: # odd idx, even row num
					out_file.write("\tpulseq_memory[{}] = {}\n\n".format(idx, hex_cmd))
				else: # even idx, odd row num
					out_file.write("A[{}]\tpulseq_memory[{}] = {} \n".format( hex(int(idx/2)),
								   idx, hex_cmd))
				idx += 1

		f.close()
		return b

assembler = Assembler()

# Sample usage
if __name__ == "__main__":
	a = Assembler()
	inp_file = 'sequence/basic/se_default.txt'
	hex_bytes = a.assemble(inp_file)
	#print("Hex bytes = {}\n".format(hex_bytes))
