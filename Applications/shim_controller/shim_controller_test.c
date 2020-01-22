#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <math.h>
#include <sys/mman.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define PI 3.14159265

typedef union {
  int32_t le_value;
  unsigned char b[4];
} swappable_int32_t;

typedef struct {
  float gradient_sens_x; // [mT/m/A]
  float gradient_sens_y; // [mT/m/A]
  float gradient_sens_z; // [mT/m/A]
  float gradient_sens_z2; // [?/A]
} gradient_spec_t;

typedef struct {
  float gradient_x; // [A]
  float gradient_y; // [A]
  float gradient_z; // [A]
  float gradient_z2; // [A];
} gradient_offset_t;

typedef enum {
	GRAD_ZERO_DISABLED_OUTPUT = 0,
	GRAD_ZERO_ENABLED_OUTPUT,
	GRAD_OFFSET_ENABLED_OUTPUT
} gradient_state_t;

typedef enum {
	GRAD_AXIS_X = 0,
	GRAD_AXIS_Y,
	GRAD_AXIS_Z,
	GRAD_AXIS_Z2
} gradient_axis_t;

typedef struct {
  float val;
} angle_t;


// Function 1
/* generate a gradient waveform that just changes a state 

	 events like this need a 30us gate time in the sequence

  Notes about the DAC control:
  In the present OCRA hardware configuration of the AD5781 DAC, the RBUF bit must always be set so
  that it can function. (HW config is as Figure 52 in the datasheet).

*/
void update_shim_waveform_state(volatile uint32_t *shim,gradient_state_t state, unsigned int mode)
{ 
  uint32_t i;
  int32_t ival;
  
  float fLSB = 10.0/((1<<15)-1);
  
  switch(state) {
  default:
  case GRAD_ZERO_DISABLED_OUTPUT:
    // set the DAC register to zero
    shim[0] = 0x00ffffff & (0 | 0x003f0000);
    break;
  case GRAD_ZERO_ENABLED_OUTPUT:
    shim[0] = 0x00ffffff & (0 | 0x003f0000);
    break;
  case GRAD_OFFSET_ENABLED_OUTPUT:
    ival = (int32_t)12000;
    shim[0] = 0x000f0000;
    shim[1] = 0x000f0000;
    shim[2] = 0x000f0000;
    shim[3] = 0x000f0000;
    break;
  }

  
  /*
  for (int k=1; k<500; k++) {
    // DAC A
    shim[4*k] = 0x00000000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5)+16000) & 0x0000ffff);
    // DAC B
    shim[4*k+1] = 0x00010000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5+M_PI/4.0)+16000) & 0x0000ffff);
    shim[4*k+2] = 0x00020000;
    shim[4*k+3] = 0x00030000;
  }
  */

  if (mode == 0) {
    for (int k=1; k<500; k++) {
      // DAC C => scope channel 1
      shim[4*k] = 0x00020000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5)+16000.0) & 0x0000ffff);
      // DAC A => scope channel 3
      shim[4*k+1] = 0x00000000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5+M_PI/2.0)+16000.0) & 0x0000ffff);
      // DAC E => scope channel 4
      shim[4*k+2] = 0x00040000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5+M_PI)+16000.0) & 0x0000ffff);
      // DAC G => scope channel 2
      shim[4*k+3] = 0x00060000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5+3.0*M_PI/2.0)+16000.0) & 0x0000ffff);
    }
  } else if (mode == 1) {
    for (int k=1; k<500; k++) {
      // DAC C => scope channel 1
      shim[4*k] = 0x00020000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5)+16000.0) & 0x0000ffff);
      // DAC A => scope channel 3
      shim[4*k+1] = 0x00000000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5+M_PI/2.0)+16000.0) & 0x0000ffff);
      // DAC E => scope channel 4
      shim[4*k+2] = 0x00040000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/18.5+M_PI)+16000.0) & 0x0000ffff);
      // DAC G => scope channel 2
      shim[4*k+3] = 0x00060000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/18.5+3.0*M_PI/2.0)+16000.0) & 0x0000ffff);
    }
  } else if (mode == 2) {
    for (int k=1; k<500; k++) {
      // DAC C => scope channel 1
      shim[4*k] = 0x00020000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5)+16000.0) & 0x0000ffff);
      // DAC A => scope channel 3
      shim[4*k+1] = 0x00000000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/12.5+M_PI/2.0)+16000.0) & 0x0000ffff);
      // DAC E => scope channel 4
      shim[4*k+2] = 0x00040000 + ((uint32_t)(16000.0*(float)(k % 100)/100+16000.0) & 0x0000ffff);
      // DAC G => scope channel 2
      shim[4*k+3] = 0x00060000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/60+3.0*M_PI/2.0)+16000.0) & 0x0000ffff);
    }
  } else if (mode == 3) {
    for (int k=1; k<500; k++) {
      // DAC C => scope channel 1
      shim[4*k] = 0x00020000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/25.0)+16000.0) & 0x0000ffff);
      // DAC A => scope channel 3
      shim[4*k+1] = 0x00000000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/25.0+M_PI/2.0)+16000.0) & 0x0000ffff);
      // DAC E => scope channel 4
      shim[4*k+2] = 0x00040000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/25.0+M_PI)+16000.0) & 0x0000ffff);
      // DAC G => scope channel 2
      shim[4*k+3] = 0x00060000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/25.0+3.0*M_PI/2.0)+16000.0) & 0x0000ffff);
    }
  } else if (mode == 4) {
    for (int k=1; k<2000; k++) {
      // DAC C => scope channel 1
      shim[4*k] = 0x00020000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/25.0)+16000.0) & 0x0000ffff);
      // DAC A => scope channel 3
      shim[4*k+1] = 0x00000000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/25.0+M_PI/2.0)+16000.0) & 0x0000ffff);
      // DAC E => scope channel 4
      shim[4*k+2] = 0x00040000 + ((uint32_t)(16000.0*(float)(k % 100)/100+16000.0) & 0x0000ffff);
      // DAC G => scope channel 2
      shim[4*k+3] = 0x00060000 + ((uint32_t)(16000.0*sin((float)(k)*M_PI/60+3.0*M_PI/2.0)+16000.0) & 0x0000ffff);
    }
  }
  
}

