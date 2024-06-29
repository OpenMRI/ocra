
### ADC

create_bd_port -dir I -from 6 -to 0 adc_dat_i_0
create_bd_port -dir I -from 6 -to 0 adc_dat_i_1
create_bd_port -dir I -from 6 -to 0 adc_dat_i_2
create_bd_port -dir I -from 6 -to 0 adc_dat_i_3

create_bd_port -dir I adc_clk_0_p_i
create_bd_port -dir I adc_clk_0_n_i
create_bd_port -dir I adc_clk_1_p_i
create_bd_port -dir I adc_clk_1_n_i

create_bd_port -dir O spi_csa_o
create_bd_port -dir O spi_csb_o
create_bd_port -dir O spi_clk_o
create_bd_port -dir O spi_mosi_o

### PWM
create_bd_port -dir O -from 3 -to 0 dac_pwm_o

### XADC - Revisit this. Looks incorrect compared to RP's sdc and schematic.
#create_bd_intf_port -mode Slave -vlnv xilinx.com:interface:diff_analog_io_rtl:1.0 Vp_Vn
#create_bd_intf_port -mode Slave -vlnv xilinx.com:interface:diff_analog_io_rtl:1.0 Vaux0
#create_bd_intf_port -mode Slave -vlnv xilinx.com:interface:diff_analog_io_rtl:1.0 Vaux1
#create_bd_intf_port -mode Slave -vlnv xilinx.com:interface:diff_analog_io_rtl:1.0 Vaux9
#create_bd_intf_port -mode Slave -vlnv xilinx.com:interface:diff_analog_io_rtl:1.0 Vaux8

### Expansion connector
create_bd_port -dir IO -from 10 -to 0 exp_p_tri_io
create_bd_port -dir IO -from 10 -to 0 exp_n_tri_io

### LED
create_bd_port -dir O -from 7 -to 0 led_o

### SATA Connector
create_bd_port -dir I sata_s1_b_p
create_bd_port -dir I sata_s1_b_n
create_bd_port -dir I sata_s2_b_p
create_bd_port -dir I sata_s2_b_n
