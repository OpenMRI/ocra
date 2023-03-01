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

// Function 6
/*
	This function updates the pulse sequence in the memory with a chosen one through index
*/
void update_pulse_sequence(uint32_t seq_idx, volatile uint32_t *pulseq_memory)
{
 switch(seq_idx) {

  case 1:
    /* Setup pulse sequence 1
       FID signal acquisition
    */
    pulseq_memory[0] = 0x02;
    pulseq_memory[1] = 0x5c000000;

    pulseq_memory[2] = 0xff00;
    pulseq_memory[3] = 0x0;

    pulseq_memory[4] = 0x1;
    pulseq_memory[5] = 0x10000000;

    pulseq_memory[6] = 0x0441e9db;
    pulseq_memory[7] = 0x74000000;

    pulseq_memory[8] = 0x0;
    pulseq_memory[9] = 0x64000000;
    break;

    // end pulse sequence 1

  case 2:
    pulseq_memory[0] = 0x02;
    pulseq_memory[1] = 0x5c000000;

    pulseq_memory[2] = 0x1f;
    pulseq_memory[3] = 0x0;

    pulseq_memory[4] = 0x1;
    pulseq_memory[5] = 0x10000000;

    pulseq_memory[6] = 0x0441e9db;
    pulseq_memory[7] = 0x74000000;

    pulseq_memory[8] = 0x0;
    pulseq_memory[9] = 0x64000000;
    break;

    // End pulse sequence 2
  default:
    /* this sequence does nothing but halt immediately */
    // HALT
    // A[0]
    pulseq_memory[0] = 0x00000000;
    pulseq_memory[1] = 0x64000000;
  }
}



int main(int argc, char *argv[])
{
  int fd, i;
	void *cfg, *sts;
	volatile uint32_t *slcr, *rx_freq, *rx_rate, *seq_config, *pulseq_memory, *tx_divider;


	if((fd = open("/dev/mem", O_RDWR)) < 0) {
  	perror("open");
  	return EXIT_FAILURE;
	}


  // set up shared memory (please refer to the memory offset table)
	slcr = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0xF8000000);
	sts = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40001000);
	pulseq_memory = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40030000);
	seq_config = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40040000);



	printf("Setting FPGA clock to 143 MHz !\n"); fflush(stdout);
	/* set FPGA clock to 143 MHz */
	slcr[2] = 0xDF0D;
	slcr[92] = (slcr[92] & ~0x03F03F30) | 0x00100700;
	printf(".... Done !\n"); fflush(stdout);

	printf("Erasing pulse sequence memory !\n"); fflush(stdout);
	for(i=0; i<32; i++)
	pulseq_memory[i] = 0x0;

	// HALT the microsequencer
	seq_config[0] = 0x00;
	printf("... Done !\n"); fflush(stdout);

	while(1) {
	update_pulse_sequence(1, pulseq_memory); 
	for(i=0; i<10; i++)
	  printf("%d: %ld\n",i,pulseq_memory[i]);
	
	seq_config[0] = 0x00000007;
        usleep(1000000); // sleep 1 second
	seq_config[0] = 0x00000000;
	
	update_pulse_sequence(2, pulseq_memory); 

	seq_config[0] = 0x00000007;
        usleep(1000000); // sleep 1 second
	seq_config[0] = 0x00000000;
	}

	close(fd);
	exit(0);
}
