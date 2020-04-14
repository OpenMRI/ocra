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
} gradient_spec_t;

typedef struct {
  float gradient_x; // [A]
  float gradient_y; // [A]
  float gradient_z; // [A]
} gradient_offset_t;

typedef enum {
	GRAD_ZERO_DISABLED_OUTPUT = 0,
	GRAD_ZERO_ENABLED_OUTPUT,
	GRAD_OFFSET_ENABLED_OUTPUT
} gradient_state_t;

typedef enum {
	GRAD_AXIS_X = 0,
	GRAD_AXIS_Y,
	GRAD_AXIS_Z
} gradient_axis_t;

typedef struct {
  // int32_t val;
  float val;
} angle_t;

// TODO: add a function for matrix multiplication and rotation matrix generation

// Function 1
/* generate a gradient waveform that just changes a state 

	 events like this need a 30us gate time in the sequence
*/
void update_gradient_waveform_state(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz,gradient_state_t state, gradient_offset_t offset)
{
	int32_t vmax_val = (1<<19)-1;
	int32_t vmax_val_1v = vmax_val/10; // Assume a translation of 1A/V
 
	int32_t ramp_accum;
	uint32_t i;
	int32_t ival;
  
	float fLSB = 10.0/((1<<15)-1);
	
	switch(state) {
		default:
		case GRAD_ZERO_DISABLED_OUTPUT:
			// set the DAC register to zero
			gx[0] = 0x001fffff & (0 | 0x00100000);
			gy[0] = 0x001fffff & (0 | 0x00100000);
			gz[0] = 0x001fffff & (0 | 0x00100000);
			// disable the outputs with 2's completment coding
			// 24'b0010 0000 0000 0000 0000 0000;
			gx[1] = 0x00200000;
			gy[1] = 0x00200000;
			gz[1] = 0x00200000;
			break;
		case GRAD_ZERO_ENABLED_OUTPUT:
			gx[0] = 0x001fffff & (0 | 0x00100000);
			gy[0] = 0x001fffff & (0 | 0x00100000);
			gz[0] = 0x001fffff & (0 | 0x00100000);
			// enable the outputs with 2's completment coding
			// 24'b0010 0000 0000 0000 0000 0010;
			gx[1] = 0x00200002;
			gy[1] = 0x00200002;
			gz[1] = 0x00200002;			
			break;
		case GRAD_OFFSET_ENABLED_OUTPUT:
			ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
			gx[0] = 0x001fffff & (ival | 0x00100000);
			ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
			gy[0] = 0x001fffff & (ival | 0x00100000);
			ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
			gz[0] = 0x001fffff & (ival | 0x00100000);
			// enable the outputs with 2's completment coding
			// 24'b0010 0000 0000 0000 0000 0010;
			gx[1] = 0x00200002;
			gy[1] = 0x00200002;
			gz[1] = 0x00200002;	
			break;
	}
	for (int k=2; k<2000; k++) {
		gx[k] = 0x0;
		gy[k] = 0x0;
		gz[k] = 0x0;
	}
}

// Function 2
void clear_gradient_waveforms( volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz)
{
	for (int k=0; k<2000; k++) {
		gx[k] = 0x0;
		gy[k] = 0x0;
		gz[k] = 0x0;
	}	
}


// 2D Gradient waveforms for spin echo with rotation
void generate_gradient_waveforms_se_rot_2d(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, float PEamp, gradient_offset_t offset, float theta)
{
  // printf("Designing a gradient waveform !\n"); fflush(stdout);
  int32_t vmax_val = (1<<19)-1;
  // printf("Vmax val 10V = %d\n", vmax_val);
  int32_t vmax_val_1v = vmax_val/10;
  int32_t vmax_val_3v = vmax_val/10;
 
  int32_t ramp_accum;
  uint32_t i;
  int32_t ivalx, ivaly, ival;
  float fval; // try this for intermediate computation
  
  ramp_accum = 0;
  // volatile uint32_t *waveform;
  float offset_val = 0.0;
  float fLSB = 10.0/((1<<15)-1);
  // printf("fLSB = %g Volts\n",fLSB);
  
  // enable the gradients with the prescribed offset current
  ivalx = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ivalx | 0x00100000);
  ivaly = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ivaly | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  
  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;


  float fROamplitude = ROamp;
  float fRO_half_moment = 2.8*fROamplitude/2.0; // [ms]*Volts crazy moment
  float fROpreamplitude = fRO_half_moment/0.8;  // Volts
  // printf("fROprepamplitude = %f V\n",fROpreamplitude);
  float fROprestep = fROpreamplitude/20.0;
  float fROstep = fROamplitude/20.0;
  float fRO = 0.0;
  // float fRO = offset_val;
  // float fRO = ROamp;

  // float fPE = PEamp;
  float fPE = 0.0;
  float fPEstep = PEamp/20.0;

  // Design the X and Y gradients
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    fPE += fPEstep;
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;

    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ivalx);
    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }
  for(i=22; i<82; i++) {
     // ival = (int32_t)floor(fRO/fLSB)*16;
    ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;

    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    fPE -= fPEstep;

    // ival = (int32_t)floor(fRO/fLSB)*16;
    ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;    

    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;

    // ival = (int32_t)floor(fRO/fLSB)*16;
    ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;  

    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }
  for(i=122; i<422; i++) {
     // ival = (int32_t)floor(fRO/fLSB)*16;
    ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;  

    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);

  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
    ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;  

    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }

  // Design the Y gradient
  // prephaser 200 us rise time, 3V amplitude


  //  for(i=2; i<22; i++) {
  //   fPE += fPEstep;
  //   ival = (int32_t)floor(fPE/fLSB)*16;
  //   printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
  //   gy[i] = 0x001fffff & (ival | 0x00100000);
  // }
  // for(i=22; i<82; i++) {
  //   ival = (int32_t)floor(fPE/fLSB)*16;
  //   printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
  //   gy[i] = 0x001fffff & (ival | 0x00100000);
  // }
  // for(i=82; i<102; i++) {
  //   fPE -= fPEstep;
  //   ival = (int32_t)floor(fPE/fLSB)*16;
  //   printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
  //   gy[i] = 0x001fffff & (ival | 0x00100000);
  // }
  // for(i=102; i<442; i++) {
  //   ival = (int32_t)floor(fPE/fLSB)*16;
  //   printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
  //   gy[i] = 0x001fffff & (ival | 0x00100000);
  // }


  // for(i=2; i<22; i++) {
  //   fPE += fPEstep;
  //   ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
  //   // ival = (int32_t)floor(fPE/fLSB)*16 * sin(theta);
  //   // ival = (int32_t)floor(fPE/fLSB)*16 * sin(theta) + (int32_t)floor(fRO/fLSB)*16 * cos(theta);
  //   ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
  //   printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
  //   gy[i] = 0x001fffff & (ival | 0x00100000);
  // }
  // for(i=22; i<82; i++) {
  //   ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
  //   // ival = (int32_t)floor(fPE/fLSB)*16 * sin(theta);
  //   // ival = (int32_t)floor(fPE/fLSB)*16 * sin(theta) + (int32_t)floor(fRO/fLSB)*16 * cos(theta);
  //   ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
  //   printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
  //   gy[i] = 0x001fffff & (ival | 0x00100000);
  // }
  // for(i=82; i<102; i++) {
  //   fPE -= fPEstep;
  //   ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
  //   // ival = (int32_t)floor(fPE/fLSB)*16 * sin(theta) + (int32_t)floor(fRO/fLSB)*16 * cos(theta);
  //   // ival = (int32_t)floor(fPE/fLSB)*16 * sin(theta);
  //   ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
  //   printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
  //   gy[i] = 0x001fffff & (ival | 0x00100000);
  // }
  // for(i=102; i<442; i++) {
  //   ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
  //   // ival = (int32_t)floor(fPE/fLSB)*16 * sin(theta);
  //   // ival = (int32_t)floor(fPE/fLSB)*16 * sin(theta) + (int32_t)floor(fRO/fLSB)*16 * cos(theta);
  //   ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
  //   printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
  //   gy[i] = 0x001fffff & (ival | 0x00100000);
  // }

  // Clear the rest of the buffer
  for(int k=442; k<2000; k++)
  {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[k] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[k] = 0x001fffff & (ival | 0x00100000);

  }

  // Z shim
  for(int k=2; k<2000; k++)
  {
    ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
    gz[k] = 0x001fffff & (ival | 0x00100000);
  }

}

