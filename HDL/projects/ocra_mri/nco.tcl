#
# nco.tcl
# 2017 by Thomas Witzel
# block design for the NCO 

# Create xlslice
cell xilinx.com:ip:xlslice:1.0 slice_1 {
  DIN_WIDTH 64 DIN_FROM 31 DIN_TO 0 DOUT_WIDTH 32
}

# Create axis_constant
cell pavel-demin:user:axis_constant:1.0 phase_nco {
  AXIS_TDATA_WIDTH 32
} {
  cfg_data slice_1/Dout
  aclk /ps_0/FCLK_CLK0
}

# Create dds_compiler
cell xilinx.com:ip:dds_compiler:6.0 dds_nco {
  DDS_CLOCK_RATE 125
  SPURIOUS_FREE_DYNAMIC_RANGE 138
  FREQUENCY_RESOLUTION 0.2
  PHASE_INCREMENT Streaming
  HAS_TREADY true
  HAS_PHASE_OUT false
  PHASE_WIDTH 30
  OUTPUT_WIDTH 24
  DSP48_USE Minimal
  NEGATIVE_SINE true
} {
  S_AXIS_PHASE phase_nco/M_AXIS
  aclk /ps_0/FCLK_CLK0
}

# Create axis_broadcaster, no remapping as the stream is copied exactly
# 3 bytes width as thats what the output of the DDS is
cell xilinx.com:ip:axis_broadcaster:1.1 bcast_nco {
  S_TDATA_NUM_BYTES.VALUE_SRC USER
  M_TDATA_NUM_BYTES.VALUE_SRC USER
  S_TDATA_NUM_BYTES 6
  M_TDATA_NUM_BYTES 6
  M00_TDATA_REMAP {tdata[47:0]}
  M01_TDATA_REMAP {tdata[47:0]}
} {
  S_AXIS dds_nco/M_AXIS_DATA
  aclk /ps_0/FCLK_CLK0
  aresetn /rst_0/peripheral_aresetn
}