// Function 2
void clear_shim_waveforms( volatile uint32_t *shim)
{
  for (int k=0; k<16000; k++) {
    shim[k] = 0x0;
  }	
}
 

int main(int argc, char *argv[])
{
  int fd, sock_server, sock_client;
  void *cfg, *sts;
  volatile uint32_t *slcr, *rx_freq, *rx_rate, *seq_config, *pulseq_memory, *tx_divider;
  volatile uint16_t *rx_cntr, *tx_size;
  //volatile uint8_t *rx_rst, *tx_rst;
  volatile uint64_t *rx_data; 
  void *tx_data;
  float tx_freq;
  struct sockaddr_in addr;
  uint32_t command;
  int16_t pulse[32768];
  uint64_t buffer[8192];
  int size, yes = 1;
  swappable_int32_t lv,bv;
  volatile uint32_t *shim_memory;
  unsigned int mode;

  if (argc != 2) {
    fprintf(stderr,"Usage: %s mode\n The mode is an integer, check the code whats valid.\n",argv[0]);
    return -1;
  }

  // not the right conversion tool
  mode = atoi(argv[1]);
    

  if((fd = open("/dev/mem", O_RDWR)) < 0) {
    perror("open");
    return EXIT_FAILURE;
  }


  // set up shared memory (please refer to the memory offset table)
  slcr = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0xF8000000);
  cfg = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40000000);
  
  /*
    NOTE: The block RAM can only be addressed with 32 bit transactions, so gradient_memory needs to
    be of type uint32_t. The HDL would have to be changed to an 8-bit interface to support per
    byte transactions
  */
  shim_memory = mmap(NULL, 8*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40020000);
  	
  printf("Setup standard memory maps !\n"); fflush(stdout);
  
  //rx_rst = ((uint8_t *)(cfg + 0));
  tx_divider = ((uint32_t *)(cfg + 0));

  rx_freq = ((uint32_t *)(cfg + 4));
  rx_rate = ((uint32_t *)(cfg + 8));
  rx_cntr = ((uint16_t *)(sts + 0));
  
  //tx_rst = ((uint8_t *)(cfg + 1));
  tx_size = ((uint16_t *)(cfg + 12));

  printf("Setting FPGA clock to 143 MHz !\n"); fflush(stdout);
  /* set FPGA clock to 143 MHz */
  slcr[2] = 0xDF0D;
  slcr[92] = (slcr[92] & ~0x03F03F30) | 0x00100700;  
  printf(".... Done !\n"); fflush(stdout);
  *tx_divider = 0x0;

  //sleep(20);
  while(1) {
    printf(".... GO !\n"); fflush(stdout);
    update_shim_waveform_state(shim_memory,GRAD_OFFSET_ENABLED_OUTPUT,mode);
    *tx_divider = 0x1;
    sleep(1);
    *tx_divider = 0x0;
  }
  
  //update_shim_waveform_state(shim_memory,GRAD_ZERO_DISABLED_OUTPUT);
  //*tx_divider = 0x1;

  sleep(5);
  //*tx_divider = 0x0;
  return EXIT_SUCCESS;
} // End main