void generate_gradient_waveforms_se_rot(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, gradient_axis_t axis, gradient_offset_t offset, float theta)
{
  // printf("Designing a gradient waveform !\n"); fflush(stdout);
  int32_t vmax_val = (1<<19)-1;
  // printf("Vmax val 10V = %d\n", vmax_val);
  int32_t vmax_val_1v = vmax_val/10;
  int32_t vmax_val_3v = vmax_val/10;
 
  int32_t ramp_accum;
  uint32_t i;
  int32_t ival;
  float fval; // try this for intermediate computation
  
  ramp_accum = 0;
  // volatile uint32_t *waveform;
  float offset_val = 0.0;
  

  float fLSB = 10.0/((1<<15)-1);
  // printf("fLSB = %g Volts\n",fLSB);
  
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);

  // // set the DAC register to zero
  // gx[0] = 0x00100000;
  // gy[0] = 0x00100000;
  // gz[0] = 0x00100000;
  
  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;

  // // set the offset current for all 3 axis
  // for(int k=2; k<2000; k++)
  // {
  //   ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  //   gx[k] = 0x001fffff & (ival | 0x00100000);
  //   ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  //   gy[k] = 0x001fffff & (ival | 0x00100000);
  //   ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  //   gz[k] = 0x001fffff & (ival | 0x00100000);
  // }

  float fROamplitude = ROamp;
  float fRO_half_moment = 2.8*fROamplitude/2.0; // [ms]*Volts crazy moment
  float fROpreamplitude = fRO_half_moment/0.8;  // Volts
  // printf("fROprepamplitude = %f V\n",fROpreamplitude);
  float fROprestep = fROpreamplitude/20.0;
  float fROstep = fROamplitude/20.0;
  float fRO = offset_val;

  // float fPEamplitude = PEamp;
  // float fPEstep = PEamp/20.0;
  // float fPE = offset.gradient_y;
  
    // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    // ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
     // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=122; i<422; i++) {
     // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }


  
  // Design the Y gradient
  // prephaser 200 us rise time, 3V amplitude
  // Design the Y gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=122; i<422; i++) {
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
    // ival = (int32_t)floor(fRO/fLSB)*16;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }



  // clear the rest of the buffer
  for(int k=442; k<2000; k++)
  {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[k] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[k] = 0x001fffff & (ival | 0x00100000);

  }

  // Z gradient is just the z shim
  for(int k=2; k<2000; k++)
  {
    ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
    gz[k] = 0x001fffff & (ival | 0x00100000);
  }

  // // // Why doesn't this work? It just makes the red pitaya crash, even when computing fval...
  // // // set the offset current for all 3 axes
  // for(int k=2; k<2000; k++)
  // {
  //   fval = (float)(gx[k] + offset.gradient_x);
  //   printf("fval x = %f\n", fval);
  //   // ival = (int32_t)floor(fval/fLSB)*16;
  //   // printf("ival x = %d\n", ival);
  //   // gx[k] = 0x001fffff & (ival | 0x00100000);

  //   fval = (float)(gy[k] + offset.gradient_y);
  //   printf("fval y = %f\n", fval);
  //   // ival = (int32_t)floor(fval/fLSB)*16;
  //   // printf("ival y = %d\n", ival);
  //   // gy[k] = 0x001fffff & (ival | 0x00100000);

  //   ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  //   printf("ival z = %d\n", ival);
  //   // gz[k] = 0x001fffff & (ival | 0x00100000);
  // }

  // TEST FOR DEBUGGING
  // for(int k=2; k<2000; k++)
  // {
  //   ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  //   gx[k] = 0x001fffff & (ival | 0x00100000);
  //   ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  //   gy[k] = 0x001fffff & (ival | 0x00100000);
  //   ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  //   gz[k] = 0x001fffff & (ival | 0x00100000);
  // }


}



// Function 3
// just generate a projection along one dimension
void generate_gradient_waveforms_se_proj(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, gradient_axis_t axis, gradient_offset_t offset)
{
  printf("Designing a gradient waveform !\n"); fflush(stdout);
  int32_t vmax_val = (1<<19)-1;
  printf("Vmax val 10V = %d\n", vmax_val);
  int32_t vmax_val_1v = vmax_val/10;
  int32_t vmax_val_3v = vmax_val/10;
 
  int32_t ramp_accum;
  uint32_t i;
  int32_t ival;
	
  ramp_accum = 0;
  volatile uint32_t *waveform;
  float offset_val = 0.0;
  
  switch(axis) {
	case GRAD_AXIS_X:
		waveform = gx;
		offset_val = offset.gradient_x;
		break;
	case GRAD_AXIS_Y:
		waveform = gy;
		offset_val = offset.gradient_y;
		break;
	case GRAD_AXIS_Z:
		waveform = gz;
		offset_val = offset.gradient_z;
		break;
  }
  float fLSB = 10.0/((1<<15)-1);
  printf("fLSB = %g Volts\n",fLSB);
  
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  
  // set the offset current for all 3 axis
  for(int k=2; k<2000; k++)
  {
	  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
	  gx[k] = 0x001fffff & (ival | 0x00100000);
	  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
	  gy[k] = 0x001fffff & (ival | 0x00100000);
	  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
	  gz[k] = 0x001fffff & (ival | 0x00100000);
  }
  
  float fROamplitude = ROamp;
  float fRO_half_moment = 2.8*fROamplitude/2.0; // [ms]*Volts crazy moment
  float fROpreamplitude = fRO_half_moment/0.8;  // Volts
  printf("fROprepamplitude = %f V\n",fROpreamplitude);
  float fROprestep = fROpreamplitude/20.0;
  float fROstep = fROamplitude/20.0;
  float fRO = offset_val;
  // float fRO = offset.gradient_x;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    waveform[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    waveform[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    waveform[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    waveform[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=122; i<422; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    waveform[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    waveform[i] = 0x001fffff & (ival | 0x00100000);
  }
}


// Function 4
/* This function makes gradient waveforms for the original SE sequence (4), with the prephaser immediately before the readout,
   and the phase-encode during the prephaser
   
   this also still includes a state update
   The waveform will play out with a 30us delay
 */
