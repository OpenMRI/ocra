#create_clock -period 8.000 -name adc_clk_01 [get_ports {adc_clk_i[0][1]}]
#create_clock -period 8.000 -name adc_clk_23 [get_ports {adc_clk_i[1][1]}]

#set_input_delay -clock adc_clk_01 4.000 [get_ports {adc_dat_i[0][*]}]
#set_input_delay -clock adc_clk_23 4.000 [get_ports {adc_dat_i[1][*]}]
