global fclk
global f_aresetn
global f_reset
global pl_param_dict

# Create xlslice
# Trigger slice on Bit 1 (RX pulse)
cell xilinx.com:ip:xlslice:1.0 slice_0 {
  DIN_WIDTH 8 DIN_FROM 1 DIN_TO 1 DOUT_WIDTH 1
}

# Create xlslice
cell xilinx.com:ip:xlslice:1.0 rate_slice {
  DIN_WIDTH 32 DIN_FROM 15 DIN_TO 0 DOUT_WIDTH 16
}

# Create xlconstant
cell xilinx.com:ip:xlconstant:1.1 const_0

# Create axis_clock_converter
cell xilinx.com:ip:axis_clock_converter:1.1 fifo_0 {
  TDATA_NUM_BYTES.VALUE_SRC USER
  TDATA_NUM_BYTES 4
} {
  m_axis_aclk $fclk
  m_axis_aresetn $f_aresetn
}

if { [dict get $pl_param_dict modulated] == "TRUE"} {
    # Create axis_lfsr
    cell pavel-demin:user:axis_lfsr:1.0 lfsr_0 {} {
      aclk $fclk
      aresetn $f_aresetn
    }
    # Create cmpy
    cell xilinx.com:ip:cmpy:6.0 mult_0 {
      FLOWCONTROL Blocking
      APORTWIDTH.VALUE_SRC USER
      BPORTWIDTH.VALUE_SRC USER
      APORTWIDTH 16
      BPORTWIDTH 24
      ROUNDMODE Random_Rounding
      OUTPUTWIDTH 26
    } {
      S_AXIS_A fifo_0/M_AXIS
      S_AXIS_CTRL lfsr_0/M_AXIS
      aclk $fclk
    }
    # Create axis_broadcaster
    cell xilinx.com:ip:axis_broadcaster:1.1 bcast_0 {
      S_TDATA_NUM_BYTES.VALUE_SRC USER
      M_TDATA_NUM_BYTES.VALUE_SRC USER
      S_TDATA_NUM_BYTES 8
      M_TDATA_NUM_BYTES 3
      M00_TDATA_REMAP {tdata[23:0]}
      M01_TDATA_REMAP {tdata[55:32]}
    } {
      S_AXIS mult_0/M_AXIS_DOUT
      aclk $fclk
      aresetn $f_aresetn
    }
} else {
    # Create axis_broadcaster
    cell xilinx.com:ip:axis_broadcaster:1.1 bcast_0 {
      S_TDATA_NUM_BYTES.VALUE_SRC USER
      M_TDATA_NUM_BYTES.VALUE_SRC USER
      S_TDATA_NUM_BYTES 4
      M_TDATA_NUM_BYTES 3
      M00_TDATA_REMAP {tdata[15:0],  8'b0}
      M01_TDATA_REMAP {tdata[31:16], 8'b0}
    } {
      S_AXIS fifo_0/M_AXIS
      aclk $fclk
      aresetn $f_aresetn
    }
}

# Create axis_variable
cell pavel-demin:user:axis_variable:1.0 rate_0 {
  AXIS_TDATA_WIDTH 16
} {
  cfg_data rate_slice/Dout
  aclk $fclk
  aresetn $f_aresetn
}

# Create axis_variable
cell pavel-demin:user:axis_variable:1.0 rate_1 {
  AXIS_TDATA_WIDTH 16
} {
  cfg_data rate_slice/Dout
  aclk $fclk
  aresetn $f_aresetn
}

# Create cic_compiler
cell xilinx.com:ip:cic_compiler:4.0 cic_0 {
  INPUT_DATA_WIDTH.VALUE_SRC USER
  FILTER_TYPE Decimation
  NUMBER_OF_STAGES 6
  SAMPLE_RATE_CHANGES Programmable
  MINIMUM_RATE 25
  MAXIMUM_RATE 8192
  FIXED_OR_INITIAL_RATE 625
  INPUT_SAMPLE_FREQUENCY 125
  CLOCK_FREQUENCY 125
  INPUT_DATA_WIDTH 24
  QUANTIZATION Truncation
  OUTPUT_DATA_WIDTH 24
  USE_XTREME_DSP_SLICE false
  HAS_DOUT_TREADY true
  HAS_ARESETN true
} {
  S_AXIS_DATA bcast_0/M00_AXIS
  S_AXIS_CONFIG rate_0/M_AXIS
  aclk $fclk
  aresetn $f_aresetn
}

# Create axis_subset_converter
cell xilinx.com:ip:axis_subset_converter:1.1 cic_data_resize_0 {
  S_TDATA_NUM_BYTES.VALUE_SRC USER
  M_TDATA_NUM_BYTES.VALUE_SRC USER
  S_TDATA_NUM_BYTES 3
  M_TDATA_NUM_BYTES 4
  TDATA_REMAP {tdata[23:0], 8'b0}
} {
  S_AXIS cic_0/M_AXIS_DATA
  aclk $fclk
  aresetn $f_aresetn
}

# Create cic_compiler
cell xilinx.com:ip:cic_compiler:4.0 cic_1 {
  INPUT_DATA_WIDTH.VALUE_SRC USER
  FILTER_TYPE Decimation
  NUMBER_OF_STAGES 6
  SAMPLE_RATE_CHANGES Programmable
  MINIMUM_RATE 25
  MAXIMUM_RATE 8192
  FIXED_OR_INITIAL_RATE 625
  INPUT_SAMPLE_FREQUENCY 125
  CLOCK_FREQUENCY 125
  INPUT_DATA_WIDTH 24
  QUANTIZATION Truncation
  OUTPUT_DATA_WIDTH 24
  USE_XTREME_DSP_SLICE false
  HAS_DOUT_TREADY true
  HAS_ARESETN true
} {
  S_AXIS_DATA bcast_0/M01_AXIS
  S_AXIS_CONFIG rate_1/M_AXIS
  aclk $fclk
  aresetn $f_aresetn
}

# Create axis_subset_converter
cell xilinx.com:ip:axis_subset_converter:1.1 cic_data_resize_1 {
  S_TDATA_NUM_BYTES.VALUE_SRC USER
  M_TDATA_NUM_BYTES.VALUE_SRC USER
  S_TDATA_NUM_BYTES 3
  M_TDATA_NUM_BYTES 4
  TDATA_REMAP {tdata[23:0], 8'b0}
} {
  S_AXIS cic_1/M_AXIS_DATA
  aclk $fclk
  aresetn $f_aresetn
}

# Create axis_combiner
cell  xilinx.com:ip:axis_combiner:1.1 comb_0 {
  TDATA_NUM_BYTES.VALUE_SRC USER
  TDATA_NUM_BYTES 4
} {
  S00_AXIS cic_data_resize_0/M_AXIS
  S01_AXIS cic_data_resize_1/M_AXIS
  aclk $fclk
  aresetn $f_aresetn
}

cell open-mri:user:axis_dma_rx:1.0 axis_dma_rx_0 {
  C_S_AXI_ADDR_WIDTH 16
  C_S_AXI_DATA_WIDTH 32
  C_AXIS_TDATA_WIDTH 64
} {
  aclk      $fclk
  aresetn   $f_aresetn
}

cell xilinx.com:ip:axi_datamover:5.1 axi_datamover_0 {
  c_include_mm2s            Omit
  c_include_mm2s_stsfifo    false
  c_m_axi_s2mm_data_width   64
  c_s_axis_s2mm_tdata_width 64
  c_s2mm_support_indet_btt  true
  c_enable_mm2s             0
} {
  m_axi_s2mm_aclk             $fclk
  m_axis_s2mm_cmdsts_awclk    $fclk
  m_axis_s2mm_cmdsts_aresetn  $f_aresetn
  m_axi_s2mm_aresetn          $f_aresetn
  s2mm_err                    axis_dma_rx_0/s2mm_err
  M_AXIS_S2MM_STS             axis_dma_rx_0/S_AXIS_S2MM_STS
  S_AXIS_S2MM                 axis_dma_rx_0/M_AXIS_S2MM
  S_AXIS_S2MM_CMD             axis_dma_rx_0/M_AXIS_S2MM_CMD
}
cell open-mri:user:axi_sniffer:1.0 axi_sniffer_0 {
  C_S_AXI_ADDR_WIDTH 32
  C_S_AXI_DATA_WIDTH 64
} {
  aclk      $fclk
  aresetn   $f_aresetn
  bresp     axis_dma_rx_0/axi_mm_bresp
  bvalid    axis_dma_rx_0/axi_mm_bvalid
  bready    axis_dma_rx_0/axi_mm_bready
}
set_property CONFIG.PROTOCOL AXI4 [get_bd_intf_pins /rx_0/axi_sniffer_0/S_AXI]
save_bd_design
if { [dict get $pl_param_dict mode] == "SIMPLE"} {
    cell open-mri:user:axis_acq_trigger:1.0 axis_acq_trigger_0 {
        C_S_AXI_ADDR_WIDTH 12
        C_S_AXI_DATA_WIDTH 32
        C_AXIS_TDATA_WIDTH 64
    } {
        aclk      $fclk
        aresetn   $f_aresetn
        S_AXIS    comb_0/M_AXIS
    }
    save_bd_design
    cell xilinx.com:ip:axis_data_fifo:2.0 axis_data_fifo_0 {
        TDATA_NUM_BYTES 8
        FIFO_DEPTH 16
    } {
        s_axis_aclk $fclk
        s_axis_aresetn axis_acq_trigger_0/resetn_out
        s_axis axis_acq_trigger_0/M_AXIS
        m_axis axis_dma_rx_0/S_AXIS
    }
    save_bd_design
    cell xilinx.com:ip:util_vector_logic:2.0 fifo_reset_0 {
        C_OPERATION not
        C_SIZE 1
    } {
        Op1 axis_acq_trigger_0/resetn_out
    }
    cell xilinx.com:ip:util_vector_logic:2.0 gate_out_0 {
        C_OPERATION not
        C_SIZE 1
    } {
        Res axis_dma_rx_0/gate
    }
    cell xilinx.com:ip:fifo_generator:13.2 fifo_acq_len_0 {
        Fifo_Implementation Common_Clock_Distributed_RAM
        Input_Data_Width 20
        Input_Depth 16
        Performance_Options First_Word_Fall_Through
    } {
        din   axis_acq_trigger_0/acq_len_out
        wr_en axis_acq_trigger_0/gate_out
        empty gate_out_0/Op1
        dout  axis_dma_rx_0/acq_len_in
        rd_en axis_dma_rx_0/acq_len_rd_en
        clk  $fclk
        srst fifo_reset_0/Res
    }
} else {
    connect_bd_intf_net [get_bd_intf_pins comb_0/M_AXIS] [get_bd_intf_pins axis_dma_rx_0/S_AXIS]
    connect_bd_net [get_bd_pins slice_0/Dout]  [get_bd_pins axis_dma_rx_0/gate]
}