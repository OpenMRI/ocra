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

// for debugging:
#include <inttypes.h>
//-------------------

#define PI 3.14159265

typedef union {
  int32_t le_value;
  unsigned char b[4];
} swappable_int32_t;

/*
  This function updates the pulse sequence in the memory with the uploaded sequence
*/
void update_pulse_sequence_from_upload(uint32_t *pulseq_memory_upload, volatile uint32_t *pulseq_memory)
{
  int i;
  int length = 200;
  for(i=0; i<length; i++){
    pulseq_memory[i] = pulseq_memory_upload[i];
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
  int conn_status;

  volatile uint32_t *attn_config;


  int i, j; // for loop
  uint32_t default_frequency = 20100000; // 20.10MHz
  float pi = 3.14159;


  // sequence type
  uint32_t seqType_idx; // used in GUI 3 and 5
  uint32_t pulseq_memory_upload_temp[200]; // record uploaded sequence
  unsigned char *b; // for sequence upload
  unsigned int cmd; // for sequence upload
  uint32_t mem_counter, nbytes, size_of_seq; // for sequence upload

  // signal from the client
  uint32_t trig;    // Highest 4 bits of command            (trig==1)  Change center frequency
  uint32_t value;   // Lower 28 bits of command             2^28 = 268,435,456 enough for frequency ~15,700,000
  uint32_t value1;  // Second highest 4 bits of command     0~6: different functions



  if(argc != 4) {
    fprintf(stderr,"parameters: RF duration, RF amplitude Attenuation (0-31.75dB)\n");
    fprintf(stderr,"e.g.\t./relax_server 150 32200 20.0\n");
    return -1;
  }

  if((fd = open("/dev/mem", O_RDWR)) < 0) {
    perror("open");
    return EXIT_FAILURE;
  }


  // set up shared memory (please refer to the memory offset table)
  slcr = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0xF8000000);
  cfg = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40000000);
  sts = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40001000);
  rx_data = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40010000);
  tx_data = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40020000);
  pulseq_memory = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40030000);
  seq_config = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40040000);
  attn_config = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40050000);


  // Attenuation
  float attenuation = atof(argv[3]);
  // Check if its bigger than 31.75 or some thing (later)
  if(attenuation < 0.0 || attenuation > 31.75) {
    fprintf(stderr,"Error: transmit attenuation of %g dB out of range.\n Please specify a value between 0 and 31.75 dB!\n",attenuation);
    return -1;
  }

  // convert to the bits
  unsigned int attn_bits = attenuation/0.25;

  /* set the attenuation value */
  attn_config[0] = attn_bits;

  printf("Attn register value: %g dB (bits = %d)\n",attenuation,attn_config[0]);

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

  printf("Erasing pulse sequence memory !\n"); fflush(stdout);
  for(i=0; i<32; i++)
  pulseq_memory[i] = 0x0;

  // HALT the microsequencer
  seq_config[0] = 0x00;
  printf("... Done !\n"); fflush(stdout);

  // set the NCO to 20.1 MHz
  printf("setting frequency to %.4f MHz\n",default_frequency/1e6f);
  *rx_freq = (uint32_t)floor(default_frequency / 125.0e6 * (1<<30) + 0.5);

  /* set default rx sample rate */
  *rx_rate = 250;

  /* fill tx buffer with zeros */
  memset(tx_data, 0, 65536);

  /* local oscillator for the excitation pulse */
  tx_freq = 19.0e6;  // not used
  for(i = 0; i < 32768; i++) {
    pulse[i] = 0;
  }


  /************* Design RF pulse *************/
  uint32_t duration = atoi(argv[1]);  // 64+2*duration < 2*offset_gap = 2000 -> duration<968
  uint32_t offset_gap = 1000;
  uint32_t memory_gap = 2*offset_gap;
  int32_t RF_amp; //7*2300 = 16100
  RF_amp = atoi(argv[2]);

  // this divider makes the sample duration a convenient 1us
  *tx_divider = 125;

  // RF sample duration is
  float txsample_duration_us = 1.0/125.0*(float)(*tx_divider);

  printf("Transmit sample duration is %g us\n",txsample_duration_us);

  unsigned int ntxsamples_needed = (float)(duration)/txsample_duration_us;
  printf("A %d us pulse would need %d samples !\n",duration,ntxsamples_needed);

  // RF Pulse 0: RF:90x+ offset 0
  for(i = 0; i <= 2*ntxsamples_needed; i=i+2) {
    pulse[i] = RF_amp;
  }

  // RF Pulse 1: RF:180x+ offset 1000 in 32 bit space
  // this is a hard pulse with double the duration of the hard 90
  for(i = 1*memory_gap; i <= 1*memory_gap+(2*ntxsamples_needed)*2; i=i+2) {
    pulse[i] = RF_amp;
  }

  // RF Pulse 2: RF:180y+ offset 2000 in 32 bit space
  for(i = 2*memory_gap; i <= 2*memory_gap+(2*ntxsamples_needed)*2; i=i+2) {
    pulse[i+1] = RF_amp;
  }

  // RF Pulse 3: RF:180y- offset 3000 in 32 bit space
  for(i = 3*memory_gap; i <= 3*memory_gap+(2*ntxsamples_needed)*2; i=i+2) {
    pulse[i+1] = -RF_amp;
  }

  // RF Pulse 4: RF:180x+ offset 4000 in 32 bit space
  // this is a hard 180 created by doubling the amplitude of the hard 90
  for(i = 4*memory_gap; i <= 4*memory_gap+(2*ntxsamples_needed); i=i+2) {
    pulse[i] = 2*RF_amp;
  }

  // RF Pulse 5: SINC PULSE
  for(i = 5*memory_gap; i <= 5*memory_gap+512; i=i+2) {
    j = (int)((i - (5*memory_gap+64)) / 2) - 128;
    pulse[i] = (int16_t) floor(48*RF_amp*(0.54 + 0.46*(cos((pi*j)/(2*48)))) * sin((pi*j)/(48))/(pi*j));
  }
  pulse[5*memory_gap+64+256] = RF_amp;

  // RF Pulse 6: SIN PULSE
  for(i = 6*memory_gap; i <= 6*memory_gap+512; i=i+2) {
    pulse[i] = (int16_t) floor(RF_amp * sin((pi*i)/(128)));
  }

  size = 32768-1;
  *tx_size = size;
  memset(tx_data, 0, 65536);
  memcpy(tx_data, pulse, 2 * size);

  /************* End of RF pulse *************/

  while(1) {
  	// Connect to the client
  	if((sock_server = socket(AF_INET, SOCK_STREAM, 0)) < 0) {
    	perror("socket");
    	return EXIT_FAILURE;
  	}
  	setsockopt(sock_server, SOL_SOCKET, SO_REUSEADDR, (void *)&yes , sizeof(yes));

  	/* setup listening address */
  	memset(&addr, 0, sizeof(addr));
  	addr.sin_family = AF_INET;
  	addr.sin_addr.s_addr = htonl(INADDR_ANY);
  	addr.sin_port = htons(1001);

  	if(bind(sock_server, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
    	perror("bind");
    	return EXIT_FAILURE;
  	}

  	// Start listening
  	printf("%s \n", "Listening...");
  	listen(sock_server, 1024);

    if((sock_client = accept(sock_server, NULL, NULL)) < 0) {
      perror("accept");
      return EXIT_FAILURE;
    }
    printf("%s \n", "Accepted client!");


  	while(1) {

      // Do nothing until received values
      while(1) {
        conn_status = recv(sock_client, (char *)&command, 4, MSG_WAITALL);
        if( conn_status <= 0 ) {
          // If status is <= 0 close connection and break -- listen again
          close(sock_server);
        }
        break;
      }
      printf("Status: %d \n", conn_status);
      if (conn_status <= 0) {
        break;
      }

      /*
      ---trigger statements---
        0: do nothing
        1: acquire: just print and go on (acquiring at the end of while)
        2: change freq. and continue
        3: change at and continue
        4: receive pulse sequence and continue
        5: break & continue: break current while loop and begin to listen again
        6: break all while loops
      */

      trig = command >> 28;
      printf("Trigger %lu \n", trig);

      if (trig == 0 ) {
        continue;
      }

      // Acquire when triggered
      else if (trig == 1) {
        printf("Aquiring data\n");
        seq_config[0] = 0x00000007;
        usleep(1000000); // sleep 1 second
        printf("Number of RX samples in FIFO: %d\n",*rx_cntr);
        // Transfer the data to the client
        // transfer 10 * 5k = 50k samples
        for(i = 0; i < 10; ++i) {
          while(*rx_cntr < 10000) usleep(500);
            for(j = 0; j < 5000; ++j) buffer[j] = *rx_data;
            send(sock_client, buffer, 5000*8, MSG_NOSIGNAL | (i<9?MSG_MORE:0));
        }
        printf("stop !!\n");
        seq_config[0] = 0x00000000;
        usleep(500000);
      }

      // Change center frequency
      else if (trig == 2) {

        printf("Change frequency value.\n");
        value = command & 0xfffffff;
        *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
        printf("Setting frequency to %.4f MHz\n",value/1e6f);
        if(value < 0 || value > 60000000) {
          printf("Frequency value out of range\n");
          continue;
        }
        continue;  // wait for acquire command
      }

      // Change attenuator value
      else if ( trig == 3 ) {
        printf("Change attenuator value.\n");
        unsigned int attn_value = command & 0x000007f;

        printf("Setting attenuation to %.2f dB\n", (float)(attn_value)*0.25);
        if (attn_value > 127) {
          printf("Attenuator setting out of range, clipping at 31.75 dB\n");
          attn_value = 127;
        }
        // set the attenuation value
        attn_config[0] = attn_value;
        continue;  // wait for acquire command
      }

      // receive pulse sequence from frontend
      else if( trig == 4 ) { // receive pulse sequence from frontend
        printf("Receive pulse sequence from frontend.\n");

        // seqType_idx = (int)(command & 0x0fffffff);

        printf("%s \n", "Receiving pulse sequence");
        nbytes = read(sock_client, &buffer, sizeof(buffer));
        printf("%s %d \n", "Num bytes received = ", nbytes);
        b = (unsigned char*) buffer;

        mem_counter = nbytes/4 - 1;
        for (i=nbytes-1; i>=0; i-=4) {
          cmd = (b[i]<<24) | (b[i-1]<<16)| (b[i-2] <<8) | b[i-3];
          pulseq_memory_upload_temp[mem_counter] = cmd;
          mem_counter -= 1;
        }

        mem_counter = 0;
        for (i=0; i<nbytes; i+=4) {
          printf("\tpulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);
          mem_counter += 1;
        }

        printf("%s \n", "Pulse sequence loaded");
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        continue;  // wait for acquire command
      }
    }
  }

  seq_config[0] = 0x00000007;
  usleep(1000000); // sleep 1 second
  // stop the FPGA again
  printf("stop !!\n");
  seq_config[0] = 0x00000000;

  // Close the socket connection
  close(sock_server);
  return EXIT_SUCCESS;
} // End main