void update_gradient_waveforms_se(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, float PEamp, gradient_offset_t offset)
{
  printf("Designing a gradient waveform !\n"); fflush(stdout);
  int32_t vmax_val = (1<<19)-1;
  printf("Vmax val 10V = %d\n", vmax_val);
  int32_t vmax_val_1v = vmax_val/10;
  int32_t vmax_val_3v = vmax_val/10;
 
  int32_t ramp_accum;
  uint32_t i;
  int32_t ival;

  ramp_accum = 0;
  
  float fLSB = 10.0/((1<<15)-1);
  printf("fLSB = %g Volts\n",fLSB);
  
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);


  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  
  float fROamplitude = ROamp;
  float fRO_half_moment = 2.8*fROamplitude/2.0; // [ms]*Volts crazy moment
  float fROpreamplitude = fRO_half_moment/0.8;  // Volts
  printf("fROprepamplitude = %f V\n",fROpreamplitude);
  float fROprestep = fROpreamplitude/20.0;
  float fROstep = fROamplitude/20.0;
  float fRO = offset.gradient_x;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    // printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=122; i<422; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  
  // Design the Y gradient
  // prephaser 200 us rise time, 3V amplitude
  float fPEamplitude = PEamp;
  float fPEstep = PEamp/20.0;
  float fPE = offset.gradient_y;
  
  for(i=2; i<22; i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    // printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    // printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    // printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<442; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    // printf("i: %d fPE = %f dec= %d\n",i,fPE,ival);
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // clear the rest of the buffer
  for(i=442; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
}


// Function 5
void update_gradient_waveforms_se3d(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, float PEamp, float PE2amp, gradient_offset_t offset)
{
  printf("Designing a gradient waveform !\n"); fflush(stdout);
  int32_t vmax_val = (1<<19)-1;
  printf("Vmax val 10V = %d\n", vmax_val);
  int32_t vmax_val_1v = vmax_val/10;
  int32_t vmax_val_3v = vmax_val/10;
 
  int32_t ramp_accum;
  uint32_t i;
  int32_t ival;

  ramp_accum = 0;
  
  float fLSB = 10.0/((1<<15)-1);
  printf("fLSB = %g Volts\n",fLSB);
  
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  
  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  
  float fROamplitude = ROamp;
  float fRO_half_moment = 2.8*fROamplitude/2.0; // [ms]*Volts crazy moment
  float fROpreamplitude = fRO_half_moment/0.8;  // Volts
  printf("fROprepamplitude = %f V\n",fROpreamplitude);
  float fROprestep = fROpreamplitude/20.0;
  float fROstep = fROamplitude/20.0;
  float fRO = offset.gradient_x;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=122; i<422; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  
  // Design the Y gradient
  // prephaser 200 us rise time, 3V amplitude
  float fPEamplitude = PEamp;
  float fPEstep = PEamp/20.0;
  float fPE = offset.gradient_y;
  
  for(i=2; i<22; i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<442; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // Design the Z gradient
  // prephaser 200 us rise time, 3V amplitude
  fPEamplitude = PE2amp;
  fPEstep = PE2amp/20.0;
  fPE = offset.gradient_z;
  
  for(i=2; i<22; i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<442; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }

  // clear the rest of the buffer
  for(i=442; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
}


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

    // JUMP vector[0] (reset vector)
  
    // J to address 10 x 8 bytes A[B]
    // A[0]
    pulseq_memory[0]  = 0x0000000B;
    pulseq_memory[1]  = 0x5C000000;
    
    // A[1] CMD1 TX GATE & TX PULSE
    pulseq_memory[2]  = 0x00000013;
    pulseq_memory[3]  = 0x00000000;
    
    // A[2] CMD2 OFF
    pulseq_memory[4]  = 0x00000002;
    pulseq_memory[5]  = 0x00000000;
    
    // A[3] CMD3 GRAD GATE
    pulseq_memory[6]  = 0x00000006;
    pulseq_memory[7]  = 0x00000000;
    
    // A[4] CMD4 RX GATE & RXPULSE & GRADGATE
    pulseq_memory[8]  = 0x00000024;
    pulseq_memory[9]  = 0x00000000;
    
    // A[5] LOOP COUNTER (NO repetitions for now)
    pulseq_memory[10]  = 0x00000001;
    pulseq_memory[11]  = 0x00000000;

    // A[6] CMD5 EVERYTHING OFF, BUT DO NOT RESERT RX FIFO
    pulseq_memory[12]  = 0x00000000;
    pulseq_memory[13]  = 0x00000000;

    // A[7] UNUSED 
    pulseq_memory[14]  = 0x00000000;
    pulseq_memory[15]  = 0x00000000;

    // A[8] UNUSED 
    pulseq_memory[16]  = 0x00000000;
    pulseq_memory[17]  = 0x00000000;
    
    // A[9] UNUSED 
    pulseq_memory[18]  = 0x00000000;
    pulseq_memory[19]  = 0x00000000;

    // A[A] UNUSED
    pulseq_memory[20]  = 0x00000000;
    pulseq_memory[21]  = 0x00000000;
    
    // LD64 [5] -> R[2]: Load Loop counter to R[2]
    // A[B] 
    pulseq_memory[22]  = 0x00000005;
    pulseq_memory[23]  = 0x10000002;
    
    // LD64 [1] -> R[3]: Load CMD1 to R[3]
    // A[C]
    pulseq_memory[24]  = 0x00000001;
    pulseq_memory[25]  = 0x10000003;

    // LD64 [2] -> R[4]: Load CMD2 to R[4]
    // A[D]
    pulseq_memory[26]  = 0x00000002;
    pulseq_memory[27]  = 0x10000004;

    // LD64 [3] -> R[5]: Load CMD3 to R[5]
    // A[E]
    pulseq_memory[28]  = 0x00000003;
    pulseq_memory[29]  = 0x10000005;

    // LD64 [4] -> R[6]: Load CMD4 to R[6]
    // A[F]
    pulseq_memory[30]  = 0x00000004;
    pulseq_memory[31]  = 0x10000006;
  
    // LD64 [6] -> R[7]: Load CMD5 to R[7]
    // A[10]
    pulseq_memory[32]  = 0x00000004;
    pulseq_memory[33]  = 0x10000007;

    // TXOFFSET 0
    // A[11]
    pulseq_memory[34]  = 0x00000000;
    pulseq_memory[35]  = 0x20000000;

    // GRADOFFSET 0
    // A[12]
    pulseq_memory[36]  = 0x00000000;
    pulseq_memory[37]  = 0x24000000;
      
    // PR R[3] and unblank for 110 us (15714 clock cycles at 7 ns)
    // Issue CMD1 
    // A[13]
    pulseq_memory[38]  = 0x00003D62;
    pulseq_memory[39]  = 0x74000300;
    
    // PR R[4] and put 0 ms wait (0 clock cycles at 7 ns)
    // Issue CMD2
    // A[14]
    pulseq_memory[40]  = 0x00000000;
    pulseq_memory[41]  = 0x74000400;

    // PR R[6] and put 500 ms wait (71428500 clock cycles at 7 ns)
    // Issue CMD4
    // A[15]
    pulseq_memory[42]  = 0x0441E994;
    pulseq_memory[43]  = 0x74000600;

    // PR R[7] and put 0 ms wait 
    // Issue CMD5
    // A[16]
    pulseq_memory[44]  = 0x00000000;
    pulseq_memory[45]  = 0x74000700;

    // DEC R[2]
    // A[17]
    pulseq_memory[46]  = 0x00000000;
    pulseq_memory[47]  = 0x04000002;
    
    // JNZ R[2] => `PC=0x11
    // A[18]
    pulseq_memory[48]  = 0x00000011;
    pulseq_memory[49]  = 0x40000002;
    
    // HALT
    // A[19]
    pulseq_memory[50] = 0x00000000;
    pulseq_memory[51] = 0x64000000;

    break;
    /* I tried omitting PR R[4], it is not making difference for now I believe*/    
    // end pulse sequence 1 
     
  case 2:
    /* Setup pulse sequence 2
       Spin echo, 1 repetition only
       Enable gradients (can be turned off)
    */

    // JUMP vector[0] (reset vector)
  
    // J to address 10 x 8 bytes A[B]
    // A[0]
    pulseq_memory[0]  = 0x0000000B;
    pulseq_memory[1]  = 0x5C000000;
    
    // A[1] CMD1 TX GATE & TX PULSE
    pulseq_memory[2]  = 0x00000013;
    pulseq_memory[3]  = 0x00000000;
    
    // A[2] CMD2 OFF
    pulseq_memory[4]  = 0x00000002;
    pulseq_memory[5]  = 0x00000000;
    
    // A[3] CMD3 GRAD GATE
    pulseq_memory[6]  = 0x00000006;
    pulseq_memory[7]  = 0x00000000;
    
    // A[4] CMD4 RX GATE & RXPULSE & GRADGATE
    pulseq_memory[8]  = 0x00000024;
    pulseq_memory[9]  = 0x00000000;
    
    // A[5] LOOP COUNTER (NO repetitions for now)
    pulseq_memory[10]  = 0x00000001;
    pulseq_memory[11]  = 0x00000000;

    // A[6] CMD5 EVERYTHING OFF, BUT DO NOT RESERT RX FIFO
    pulseq_memory[12]  = 0x00000000;
    pulseq_memory[13]  = 0x00000000;

    // A[7] UNUSED 
    pulseq_memory[14]  = 0x00000000;
    pulseq_memory[15]  = 0x00000000;

    // A[8] UNUSED 
    pulseq_memory[16]  = 0x00000000;
    pulseq_memory[17]  = 0x00000000;
    
    // A[9] UNUSED 
    pulseq_memory[18]  = 0x00000000;
    pulseq_memory[19]  = 0x00000000;

    // A[A] UNUSED
    pulseq_memory[20]  = 0x00000000;
    pulseq_memory[21]  = 0x00000000;
    
    // LD64 [5] -> R[2]: Load Loop counter to R[2]
    // A[B] 
    pulseq_memory[22]  = 0x00000005;
    pulseq_memory[23]  = 0x10000002;
    
    // LD64 [1] -> R[3]: Load CMD1 to R[3]
    // A[C]
    pulseq_memory[24]  = 0x00000001;
    pulseq_memory[25]  = 0x10000003;

    // LD64 [2] -> R[4]: Load CMD2 to R[4]
    // A[D]
    pulseq_memory[26]  = 0x00000002;
    pulseq_memory[27]  = 0x10000004;

    // LD64 [3] -> R[5]: Load CMD3 to R[5]
    // A[E]
    pulseq_memory[28]  = 0x00000003;
    pulseq_memory[29]  = 0x10000005;

    // LD64 [4] -> R[6]: Load CMD4 to R[6]
    // A[F]
    pulseq_memory[30]  = 0x00000004;
    pulseq_memory[31]  = 0x10000006;
  
    // LD64 [6] -> R[7]: Load CMD5 to R[7]
    // A[10]
    pulseq_memory[32]  = 0x00000004;
    pulseq_memory[33]  = 0x10000007;

    // TXOFFSET 0
    // A[11]
    pulseq_memory[34]  = 0x00000000;
    pulseq_memory[35]  = 0x20000000;

  	// GRADOFFSET 0
  	// A[12]
  	pulseq_memory[36]  = 0x00000000;
  	pulseq_memory[37]  = 0x24000000;
  		
    // PR R[3] and unblank for 110 us (15714 clock cycles at 7 ns)
    // Issue CMD1 
    // A[13]
    pulseq_memory[38]  = 0x00003D62;
    pulseq_memory[39]  = 0x74000300;
    
    // PR R[4] and put 5 ms wait (714285 clock cycles at 7 ns)
    // Issue CMD2
    // A[14]
    pulseq_memory[40]  = 0x000AE62D;
    pulseq_memory[41]  = 0x74000400;

    // TXOFFSET 0x64 [decimal 100]
    // CHANGE to TXOFFSET 0x1f4 (decimal 500)
    // A[15]
    pulseq_memory[42]  = 0x000001f4;
    pulseq_memory[43]  = 0x20000000;

    // PR R[3] and unblank for 260 us (37142 clock cycles at 7 ns)
    // Issue CMD1
    // A[16] 
    pulseq_memory[44]  = 0x00009116;
    pulseq_memory[45]  = 0x74000300;
    
    // PR R[4] and put 2.5 ms wait (357142 clock cycles at 7 ns)
    // Issue CMD2
    // A[17]
    //pulseq_memory[44]  = 0x00057316;
    pulseq_memory[46]  = 0x00051F62;
    pulseq_memory[47]  = 0x74000400;

    // PR R[5] and put 1 ms wait (142857 clock cycles at 7 ns)
    // Issue CMD3
    // A[18]
    pulseq_memory[48]  = 0x00022E09;
    pulseq_memory[49]  = 0x74000500;

    // PR R[6] and put 500 ms wait (71428500 clock cycles at 7 ns)
    // Issue CMD4
    // A[19]
    pulseq_memory[50]  = 0x0441E994;
    pulseq_memory[51]  = 0x74000600;

    // PR R[7] and put 0 ms wait 
    // Issue CMD5
    // A[1A]
    pulseq_memory[52]  = 0x00000000;
    pulseq_memory[53]  = 0x74000700;

    // DEC R[2]
    // A[1B]
    pulseq_memory[54]  = 0x00000000;
    pulseq_memory[55]  = 0x04000002;
    
    // JNZ R[2] => `PC=0x11
    // A[1C]
    pulseq_memory[56]  = 0x00000011;
    pulseq_memory[57]  = 0x40000002;
    
    // HALT
    // A[1D]
    pulseq_memory[58] = 0x00000000;
    pulseq_memory[59] = 0x64000000;
     
    break;
    // End pulse sequence 2

  case 3:
    /* Setup pulse sequence 3
       Gradient echo, 1 repetition only
       The interval between RF and Gradient is set to 1 clock cycles (7 ns)
    */

    // JUMP vector[0] (reset vector)
  
    // J to address 10 x 8 bytes A[B]
    // A[0]
    pulseq_memory[0]  = 0x0000000B;
    pulseq_memory[1]  = 0x5C000000;
    
    // A[1] CMD1 TX GATE & TX PULSE
    pulseq_memory[2]  = 0x00000013;
    pulseq_memory[3]  = 0x00000000;
    
    // A[2] CMD2 OFF
    pulseq_memory[4]  = 0x00000002;
    pulseq_memory[5]  = 0x00000000;
    
    // A[3] CMD3 GRAD GATE
    pulseq_memory[6]  = 0x00000006;
    pulseq_memory[7]  = 0x00000000;
    
    // A[4] CMD4 RX GATE & RXPULSE & GRADGATE
    pulseq_memory[8]  = 0x00000024;
    pulseq_memory[9]  = 0x00000000;
    
    // A[5] LOOP COUNTER (NO repetitions for now)
    pulseq_memory[10]  = 0x00000001;
    pulseq_memory[11]  = 0x00000000;

    // A[6] CMD5 EVERYTHING OFF, BUT DO NOT RESERT RX FIFO
    pulseq_memory[12]  = 0x00000000;
    pulseq_memory[13]  = 0x00000000;

    // A[7] UNUSED 
    pulseq_memory[14]  = 0x00000000;
    pulseq_memory[15]  = 0x00000000;

    // A[8] UNUSED 
    pulseq_memory[16]  = 0x00000000;
    pulseq_memory[17]  = 0x00000000;
    
    // A[9] UNUSED 
    pulseq_memory[18]  = 0x00000000;
    pulseq_memory[19]  = 0x00000000;

    // A[A] UNUSED
    pulseq_memory[20]  = 0x00000000;
    pulseq_memory[21]  = 0x00000000;
    
    // LD64 [5] -> R[2]: Load Loop counter to R[2]
    // A[B] 
    pulseq_memory[22]  = 0x00000005;
    pulseq_memory[23]  = 0x10000002;
    
    // LD64 [1] -> R[3]: Load CMD1 to R[3]
    // A[C]
    pulseq_memory[24]  = 0x00000001;
    pulseq_memory[25]  = 0x10000003;

    // LD64 [2] -> R[4]: Load CMD2 to R[4]
    // A[D]
    pulseq_memory[26]  = 0x00000002;
    pulseq_memory[27]  = 0x10000004;

    // LD64 [3] -> R[5]: Load CMD3 to R[5]
    // A[E]
    pulseq_memory[28]  = 0x00000003;
    pulseq_memory[29]  = 0x10000005;

    // LD64 [4] -> R[6]: Load CMD4 to R[6]
    // A[F]
    pulseq_memory[30]  = 0x00000004;
    pulseq_memory[31]  = 0x10000006;
  
    // LD64 [6] -> R[7]: Load CMD5 to R[7]
    // A[10]
    pulseq_memory[32]  = 0x00000004;
    pulseq_memory[33]  = 0x10000007;

    // TXOFFSET 0
    // A[11]
    pulseq_memory[34]  = 0x00000000;
    pulseq_memory[35]  = 0x20000000;

    // GRADOFFSET 0
    // A[12]
    pulseq_memory[36]  = 0x00000000;
    pulseq_memory[37]  = 0x24000000;
      
    // PR R[3] and unblank for 110 us (15714 clock cycles at 7 ns)
    // Issue CMD1 
    // A[13]
    pulseq_memory[38]  = 0x00003D62;
    pulseq_memory[39]  = 0x74000300;
    
    // PR R[4] and put 0. ms wait (1 clock cycles at 7 ns)
    // Issue CMD2
    // A[14]
    pulseq_memory[40]  = 0x00000001;
    pulseq_memory[41]  = 0x74000400;


    // PR R[5] and put 1 ms wait (142857 clock cycles at 7 ns)
    // Issue CMD3
    // A[15]
    pulseq_memory[42]  = 0x00022E09;
    pulseq_memory[43]  = 0x74000500;

    // PR R[6] and put 500 ms wait (71428500 clock cycles at 7 ns)
    // Issue CMD4
    // A[16]
    pulseq_memory[44]  = 0x0441E994;
    pulseq_memory[45]  = 0x74000600;

    // PR R[7] and put 0 ms wait 
    // Issue CMD5
    // A[17]
    pulseq_memory[46]  = 0x00000000;
    pulseq_memory[47]  = 0x74000700;

    // DEC R[2]
    // A[18]
    pulseq_memory[48]  = 0x00000000;
    pulseq_memory[49]  = 0x04000002;
    
    // JNZ R[2] => `PC=0x11
    // A[19]
    pulseq_memory[50]  = 0x00000011;
    pulseq_memory[51]  = 0x40000002;
    
    // HALT
    // A[1A]
    pulseq_memory[52] = 0x00000000;
    pulseq_memory[53] = 0x64000000;
      
    break;
    // End pulse sequence 3 
  
	// sequence 100: service sequence to set gradient state
	case 100:

		// J to address 10 x 8 bytes A[B]
		// A[0]
		pulseq_memory[0]  = 0x00000003;
		pulseq_memory[1]  = 0x5C000000;
		// A[1] CMD1 GRAD GATE
		pulseq_memory[2]  = 0x00000006;
		pulseq_memory[3]  = 0x00000000;
		// A[2] CMD2 OFF
		pulseq_memory[4]  = 0x00000002;
		pulseq_memory[5]  = 0x00000000;
		// GRADOFFSET 0
		// A[3]
		pulseq_memory[6]  = 0x00000000;
		pulseq_memory[7]  = 0x24000000;
		// LD64 [1] -> R[2]
		// A[4]
		pulseq_memory[8]  = 0x00000001;
		pulseq_memory[9]  = 0x10000002;
		// LD64 [2] -> R[3]
		// A[5]
		pulseq_memory[10]  = 0x00000002;
		pulseq_memory[11]  = 0x10000003;		
		// PR [2] CMD1 with 40 us delay
		// A[6]
		pulseq_memory[12]  = 0x00001652;
		pulseq_memory[13]  = 0x74000200;
		// PR [3] CMD2 with no delay
		// A[7]
		pulseq_memory[14]  = 0x00000000;
		pulseq_memory[15]  = 0x74000300;		
		// HALT
		// A[8]
		pulseq_memory[16] = 0x00000000;
		pulseq_memory[17] = 0x64000000;	
	  break;
    // End pulse sequence 100

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
	int fd, sock_server, sock_client;
	void *cfg, *sts;
	volatile uint32_t *slcr, *rx_freq, *rx_rate, *seq_config, *pulseq_memory, *tx_divider;
	volatile uint16_t *rx_cntr, *tx_size;
	//volatile uint8_t *rx_rst, *tx_rst;
	volatile uint64_t *rx_data; 
	void *tx_data;
	float tx_freq, angle_rad;
	struct sockaddr_in addr;
	uint32_t command;
	int16_t pulse[32768];
	uint64_t buffer[8192];
	int i, j, size, yes = 1, num_avgs;
	swappable_int32_t lv,bv;
	volatile uint32_t *gradient_memory_x;
	volatile uint32_t *gradient_memory_y;
	volatile uint32_t *gradient_memory_z;

  
  /*
  if(argc != 6) 
  {
    fprintf(stderr,"Usage: pulsed-nmr_planB frequency program\n");
    fprintf(stderr,"parameters: Freq, Func No, Goffset X, Y, Z\n");
    fprintf(stderr," Available functions:\n");
    //fprintf(stderr," 0\t Permanently enable gradient DAC\n");
    //fprintf(stderr," 1\t Basic spin-echo, 3 seconds TR\n");
    fprintf(stderr," 2\t Orthogonal projections\n");
    fprintf(stderr," 3\t 64*64 Spin-echo\n");
    //fprintf(stderr," 4\t 3D Spin-echo\n");
    //fprintf(stderr," 5\t Spin-echo old version \n");
    fprintf(stderr," 6\t Spin-echo only\n");
    fprintf(stderr," 7\t Spin-echo for shimming\n");
    return -1;
  }

	gradient_offset_t gradient_offset;
	// these offsets are in Ampere
  gradient_offset.gradient_x = atof(argv[3])/1000.0;  // 0.170
  gradient_offset.gradient_y = atof(argv[4])/1000.0;  // 0.00
  gradient_offset.gradient_z = atof(argv[5])/1000.0;  // 0.00*/

  gradient_offset_t gradient_offset;
  // these offsets are in Ampere
  gradient_offset.gradient_x =  0.120;
  gradient_offset.gradient_y =  0.045;
  gradient_offset.gradient_z = -0.092;  
  angle_t theta;
  // theta.val = 0; // by default

  
	if((fd = open("/dev/mem", O_RDWR)) < 0)
	{
	perror("open");
	return EXIT_FAILURE;
	}

	slcr = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0xF8000000);
	cfg = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40000000);
	sts = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40001000);
	rx_data = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40010000);
	tx_data = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40020000);
	// TW new stuff
	pulseq_memory = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40030000);
	seq_config = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40040000);  

	/*
	NOTE: The block RAM can only be addressed with 32 bit transactions, so gradient_memory needs to
			be of type uint32_t. The HDL would have to be changed to an 8-bit interface to support per
		byte transactions
	*/
	gradient_memory_x = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40002000);
	gradient_memory_y = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40004000);
	gradient_memory_z = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40006000);

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
  
	/* set default rx phase increment */
	//*rx_freq = (uint32_t)floor(19000000 / 125.0e6 * (1<<30) + 0.5);

	// set the NCO to 17.62 MHz
	//*rx_freq = (uint32_t)floor(17620000 / 125.0e6 * (1<<30) + 0.5);
	// printf("setting frequency to %.4f MHz\n",atoi(argv[1])/1e6f);
	// *rx_freq = (uint32_t)floor(atoi(argv[1]) / 125.0e6 * (1<<30) + 0.5);

	// set the NCO to 5 MHz
	//*rx_freq = (uint32_t)floor(5000000 / 125.0e6 * (1<<30) + 0.5);

	/* set default rx sample rate */
	*rx_rate = 250;

	/* fill tx buffer with zeros */
	memset(tx_data, 0, 65536);

	/* local oscillator for the excitation pulse */
	tx_freq = 19.0e6;
	for(i = 0; i < 32768; i++)
	{
		pulse[i] = 0;
	}
  

  uint32_t duration = atoi(argv[2]);

	// offset 0, start with 50 us lead-in
  
	//for(i = 64; i <= 128; i=i+2)
	//for(i = 64; i <= 96; i=i+2)
  for(i = 64; i <= 64+duration; i=i+2)
	{
	// pulse[i] = 7*2300; //(int16_t)floor(8000.0 * sin(i * 2.0 * M_PI * tx_freq / 125.0e6) + 0.5);
	pulse[i] = 14*2300;
  }

	// offset 100 in 32 bit space, start with 50 us lead-in
	//for(i = 264; i <= 392; i=i+2)
	//for(i = 264; i <= 296; i=i+2)
  //
  for(i = 1064; i <= 1064+duration*2; i=i+2)
	{
	// pulse[i] = 7*2300; //(int16_t)floor(8000.0 * sin(i * 2.0 * M_PI * tx_freq / 125.0e6) + 0.5);
  pulse[i] = 14*2300;
	}

	/*
	for(i = 16; i < 30; i=i+2)
	{
	pulse[i] = (int16_t)(14*1600-(i-14)*1600); //(int16_t)floor(8000.0 * sin(i * 2.0 * M_PI * tx_freq / 125.0e6) + 0.5);
	}
  
	// Make a second RF pulse at offset 50 (in 32 bit space)
	for(i=100; i < 130; i=i+2)
	{
		pulse[i] = 14*2300;
	}
	*/

	*tx_divider = 200;

	size = 32768-1;
	*tx_size = size;
	memset(tx_data, 0, 65536);
	memcpy(tx_data, pulse, 2 * size);

	//uint32_t seq_idx;= atoi(argv[2]);
  
	
  
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
    if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
      break;
    }

    // Check if frequency setting
    if ((command>>28) == 1) {
      uint32_t value = command & 0xfffffff;
      *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
      printf("Setting frequency to %.4f MHz\n",value/1e6f);
      if(value < 0 || value > 60000000) {
        printf("Frequency value out of range\n");
        continue;
      }
      continue;       
    }


    /*** Control parameters ***/
    uint32_t trig;    // Highest 4 bits of command            (trig==1)  Change center frequency
                      //                                      (trig==2)  Change gradient offset        
    uint32_t value;   // Lower 28 bits of command             2^28 = 268,435,456 enough for frequency ~15,700,000
    uint32_t value1;  // Second highest 4 bits of command     0~6: different functions
    uint32_t value2;  // Third highest 4 bits of command      sign of gradient offset   0:+, 1:-. 
    int32_t value3;   // Remain 20 bits of command            gradient offsets value  2^20 = 1,048,576
    
    // number of phase encoding
    uint32_t npe_idx, npe2_idx;
    int32_t npe, npe2; // npe and npe_list have to signed int(will go into int operations)
    int32_t npe_list[] = {32, 64, 128, 256};
    int32_t npe2_list[] = {8, 16, 32};

    // sequence type
    uint32_t seqType_idx;

    
    switch( command & 0x0000ffff ) {
    case 1: 
      /* GUI 1 */
      /********************* FID with frequency modification and shimming *********************/
      printf("*** MRI Lab *** -- FID\n");
      
      update_pulse_sequence(1, pulseq_memory);

      while(1) {
        if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
          break;
        }
        if (command == 0) break; // Stop command

        trig = command >> 28;

        if ( trig == 1 ) { // Change center frequency
          value = command & 0xfffffff;
          *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
          printf("Setting frequency to %.4f MHz\n",value/1e6f);
          if(value < 0 || value > 60000000) {
            printf("Frequency value out of range\n");
            continue;
          }          
        }

        else if ( trig == 2 ) { // Change gradient offset
          value1 = (command & 0x0fffffff) >> 24;  
          value2 = (command & 0x00ffffff) >> 20 ; 
          value3 = (int)(command & 0x000fffff);   
          if (value2)
            value3 = -value3;
          printf("%s %d %d %d\n", "Received values", value1, value2, value3);
          switch(value1) {
          case 0: 
            printf("Acquiring\n");
            break;
          case 1: 
            printf("Set gradient offsets X %d\n", value3);
            gradient_offset.gradient_x = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 2:
            printf("Set gradient offsets Y %d\n", value3);
            gradient_offset.gradient_y = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 3: 
            printf("Set gradient offsets Z %d\n", value3);
            gradient_offset.gradient_z = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 4:
            printf("Load gradient offsets%d\n");
            gradient_offset.gradient_x = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            value3 = (int)(command & 0x000fffff);
            if (value2)
              value3 = -value3;
            printf("%s %d %d %d\n", "Received values", value1, value2, value3);
            gradient_offset.gradient_y = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            value3 = (int)(command & 0x000fffff);
            if (value2)
              value3 = -value3;
            printf("%s %d %d %d\n", "Received values", value1, value2, value3);
            gradient_offset.gradient_z = (float)value3/1000.0;
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0\n");
            gradient_offset.gradient_x = 0.0;
            gradient_offset.gradient_y = 0.0;
            gradient_offset.gradient_z = 0.0;
            break;          
          default:
            printf("Acquiring\n");
            break;
          }
          printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
        } 

        else {
          printf("Socket Sending Error.\n");
        }

        // turn on gradients with offset currents
        update_gradient_waveform_state(gradient_memory_x,gradient_memory_y,gradient_memory_z,GRAD_OFFSET_ENABLED_OUTPUT,gradient_offset);
        // take spin-echoes with offset currents enabled
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
        // usleep(2000000);
      }
      break;
      /********************* End Case 1: FID with frequency modification and shimming *********************/
    
    case 2: 
      /* GUI 2 */
      /********************* Spin Echo with frequency modification and shimming *********************/
      printf("*** MRI Lab *** -- Spin Echo\n");
      
      update_pulse_sequence(2, pulseq_memory); // Spin echo

      while(1) {
        if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
          break;
        }
        if (command == 0) break; // Stop command

        trig = command >> 28;

        if ( trig == 1 ) { // Change center frequency
          value = command & 0xfffffff;
          *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
          printf("Setting frequency to %.4f MHz\n",value/1e6f);
          if(value < 0 || value > 60000000) {
            printf("Frequency value out of range\n");
            continue;
          }          
        }

        else if ( trig == 2 ) { // Change gradient offset
          value1 = (command & 0x0fffffff) >> 24;  
          value2 = (command & 0x00ffffff) >> 20 ; 
          value3 = (int)(command & 0x000fffff);   
          if (value2)
            value3 = -value3;
          printf("%s %d %d %d\n", "Received values", value1, value2, value3);
          switch(value1) {
          case 0: 
            printf("Acquiring\n");
            break;
          case 1: 
            printf("Set gradient offsets X %d\n", value3);
            gradient_offset.gradient_x = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 2:
            printf("Set gradient offsets Y %d\n", value3);
            gradient_offset.gradient_y = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 3: 
            printf("Set gradient offsets Z %d\n", value3);
            gradient_offset.gradient_z = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 4:
            printf("Load gradient offsets%d\n");
            gradient_offset.gradient_x = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            value3 = (int)(command & 0x000fffff);
            if (value2)
              value3 = -value3;
            printf("%s %d %d %d\n", "Received values", value1, value2, value3);
            gradient_offset.gradient_y = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            value3 = (int)(command & 0x000fffff);
            if (value2)
              value3 = -value3;
            printf("%s %d %d %d\n", "Received values", value1, value2, value3);
            gradient_offset.gradient_z = (float)value3/1000.0;
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0\n");
            gradient_offset.gradient_x = 0.0;
            gradient_offset.gradient_y = 0.0;
            gradient_offset.gradient_z = 0.0;
            break;          
          default:
            printf("Acquiring\n");
            break;
          }
          printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
        } 

        else {
          printf("Socket Sending Error.\n");
        }

        // turn on gradients with offset currents
        update_gradient_waveform_state(gradient_memory_x,gradient_memory_y,gradient_memory_z,GRAD_OFFSET_ENABLED_OUTPUT,gradient_offset);
        // take spin-echoes with offset currents enabled
        printf("Aquiring data\n");
        seq_config[0] = 0x00000007;
        // usleep(1000000); // sleep 1 second  
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
        // usleep(2000000);
      }
      break;
      /********************* End Case 2: Spin Echo with frequency modification and shimming *********************/


    case 3: 
      /* GUI 3 */
      /********************* 1 D Projection with frequency modification *********************/
      printf("*** MRI Lab *** -- Projection\n");

      char pAxis; // projection axis: x/y/z

      update_pulse_sequence(2, pulseq_memory); // Spin echo

      while(1) {
        if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
          break;
        }
        if (command == 0) break; // Stop command

        trig = command >> 28;

        if ( trig == 1 ) { // Change center frequency
          value = command & 0xfffffff;
          *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
          printf("Setting frequency to %.4f MHz\n",value/1e6f);
          if(value < 0 || value > 60000000) {
            printf("Frequency value out of range\n");
            continue;
          }          
        }

        else if ( trig == 2 ) { // Change projection axis/load or zero shim
          value1 = (command & 0x0fffffff) >> 24;  
          value2 = (command & 0x00ffffff) >> 20 ; 
          value3 = (int)(command & 0x000fffff);   
          if (value2)
            value3 = -value3;
          printf("%s %d %d %d\n", "Received values", value1, value2, value3);     
          switch(value1) {
          case 0: 
            printf("Acquiring\n");
            break;
          case 1:
            printf("Set projection axis to X\n");
            pAxis = 'x';
            break;
          case 2:
            printf("Set projection axis to Y\n");
            pAxis = 'y';
            break;
          case 3:
            printf("Set projection axis to Z\n");
            pAxis = 'z';
            break;
          case 4:
            printf("Load gradient offsets%d\n");
            gradient_offset.gradient_x = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20 ; 
            value3 = (int)(command & 0x000fffff);   
            if (value2)
              value3 = -value3;
            gradient_offset.gradient_y = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20 ; 
            value3 = (int)(command & 0x000fffff);   
            if (value2)
              value3 = -value3;
            gradient_offset.gradient_z = (float)value3/1000.0;
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0\n");
            gradient_offset.gradient_x = 0.0;
            gradient_offset.gradient_y = 0.0;
            gradient_offset.gradient_z = 0.0;
            break;          
          default:
            printf("Acquiring\n");
            break;
          }
          printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
        } 

        else {
          printf("Socket Sending Error.\n");
        }

        // take 1 D spin echo projection image with offset currents enabled
        switch(pAxis) {
        case 'x':
          generate_gradient_waveforms_se_proj(gradient_memory_x,gradient_memory_y,gradient_memory_z,1.0,GRAD_AXIS_X,gradient_offset);
          break;
        case 'y':
          generate_gradient_waveforms_se_proj(gradient_memory_x,gradient_memory_y,gradient_memory_z,1.0,GRAD_AXIS_Y,gradient_offset);
          break;
        case 'z':
          generate_gradient_waveforms_se_proj(gradient_memory_x,gradient_memory_y,gradient_memory_z,1.0,GRAD_AXIS_Z,gradient_offset);
          break;
        }

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
        // usleep(2000000);
        usleep(1000000);
      }
      break;
      /********************* End Case 3: 1 D Projection with frequency modification *********************/


    case 4: 
      /* GUI 4 */
      /********************* 2 D Imaging *********************/
      
      // Parameter list
      // gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24 | self.npe_idx<<4 | self.seqType_idx ))
      // self.npe_idx       0/1/2/3   32/64/128/256
      // self.seqType_idx   0/1/2     Spin Echo/Turbo Spin Echo/Gradient Echo


      printf("*** MRI Lab *** -- 2D Imaging\n");

      while(1) {
        if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
          break;
        }
        if (command == 0) break; // Stop command

        trig = command >> 28;

        if ( trig == 1 ) { // Change center frequency
          value = command & 0xfffffff;
          *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
          printf("Setting frequency to %.4f MHz\n",value/1e6f);
          if(value < 0 || value > 60000000) {
            printf("Frequency value out of range\n");
            continue;
          }          
        }

        else if ( trig == 2 ) { // Change projection axis/load or zero shim
          value1 = (command & 0x0fffffff) >> 24;  
          value2 = (command & 0x00ffffff) >> 20 ; 
          value3 = (int)(command & 0x000fffff);   
          if (value2)
            value3 = -value3;
          printf("%s %d %d %d\n", "Received values", value1, value2, value3);     
          switch(value1) {
          case 0:  // Acquire 2D image

            npe_idx = (command & 0x000000ff) >> 4;
            npe = npe_list[npe_idx];

            seqType_idx = (command & 0x0000000f);
            switch(seqType_idx) {
            case 0:
              update_pulse_sequence(2, pulseq_memory); // Spin echo
              printf("*** MRI Lab *** -- 2D Spin Echo Imaging -- npe = %d\n", npe);
              break;
            case 1:
              update_pulse_sequence(3, pulseq_memory); // Gradient echo
              printf("*** MRI Lab *** -- 2D Gradient Echo Imaging -- npe = %d\n", npe);
              break;
            case 2:
              //update_pulse_sequence(2, pulseq_memory); // Turbo Spin echo
              printf("*** MRI Lab *** -- 2D Turbo Spin Echo Imaging -- npe = %d\n", npe);
              break;
            default:
              break;
            }
            usleep(2000000); // sleep 2 second  give enough time to monitor the printout

            printf("Acquiring\n");
            printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
            // Phase encoding gradient loop
            float pe_step = 2.936/44.53/2; //[A]
            float pe = -(npe/2-1)*pe_step;
            float ro = 1.865/2;
            update_gradient_waveforms_se(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, gradient_offset);
            for(int reps=0; reps<npe; reps++) { 
              printf("TR[%d]: go!!\n",reps);
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
              pe = pe+pe_step;
              update_gradient_waveforms_se(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro, pe, gradient_offset);
              usleep(500000);
            }
            printf("*********************************************\n");
            printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
            break;
          case 4:
            printf("Load gradient offsets%d\n");
            gradient_offset.gradient_x = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20 ; 
            value3 = (int)(command & 0x000fffff);   
            if (value2)
              value3 = -value3;
            gradient_offset.gradient_y = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20 ; 
            value3 = (int)(command & 0x000fffff);   
            if (value2)
              value3 = -value3;
            gradient_offset.gradient_z = (float)value3/1000.0;
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0\n");
            gradient_offset.gradient_x = 0.0;
            gradient_offset.gradient_y = 0.0;
            gradient_offset.gradient_z = 0.0;
            break;          
          default:
            printf("Acquiring\n");
            break;
          }
          printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
        } 

        else {
          printf("Socket Sending Error.\n");
        }

      }
      break;
      /********************* End Case 4: 2 D Imaging *********************/ 

    case 5: 
      /* GUI 5 */
      /********************* 3 D Imaging *********************/
      
      // Parameter list
      // gsocket.write(struct.pack('<I', 2 << 28 | 0 << 24 | self.npe2_idx<<8 | self.npe_idx<<4 | self.seqType_idx ))
      // self.npe2_idx      0/1/2     8/16/32
      // self.npe_idx       0/1/2/3   32/64/128/256
      // self.seqType_idx   0/1/2     Spin Echo/Turbo Spin Echo/Gradient Echo

      printf("*** MRI Lab *** -- 3D Imaging\n");

      while(1) {
        if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
          break;
        }
        if (command == 0) break; // Stop command

        trig = command >> 28;

        if ( trig == 1 ) { // Change center frequency
          value = command & 0xfffffff;
          *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
          printf("Setting frequency to %.4f MHz\n",value/1e6f);
          if(value < 0 || value > 60000000) {
            printf("Frequency value out of range\n");
            continue;
          }          
        }

        else if ( trig == 2 ) { // Change projection axis/load or zero shim
          value1 = (command & 0x0fffffff) >> 24;  
          value2 = (command & 0x00ffffff) >> 20 ; 
          value3 = (int)(command & 0x000fffff);   
          if (value2)
            value3 = -value3;
          printf("%s %d %d %d\n", "Received values", value1, value2, value3);     
          switch(value1) {
          case 0:  // Acquire 3D image

            npe_idx = (command & 0x000000ff) >> 4;
            npe = npe_list[npe_idx];
            npe2_idx = (command & 0x00000fff) >> 8;
            npe2 = npe2_list[npe_idx];

            seqType_idx = (command & 0x0000000f);
            switch(seqType_idx) {
            case 0:
              update_pulse_sequence(2, pulseq_memory); // Spin echo
              printf("*** MRI Lab *** -- 3D Spin Echo Imaging -- npe = %d, npe2 = %d\n", npe, npe2);
              break;
            case 1:
              update_pulse_sequence(3, pulseq_memory); // Gradient echo
              printf("*** MRI Lab *** -- 3D Gradient Echo Imaging -- npe = %d, npe2 = %d\n", npe, npe2);
              break;
            case 2:
              //update_pulse_sequence(2, pulseq_memory); // Turbo Spin echo
              printf("*** MRI Lab *** -- 3D Turbo Spin Echo Imaging -- npe = %d, npe2 = %d\n", npe, npe2);
              break;
            default:
              break;
            }
            usleep(2000000); // sleep 2 second  give enough time to monitor the printout

            printf("Acquiring\n");
            printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
            // Phase encoding gradient loop
            float pe_step = 2.936/44.53/2; //[A]
            float pe_step2 = 2.349/44.53;  //[A]
            float pe = -(npe/2-1)*pe_step;
            float pe2 = -(npe2/2-1)*pe_step2;
            float ro = 1.865/2;

            for(int parts = 0; parts<npe2; parts++) {
              // Phase encoding gradient loop
              float pe = -63.0*pe_step;
              update_gradient_waveforms_se3d(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, pe2, gradient_offset);
              for(int reps=0; reps<npe; reps++) { 
                printf("TR[%d]: go!!\n",parts*64+reps);  
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
                pe = pe+pe_step;
                update_gradient_waveforms_se3d(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro, pe, pe2, gradient_offset);
                usleep(2000000);
              }
              pe2 = pe2+pe_step2;
            }
            printf("*********************************************\n");
            printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
            break;

          case 4:
            printf("Load gradient offsets%d\n");
            gradient_offset.gradient_x = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20 ; 
            value3 = (int)(command & 0x000fffff);   
            if (value2)
              value3 = -value3;
            gradient_offset.gradient_y = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20 ; 
            value3 = (int)(command & 0x000fffff);   
            if (value2)
              value3 = -value3;
            gradient_offset.gradient_z = (float)value3/1000.0;
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0\n");
            gradient_offset.gradient_x = 0.0;
            gradient_offset.gradient_y = 0.0;
            gradient_offset.gradient_z = 0.0;
            break;          
          default:
            printf("Acquiring\n");
            break;
          }
          printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
        } 

        else {
          printf("Socket Sending Error.\n");
        }

      }
      break;
      /********************* End Case 5: 3 D Imaging *********************/ 


      case 6: 
      /* GUI 6 */
      /********************* 1 D Projection with real-time rotations *********************/
      printf("*** MRI Lab *** -- Real-Time Rotated Projections\n");
      printf("TEST\n");

      // char pAxis; // projection axis: x/y/z

      update_pulse_sequence(2, pulseq_memory); // Spin echo
      // try gradient echo
      // update_pulse_sequence(3, pulseq_memory); // Gradient echo

      while(1) {
        if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
          break;
        }

        if (command == 0) break; // Stop command

        trig = command >> 28;
        printf("%s %d \n", "trig = ",trig);

        if ( trig == 1 ) { // Change center frequency
          value = command & 0xfffffff;
          *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
          printf("Setting frequency to %.4f MHz\n",value/1e6f);
          if(value < 0 || value > 60000000) {
            printf("Frequency value out of range\n");
            continue;
          }          
        }

        else if ( trig == 2 ) { // Change projection axis/load or zero shim
          value1 = (command & 0x0fffffff) >> 24;  
          value2 = (command & 0x00ffffff) >> 20; 
          value3 = (int)(command & 0x000fffff); 
          if (value2)
            value3 = -value3;
          printf("%s %d %d %d\n", "Received values", value1, value2, value3);     
          switch(value1) {
          case 0: 
            printf("Acquiring\n");
            break;
          case 1: 
            printf("Set gradient offsets X %d\n", value3);
            gradient_offset.gradient_x = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 2:
            printf("Set gradient offsets Y %d\n", value3);
            gradient_offset.gradient_y = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 3: 
            printf("Set gradient offsets Z %d\n", value3);
            gradient_offset.gradient_z = (float)value3/1000.0; // these offsets are in Ampere
            break;
          case 4:
            printf("Load gradient offsets%d\n");
            gradient_offset.gradient_x = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20 ; 
            value3 = (int)(command & 0x000fffff);   
            if (value2)
              value3 = -value3;
            gradient_offset.gradient_y = (float)value3/1000.0;
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20 ; 
            value3 = (int)(command & 0x000fffff);   
            if (value2)
              value3 = -value3;
            gradient_offset.gradient_z = (float)value3/1000.0;
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0\n");
            gradient_offset.gradient_x = 0.0;
            gradient_offset.gradient_y = 0.0;
            gradient_offset.gradient_z = 0.0;
            break;          
          default:
            printf("Acquiring\n");
            break;
          }
          printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 

        } 

        else if ( trig == 3 ) { // Set the angle of rotation
          angle_rad = (command & 0x00ffffff) * PI/180.0;
          theta.val = angle_rad;
          printf("%s %d \n", "Angle in degrees = ", command & 0x00ffffff);
          printf("%s %f \n", "Angle in radians = ", theta.val);

          int avg;
          for (avg = 0; avg < num_avgs; ++avg) {
            generate_gradient_waveforms_se_rot(gradient_memory_x, gradient_memory_y, gradient_memory_z, 1.0, GRAD_AXIS_X, gradient_offset, theta.val);
            // printf("Aquiring data\n");
            printf("Acquiring shot %d\n", avg);
            seq_config[0] = 0x00000007;
            // usleep(50000);
            usleep(800000); // sleep 1 second  
            // printf("Number of RX samples in FIFO: %d\n",*rx_cntr); 

            // Transfer the data to the client
            // transfer 10 * 5k = 50k samples
            for(i = 0; i < 10; ++i) {
              while(*rx_cntr < 10000) usleep(500);
              for(j = 0; j < 5000; ++j) buffer[j] = *rx_data;
              send(sock_client, buffer, 5000*8, MSG_NOSIGNAL | (i<9?MSG_MORE:0));
            } // End data transfer loop

            printf("stop !!\n");
            seq_config[0] = 0x00000000;
            // usleep(2000000);

          } // End averaging loop
        }

        else if ( trig == 4 ) { // Set the number of averages
          num_avgs = (command & 0x00ffffff); 
          printf("%s %d \n", "Number of averages = ", command & 0x00ffffff);

        }

        else if ( trig == 5 ) { // Take a rotated 2D image
          // num_avgs = (command & 0x00ffffff); 
          printf("Angle = %d\n", (command & 0x00ffffff));
          angle_rad = (command & 0x00ffffff) * PI/180.0;
          theta.val = angle_rad;


          printf("Acquiring\n");
          printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
          // // Phase encoding gradient loop
          npe = 64;
          float pe_step = 2.936/44.53/2; //[A]
          float pe = -(npe/2-1)*pe_step;
          float ro = 1.865/2;
          // printf("Pe = %f\n", pe);
          printf("Pe step  = %f\n", pe_step);
          generate_gradient_waveforms_se_rot_2d(gradient_memory_x,gradient_memory_y, gradient_memory_z, ro, pe, gradient_offset, theta.val);
          for(int reps=0; reps<npe; reps++) { 
            printf("Pe = %f\n", pe);
            printf("TR[%d]: go!!\n",reps);
            seq_config[0] = 0x00000007;
            usleep(1000000); // sleep 1 second
            // printf("Number of RX samples in FIFO: %d\n",*rx_cntr); 
            // Transfer the data to the client
            // transfer 10 * 5k = 50k samples
            for(i = 0; i < 10; ++i) {
              while(*rx_cntr < 10000) usleep(500);
              for(j = 0; j < 5000; ++j) buffer[j] = *rx_data;
              send(sock_client, buffer, 5000*8, MSG_NOSIGNAL | (i<9?MSG_MORE:0));
            }
          printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          generate_gradient_waveforms_se_rot_2d(gradient_memory_x,gradient_memory_y, gradient_memory_z, ro, pe, gradient_offset, theta.val);
          usleep(300000);
          }


          // printf("%s %d \n", "Number of averages = ", command & 0x00ffffff);

        }


        else {
          printf("Socket Sending Error.\n");
        }

        // take 1 D spin echo projection image with offset currents enabled and rotation
        // Take some number of averages
        // int num_avgs = 20;
        // int num_avgs = 20;
        // int avg;

        // for (avg = 0; avg < num_avgs; ++avg) {

        //   generate_gradient_waveforms_se_rot(gradient_memory_x, gradient_memory_y, gradient_memory_z, 1.0, GRAD_AXIS_X, gradient_offset, theta.val);

        //   // printf("Aquiring data\n");
        //   printf("Acquiring shot %d\n", avg);
        //   seq_config[0] = 0x00000007;
        //   // usleep(50000);
        //   usleep(800000); // sleep 1 second  
        //   // printf("Number of RX samples in FIFO: %d\n",*rx_cntr); 

        //   // Transfer the data to the client
        //   // transfer 10 * 5k = 50k samples
        //   for(i = 0; i < 10; ++i) {
        //     while(*rx_cntr < 10000) usleep(500);
        //     for(j = 0; j < 5000; ++j) buffer[j] = *rx_data;
        //     send(sock_client, buffer, 5000*8, MSG_NOSIGNAL | (i<9?MSG_MORE:0));
        //   } // End data transfer loop

        //   printf("stop !!\n");
        //   seq_config[0] = 0x00000000;
        //   // usleep(2000000);

        // } // End averaging loop

        // break;

      } // End while loop for real-time rotation GUI

      break;

      /********************* End Case 6: 1 D Projection with real-time rotations *********************/
    break;

    default:
      printf("case default\n");
      break;
    }

		// kill the gradients
		update_gradient_waveform_state(gradient_memory_x,gradient_memory_y,gradient_memory_z,GRAD_ZERO_DISABLED_OUTPUT,gradient_offset);
		// the gradient state sequence
		update_pulse_sequence(100, pulseq_memory);	
		printf("disabling gradients with service sequence 100\n");
		seq_config[0] = 0x00000007;
		usleep(1000000); // sleep 1 second	
		// stop the FPGA again
		printf("stop !!\n");
		seq_config[0] = 0x00000000;
		//break;


		//return EXIT_SUCCESS;
    
	} // End while loop

	// Close the socket connection
	close(sock_server);
	return EXIT_SUCCESS;
} // End main