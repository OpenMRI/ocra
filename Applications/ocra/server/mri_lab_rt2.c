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

// local includes
#include "server_mmap.h"

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
  float val;
} angle_t;

// Function 1
/* generate a gradient waveform that just changes a state 

	 events like this need a 30us gate time in the sequence
*/
void update_gradient_waveform_state(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz,gradient_state_t state, gradient_offset_t offset)
{ 
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

// Function 3.1
// just generate a projection along one dimension
void generate_gradient_waveforms_se_proj(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, gradient_axis_t axis, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- projection !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
	
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
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset_val;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
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


// Function 3.2
// just generate a projection along one dimension (rotated)
void generate_gradient_waveforms_se_proj_rot(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, gradient_axis_t axis, gradient_offset_t offset, float theta)
{//generate_gradient_waveforms_se_rot
  printf("Designing a gradient waveform -- Rotated projection !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  
  float offset_val = 0.0;
  
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
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset_val;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=122; i<422; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16 * cos(theta);
    ival = ival + (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }


  // Design the Y gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22; i<82; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=122; i<422; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16 * sin(theta);
    ival = ival + (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
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
}


// Function 4.1
/* This function makes gradient waveforms for the spin echo and gradient echo sequences, 
  with the prephaser immediately before the readout, and the phase-encode during the prephaser.

   This also still includes a state update.
   The waveform will play out with a 30us delay.
 */
void update_gradient_waveforms_echo(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, float PEamp, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);
 
  uint32_t i;
  int32_t ival;
  
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
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
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

  // clear the rest of the buffer
  for(i=442; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
}

// Function 4.1.1
// gradient waveforms for the SE/GRE (rotated)
void update_gradient_waveforms_echo_rot(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, float PEamp, gradient_offset_t offset, float theta)
{//generate_gradient_waveforms_se_rot_2d
  printf("Designing a gradient waveform -- Rotated 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ivalx, ivaly, ival;
  
  float fLSB = 10.0/((1<<15)-1);
  printf("fLSB = %g Volts\n",fLSB);
  
  float offset_val = 0.0;
  // float gx_correction = 0.7;
  // float gx_correction = 1.0;
  // float gx_correction = 0.85;
  float gx_correction = 0.75;
  // float gy_correction = 0.5;
  // float gy_correction = 0.75;
  // float gy_correction = 0.85;
  // float gy_correction = 0.89;
  // float gy_correction = 0.87;
  // float gy_correction = 0.9;
  // float gy_correction = 0.91;
  float gy_correction = 0.93;

  // float gy_correction = 2.0;
  // float gx_correction = 2.0;
  // float gx_correction = 1.5;
  // float gy_correction = 2.5;
  // float gy_correction = 4.0;


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
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = 0.0;
 
  float fPE = 0.0;
  float fPEstep = PEamp/20.0;

  // Design the X and Y gradients
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    fPE += fPEstep;
    // ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta) * gy_correction;
    ivalx = (int32_t)ivalx;
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    ivaly = floor(fRO/fLSB)*16 * sin(theta) * gx_correction + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = (int32_t)ivaly;
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;

    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }
  for(i=22; i<82; i++) {
    // ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    // ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta);
    ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta) * gy_correction;
    ivalx = (int32_t)ivalx;
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    // ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    // ivaly = floor(fRO/fLSB)*16 * sin(theta) + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = floor(fRO/fLSB)*16 * sin(theta) * gx_correction + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = (int32_t)ivaly;
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;

    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }
  for(i=82; i<102; i++) {
    fRO -= fROprestep;
    fPE -= fPEstep;

    // ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    // ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta);
    ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta) * gy_correction;
    ivalx = (int32_t)ivalx;
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    // ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    // ivaly = floor(fRO/fLSB)*16 * sin(theta) + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = floor(fRO/fLSB)*16 * sin(theta) * gx_correction + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = (int32_t)ivaly;
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;    

    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }
  for(i=102; i<122; i++) {
    fRO -= fROstep;
    // ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    // ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta);
    ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta) * gy_correction;
    ivalx = (int32_t)ivalx;
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    // ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    // ivaly = floor(fRO/fLSB)*16 * sin(theta) + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = floor(fRO/fLSB)*16 * sin(theta) * gx_correction + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = (int32_t)ivaly;
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;  

    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }
  for(i=122; i<422; i++) {
    // ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    // ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta);
    ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta) * gy_correction;
    ivalx = (int32_t)ivalx;
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    // ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    // ivaly = floor(fRO/fLSB)*16 * sin(theta) + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = floor(fRO/fLSB)*16 * sin(theta) * gx_correction + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = (int32_t)ivaly;
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;  

    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);

  }
  for(i=422; i<442; i++) {
    fRO += fROstep;
    // ivalx = (int32_t)floor(fRO/fLSB)*16 * cos(theta) - (int32_t)floor(fPE/fLSB)*16 * sin(theta);
    // ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta);
    ivalx = floor(fRO/fLSB)*16 * cos(theta) - floor(fPE/fLSB)*16 * sin(theta) * gy_correction;
    ivalx = (int32_t)ivalx;
    ivalx = ivalx + (int32_t)floor(offset.gradient_x/fLSB)*16;

    // ivaly = (int32_t)floor(fRO/fLSB)*16 * sin(theta) + (int32_t)floor(fPE/fLSB)*16 * cos(theta);
    // ivaly = floor(fRO/fLSB)*16 * sin(theta) + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = floor(fRO/fLSB)*16 * sin(theta) * gx_correction + floor(fPE/fLSB)*16 * cos(theta);
    ivaly = (int32_t)ivaly;
    ivaly = ivaly + (int32_t)floor(offset.gradient_y/fLSB)*16;  

    gx[i] = 0x001fffff & (ivalx | 0x00100000);
    gy[i] = 0x001fffff & (ivaly | 0x00100000);
  }

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


// Function 4.2
// This function makes gradient waveforms for the slice selective SE or GRE sequences
void update_gradient_waveforms_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, float PEamp, float PE2amp, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- Slice-selective SE/GRE!\n"); fflush(stdout);
  
  uint32_t i;
  int32_t ival;
  
  float fLSB = 10.0/((1<<15)-1);
  printf("fLSB = %g Volts\n");
  
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
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
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

  // clear the rest of the buffer
  for(i=442; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=512; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }


  // slice-selective gradient
  int gz_offset = 1000; //  gz_offset + 
  fPEamplitude = PE2amp;
  fPEstep = PE2amp/6.0;
  fPE = offset.gradient_z;

  int delay = 6;
  int delay2 = delay/2;
  
  for(i=gz_offset + 2; i<gz_offset + 2 + delay; i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i= gz_offset + 2 + delay; i< gz_offset + 2 + delay + 40; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i= gz_offset + 2 + delay + 40; i< gz_offset + 2 + delay + 40 + delay; i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }

  fPEstep = PE2amp/3;
  for(i= gz_offset + 2 + delay + 40 + delay; i< gz_offset + 2 + delay + 40 + delay + delay2; i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }

  for(i= gz_offset + 2 + delay + 40 + delay + delay2; i< gz_offset + 2 + delay + 40 + delay + delay2 + 20; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }

  for(i = gz_offset + 2 + delay + 40 + delay + delay2 + 20; i< gz_offset + 2 + delay + 40 + delay + delay2 + 20 + delay2; i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
}


// Function 4.3
// This function makes gradient waveforms for the TSE sequence (etl = 2 only)
void update_gradient_waveforms_tse_2(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, \
                              float ROamp, float PEamp[], gradient_offset_t offset)  // ETL echo train length
{
  printf("Designing a gradient waveform -- CPMG echo train (etl = 2) !\n"); fflush(stdout);
 
  uint32_t i, k;
  int32_t ival;
  uint32_t etl = 2;
  uint32_t partition_size = 1000;
  
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
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  // Echo 1
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
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
  for(i=442; i<542; i++) { //442+660
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=542; i<1002; i++) { //442+660
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }

  // Echo 2
  for(i=1002; i<1102; i++) { //442+660
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1102; i<1122; i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1122; i<1422; i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1422; i<1442; i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1442; i<1542; i++) { //442+660
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  

  // Design the Y gradient
  // prephaser 200 us rise time, 3V amplitude
  float fPEamplitude, fPEstep;
  float fPE = offset.gradient_y;
  // Echo 1
  fPEamplitude = PEamp[0];
  fPEstep = PEamp[0]/20.0;
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
  for(i=442; i<462; i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=462; i<522; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=522; i<542; i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=542; i<1002; i++) { //442+660
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // Echo 2
  fPEamplitude = PEamp[1];
  fPEstep = PEamp[1]/20.0;
  for(i=1002; i<1022; i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1022; i<1082; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1082; i<1102; i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1102; i<1442; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1442; i<1462; i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1462; i<1522; i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1522; i<1542; i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }


  // clear the rest of the buffer
  for(i=1542; i<2048; i++) {//for(i=1542; i<2000; i++) {  // fail 4095 2049 succeed 2000 2048
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
}


// Function 4.3.1
// This function makes gradient waveforms for the general TSE (arbitraty etl, not in use now)
void update_gradient_waveforms_tse(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, \
                      float ROamp, uint32_t echo_train_length, float PEamp[], gradient_offset_t offset)  // ETL echo train length
{
  printf("Designing a gradient waveform -- CPMG echo train !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;

  uint32_t k;
  uint32_t etl = echo_train_length;
  uint32_t partition_size = 1000;
  uint32_t part_num = 0;
  
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
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  // Echo 1~4

  for (;part_num<=etl;) {
    part_num += 1;
    if (part_num == 1){ // only first gradient has the prephaser
      for(i=(part_num-1)*partition_size+2; i<(part_num-1)*partition_size+22; i++) {
        fRO += fROprestep;
        ival = (int32_t)floor(fRO/fLSB)*16;
        gx[i] = 0x001fffff & (ival | 0x00100000);
      }
      for(i=(part_num-1)*partition_size+22; i<(part_num-1)*partition_size+82; i++) {
        ival = (int32_t)floor(fRO/fLSB)*16;
        gx[i] = 0x001fffff & (ival | 0x00100000);
      }
      for(i=(part_num-1)*partition_size+82; i<(part_num-1)*partition_size+102; i++) {
        fRO -= fROprestep;
        ival = (int32_t)floor(fRO/fLSB)*16;
        gx[i] = 0x001fffff & (ival | 0x00100000);
      }
    }
    else {
      for(i=(part_num-1)*partition_size+2; i<(part_num-1)*partition_size+102; i++) {
        ival = (int32_t)floor(fRO/fLSB)*16;
        printf("i: %d fRO= %f dec= %d\n",i,fRO,ival);
        gx[i] = 0x001fffff & (ival | 0x00100000);
      }
    }

    for(i=(part_num-1)*partition_size+102; i<(part_num-1)*partition_size+122; i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+122; i<(part_num-1)*partition_size+422; i++) {
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+422; i<(part_num-1)*partition_size+442; i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+442; i<(part_num-1)*partition_size+542; i++) {
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+542; i<(part_num-1)*partition_size+1002; i++) { //442+660
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }


  part_num = 0;
  // Design the Y gradient
  // prephaser 200 us rise time, 3V amplitude
  float fPEamplitude, fPEstep;
  float fPE = offset.gradient_y;
  
    // Echo 1~4
  for (;part_num<=etl;) {
    part_num += 1;

    fPEamplitude = PEamp[part_num-1];
    fPEstep = fPEamplitude/20.0;

    for(i=(part_num-1)*partition_size+2; i<(part_num-1)*partition_size+22; i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+22; i<(part_num-1)*partition_size+82; i++) {
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+82; i<(part_num-1)*partition_size+102; i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+102; i<(part_num-1)*partition_size+442; i++) {
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+442; i<(part_num-1)*partition_size+462; i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+462; i<(part_num-1)*partition_size+522; i++) {
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+522; i<(part_num-1)*partition_size+542; i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=(part_num-1)*partition_size+542; i<(part_num-1)*partition_size+1002; i++) { //442+660
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }

  printf("Gx\n");
  for (i=0;i<(part_num-1)*partition_size+1002;i++) {
    printf("\t%f\n", gx[i]);
  }

  printf("Gy\n");
  for (i=0;i<(part_num-1)*partition_size+1002;i++) {
    printf("\t%f\n", gy[i]);
  }
  
  // clear the rest of the buffer
  for(i=part_num*partition_size+2; i<2048; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
}


// Function 4.4
// This function makes gradient waveforms for the epi sequence
void update_gradient_waveforms_epi(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, \
                                    float amp_x, float amp_y, gradient_offset_t offset, uint32_t y_grad_off)
{
  printf("Designing a gradient waveform -- EPI !\n"); fflush(stdout);
 
  uint32_t i, k;
  int32_t ival;

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
  
  float offset_x = offset.gradient_x;
  float offset_y = offset.gradient_y;
  
  float grad_x, grad_y;
  float grad_x_amp = amp_x;
  float grad_x_step = amp_x/5;
  float grad_y_amp = amp_y;
  float grad_y_step = amp_y/5;

  // ***
  // float pe_step = 2.936/44.53/2;  //* delta_ky = 800.0 * pe_step *//
  // amp_x = 800.0 * pe_step * 64.0 / 300.0;
  // amp_y = 800.0 * pe_step / 50.0;

  grad_x = offset_x;
  grad_y = offset_y;

  uint32_t interval = 50;
  uint32_t mem_offset = 0;

  for (k=0;k<32;k++){
  
    mem_offset = k*interval;

    // Design the X gradient
    for(i=2+mem_offset; i<7+mem_offset; i++) {
      if (k%2==0) {
        grad_x += grad_x_step;
      }
      else {
        grad_x -= grad_x_step;
      }
      ival = (int32_t)floor(grad_x/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=7+mem_offset; i<37+mem_offset; i++) {
      ival = (int32_t)floor(grad_x/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=37+mem_offset; i<42+mem_offset; i++) {
      if (k%2==0) {
        grad_x -= grad_x_step;
      }
      else {
        grad_x += grad_x_step;
      }
      ival = (int32_t)floor(grad_x/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=42+mem_offset; i<52+mem_offset; i++) {
      ival = (int32_t)floor(grad_x/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }

    // Design the Y gradient
    for(i=2+mem_offset; i<42+mem_offset; i++) {
      ival = (int32_t)floor(grad_y/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=42+mem_offset; i<47+mem_offset; i++) {
      grad_y += grad_y_step;
      ival = (int32_t)floor(grad_y/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=47+mem_offset; i<52+mem_offset; i++) {
      grad_y -= grad_y_step;
      ival = (int32_t)floor(grad_y/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }

  // set to baseline/offset
  for (i=1602;i<1702;i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }


  //#####  single shot 32  #####//
  // prephaser 1: 32 single shot Spin Echo
  uint32_t mem_offset2 = 1700;
  grad_x = offset_x;
  grad_y = offset_y;
  float grad_x_step2 = grad_x_step/2.0;
  float grad_y_step2 = amp_y * 50.0 * 15.0 / 200.0 /20;

  for(i=2+mem_offset2; i<7+mem_offset2; i++) {
    grad_x += grad_x_step2;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=7+mem_offset2; i<37+mem_offset2; i++) {
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=37+mem_offset2; i<42+mem_offset2; i++) {
    grad_x -= grad_x_step2;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }

  for(i=2+mem_offset2; i<22+mem_offset2; i++) {
    grad_y += grad_y_step2;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22+mem_offset2; i<42+mem_offset2; i++) {
    grad_y -= grad_y_step2;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // set to baseline/offset
  for(i=1742; i<1762; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // prephaser 2: 32 single shot Gradient Echo
  mem_offset2 = 1760;
  grad_x = offset_x;
  grad_y = offset_y;
  for(i=2+mem_offset2; i<7+mem_offset2; i++) {
    grad_x -= grad_x_step2;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=7+mem_offset2; i<37+mem_offset2; i++) {
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=37+mem_offset2; i<42+mem_offset2; i++) {
    grad_x += grad_x_step2;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }

  for(i=2+mem_offset2; i<22+mem_offset2; i++) {
    grad_y -= grad_y_step2;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22+mem_offset2; i<42+mem_offset2; i++) {
    grad_y += grad_y_step2;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // set to baseline/offset
  for(i=1802; i<1822; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  //#####  single shot 64  #####// only y prephaser needs to be changed
  // prephaser 3: 64 single shot Spin Echo
  mem_offset2 = 1820;
  grad_x = offset_x;
  grad_y = offset_y;
  float grad_x_step3 = grad_x_step/2.0;
  float grad_y_step3 = amp_y * 50.0 * 31.0 / 200.0 /20;

  for(i=2+mem_offset2; i<7+mem_offset2; i++) {
    grad_x += grad_x_step3;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=7+mem_offset2; i<37+mem_offset2; i++) {
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=37+mem_offset2; i<42+mem_offset2; i++) {
    grad_x -= grad_x_step3;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }

  for(i=2+mem_offset2; i<22+mem_offset2; i++) {
    grad_y += grad_y_step3;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22+mem_offset2; i<42+mem_offset2; i++) {
    grad_y -= grad_y_step3;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // set to baseline/offset
  for(i=1862; i<1882; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // prephaser 4: 64 single shot Gradient Echo
  mem_offset2 = 1880;
  grad_x = offset_x;
  grad_y = offset_y;
  for(i=2+mem_offset2; i<7+mem_offset2; i++) {
    grad_x -= grad_x_step3;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=7+mem_offset2; i<37+mem_offset2; i++) {
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=37+mem_offset2; i<42+mem_offset2; i++) {
    grad_x += grad_x_step3;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }

  for(i=2+mem_offset2; i<22+mem_offset2; i++) {
    grad_y -= grad_y_step3;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22+mem_offset2; i<42+mem_offset2; i++) {
    grad_y += grad_y_step3;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // set to baseline/offset
  for(i=1922; i<1942; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // prephaser 5: 64 single shot Gradient Echo with Partial K-space sampling
  mem_offset2 = 1940;
  grad_x = offset_x;
  grad_y = offset_y;
  grad_y_step3 = amp_y * 50.0 * 4.0 / 200.0 /20; // collect 4 extra lines across k center
  for(i=2+mem_offset2; i<7+mem_offset2; i++) {
    grad_x -= grad_x_step3;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=7+mem_offset2; i<37+mem_offset2; i++) {
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=37+mem_offset2; i<42+mem_offset2; i++) {
    grad_x += grad_x_step3;
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }

  for(i=2+mem_offset2; i<22+mem_offset2; i++) {
    grad_y -= grad_y_step3;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=22+mem_offset2; i<42+mem_offset2; i++) {
    grad_y += grad_y_step3;
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // set to baseline/offset
  for(i=1982; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  // turning off all the y gradient, for phase aligning
  if (y_grad_off) {
    for(i=0; i<2000; i++) {
      ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}


// Function 4.5
// This function makes gradient waveforms for the spiral sequence
void update_gradient_waveforms_spiral(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, \
                                    float lamda0, float omega0, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- spiral !\n"); fflush(stdout);
 
  uint32_t i;
  int32_t ival;

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
  
  
  float offset_x = offset.gradient_x;
  float offset_y = offset.gradient_y;
  float grad_x, grad_y;
  float t;
  float gamma_ratio = 1;//2*3.14159/267500000;
  
  // Design the X gradient
  for(i=2; i<1996; i++) {
    t = (i-2) * 10;
    grad_x = offset_x + lamda0 * omega0 * (cos(omega0 * t) - omega0 * t * sin(omega0 * t));
    ival = (int32_t)floor(grad_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  

  // Design the Y gradient
  for(i=2; i<1996; i++) {
    t = (i-2) * 10;
    grad_y = offset_y + lamda0 * omega0 * (sin(omega0 * t) + omega0 * t * cos(omega0 * t));
    ival = (int32_t)floor(grad_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }

  for(i=1996; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
}


// Function 5
void update_gradient_waveforms_echo3d(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, float ROamp, float PEamp, float PE2amp, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 3D SE/GRE!\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;

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
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;
  
  // Design the X gradient
  // prephaser 200 us rise time, 3V amplitude
  for(i=2; i<22; i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
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
    pulseq_memory[0] = 0x10; 
    pulseq_memory[1] = 0x5c000000;

    pulseq_memory[2] = 0x1; 
    pulseq_memory[3] = 0x0;

    pulseq_memory[4] = 0x0; 
    pulseq_memory[5] = 0x0;

    pulseq_memory[6] = 0x0; 
    pulseq_memory[7] = 0x0;

    pulseq_memory[8] = 0x2; 
    pulseq_memory[9] = 0x0;

    pulseq_memory[10] = 0x0; 
    pulseq_memory[11] = 0x0;

    pulseq_memory[12] = 0x13; 
    pulseq_memory[13] = 0x0;

    pulseq_memory[14] = 0x11; 
    pulseq_memory[15] = 0x0;

    pulseq_memory[16] = 0x6; 
    pulseq_memory[17] = 0x0;

    pulseq_memory[18] = 0x4; 
    pulseq_memory[19] = 0x0;

    pulseq_memory[20] = 0x24; 
    pulseq_memory[21] = 0x0;

    pulseq_memory[22] = 0x20; 
    pulseq_memory[23] = 0x0;

    pulseq_memory[24] = 0x0; 
    pulseq_memory[25] = 0x0;

    pulseq_memory[26] = 0x0; 
    pulseq_memory[27] = 0x0;

    pulseq_memory[28] = 0x0; 
    pulseq_memory[29] = 0x0;

    pulseq_memory[30] = 0x0; 
    pulseq_memory[31] = 0x0;

    pulseq_memory[32] = 0x1; 
    pulseq_memory[33] = 0x10000002;

    pulseq_memory[34] = 0x4; 
    pulseq_memory[35] = 0x10000003;

    pulseq_memory[36] = 0x5; 
    pulseq_memory[37] = 0x10000004;

    pulseq_memory[38] = 0x6; 
    pulseq_memory[39] = 0x10000005;

    pulseq_memory[40] = 0x7; 
    pulseq_memory[41] = 0x10000006;

    pulseq_memory[42] = 0x8; 
    pulseq_memory[43] = 0x10000007;

    pulseq_memory[44] = 0x9; 
    pulseq_memory[45] = 0x10000008;

    pulseq_memory[46] = 0xa; 
    pulseq_memory[47] = 0x10000009;

    pulseq_memory[48] = 0xb; 
    pulseq_memory[49] = 0x10000010;

    pulseq_memory[50] = 0x0; 
    pulseq_memory[51] = 0x0;

    pulseq_memory[52] = 0x0; 
    pulseq_memory[53] = 0x0;

    pulseq_memory[54] = 0x0; 
    pulseq_memory[55] = 0x0;

    pulseq_memory[56] = 0x0; 
    pulseq_memory[57] = 0x0;

    pulseq_memory[58] = 0x0; 
    pulseq_memory[59] = 0x20000000;

    pulseq_memory[60] = 0x0; 
    pulseq_memory[61] = 0x24000000;

    pulseq_memory[62] = 0x42f6; 
    pulseq_memory[63] = 0x74000500;

    pulseq_memory[64] = 0x1b3f724; 
    pulseq_memory[65] = 0x74000900;

    pulseq_memory[66] = 0x0; 
    pulseq_memory[67] = 0x74000400;

    pulseq_memory[68] = 0x0; 
    pulseq_memory[69] = 0x4000002;

    pulseq_memory[70] = 0x1d; 
    pulseq_memory[71] = 0x40000002;

    pulseq_memory[72] = 0x0; 
    pulseq_memory[73] = 0x64000000;
    
    break;

    // end pulse sequence 1 
     
  case 2:
    /* Setup pulse sequence 2
       Spin echo, 1 repetition only
       Enable gradients (can be turned off)
    */
    pulseq_memory[0] = 0x10; 
    pulseq_memory[1] = 0x5c000000;

    pulseq_memory[2] = 0x1; 
    pulseq_memory[3] = 0x0;

    pulseq_memory[4] = 0x0; 
    pulseq_memory[5] = 0x0;

    pulseq_memory[6] = 0x0; 
    pulseq_memory[7] = 0x0;

    pulseq_memory[8] = 0x2; 
    pulseq_memory[9] = 0x0;

    pulseq_memory[10] = 0x0; 
    pulseq_memory[11] = 0x0;

    pulseq_memory[12] = 0x13; 
    pulseq_memory[13] = 0x0;

    pulseq_memory[14] = 0x11; 
    pulseq_memory[15] = 0x0;

    pulseq_memory[16] = 0x6; 
    pulseq_memory[17] = 0x0;

    pulseq_memory[18] = 0x4; 
    pulseq_memory[19] = 0x0;

    pulseq_memory[20] = 0x24; 
    pulseq_memory[21] = 0x0;

    pulseq_memory[22] = 0x20; 
    pulseq_memory[23] = 0x0;

    pulseq_memory[24] = 0x0; 
    pulseq_memory[25] = 0x0;

    pulseq_memory[26] = 0x0; 
    pulseq_memory[27] = 0x0;

    pulseq_memory[28] = 0x0; 
    pulseq_memory[29] = 0x0;

    pulseq_memory[30] = 0x0; 
    pulseq_memory[31] = 0x0;

    pulseq_memory[32] = 0x1; 
    pulseq_memory[33] = 0x10000002;

    pulseq_memory[34] = 0x4; 
    pulseq_memory[35] = 0x10000003;

    pulseq_memory[36] = 0x5; 
    pulseq_memory[37] = 0x10000004;

    pulseq_memory[38] = 0x6; 
    pulseq_memory[39] = 0x10000005;

    pulseq_memory[40] = 0x7; 
    pulseq_memory[41] = 0x10000006;

    pulseq_memory[42] = 0x8; 
    pulseq_memory[43] = 0x10000007;

    pulseq_memory[44] = 0x9; 
    pulseq_memory[45] = 0x10000008;

    pulseq_memory[46] = 0xa; 
    pulseq_memory[47] = 0x10000009;

    pulseq_memory[48] = 0xb; 
    pulseq_memory[49] = 0x10000010;

    pulseq_memory[50] = 0x0; 
    pulseq_memory[51] = 0x0;

    pulseq_memory[52] = 0x0; 
    pulseq_memory[53] = 0x0;

    pulseq_memory[54] = 0x0; 
    pulseq_memory[55] = 0x0;

    pulseq_memory[56] = 0x0; 
    pulseq_memory[57] = 0x0;

    pulseq_memory[58] = 0x0; 
    pulseq_memory[59] = 0x20000000;

    pulseq_memory[60] = 0x0; 
    pulseq_memory[61] = 0x24000000;

    pulseq_memory[62] = 0x42f6; 
    pulseq_memory[63] = 0x74000500;

    pulseq_memory[64] = 0xa9543; 
    pulseq_memory[65] = 0x74000300;

    pulseq_memory[66] = 0x3e8;  //decimal 1000 
    pulseq_memory[67] = 0x20000000;

    pulseq_memory[68] = 0x6472; 
    pulseq_memory[69] = 0x74000500;

    pulseq_memory[70] = 0x4d6d6; 
    pulseq_memory[71] = 0x74000300;

    pulseq_memory[72] = 0x29da4; 
    pulseq_memory[73] = 0x74000700;

    pulseq_memory[74] = 0x1b3f724; 
    pulseq_memory[75] = 0x74000900;

    pulseq_memory[76] = 0x0; 
    pulseq_memory[77] = 0x74000400;

    pulseq_memory[78] = 0x0; 
    pulseq_memory[79] = 0x4000002;

    pulseq_memory[80] = 0x1d; 
    pulseq_memory[81] = 0x40000002;

    pulseq_memory[82] = 0x0; 
    pulseq_memory[83] = 0x64000000;
        
    break;

    // End pulse sequence 2

  case 3:
    /* Setup pulse sequence 3
       Gradient echo, 1 repetition only
       The interval between RF and Gradient is set to 0 clock cycles
    */
    pulseq_memory[0] = 0x10; 
    pulseq_memory[1] = 0x5c000000;

    pulseq_memory[2] = 0x1; 
    pulseq_memory[3] = 0x0;

    pulseq_memory[4] = 0x0; 
    pulseq_memory[5] = 0x0;

    pulseq_memory[6] = 0x0; 
    pulseq_memory[7] = 0x0;

    pulseq_memory[8] = 0x2; 
    pulseq_memory[9] = 0x0;

    pulseq_memory[10] = 0x0; 
    pulseq_memory[11] = 0x0;

    pulseq_memory[12] = 0x13; 
    pulseq_memory[13] = 0x0;

    pulseq_memory[14] = 0x11; 
    pulseq_memory[15] = 0x0;

    pulseq_memory[16] = 0x6; 
    pulseq_memory[17] = 0x0;

    pulseq_memory[18] = 0x4; 
    pulseq_memory[19] = 0x0;

    pulseq_memory[20] = 0x24; 
    pulseq_memory[21] = 0x0;

    pulseq_memory[22] = 0x20; 
    pulseq_memory[23] = 0x0;

    pulseq_memory[24] = 0x0; 
    pulseq_memory[25] = 0x0;

    pulseq_memory[26] = 0x0; 
    pulseq_memory[27] = 0x0;

    pulseq_memory[28] = 0x0; 
    pulseq_memory[29] = 0x0;

    pulseq_memory[30] = 0x0; 
    pulseq_memory[31] = 0x0;

    pulseq_memory[32] = 0x1; 
    pulseq_memory[33] = 0x10000002;

    pulseq_memory[34] = 0x4; 
    pulseq_memory[35] = 0x10000003;

    pulseq_memory[36] = 0x5; 
    pulseq_memory[37] = 0x10000004;

    pulseq_memory[38] = 0x6; 
    pulseq_memory[39] = 0x10000005;

    pulseq_memory[40] = 0x7; 
    pulseq_memory[41] = 0x10000006;

    pulseq_memory[42] = 0x8; 
    pulseq_memory[43] = 0x10000007;

    pulseq_memory[44] = 0x9; 
    pulseq_memory[45] = 0x10000008;

    pulseq_memory[46] = 0xa; 
    pulseq_memory[47] = 0x10000009;

    pulseq_memory[48] = 0xb; 
    pulseq_memory[49] = 0x10000010;

    pulseq_memory[50] = 0x0; 
    pulseq_memory[51] = 0x0;

    pulseq_memory[52] = 0x0; 
    pulseq_memory[53] = 0x0;

    pulseq_memory[54] = 0x0; 
    pulseq_memory[55] = 0x0;

    pulseq_memory[56] = 0x0; 
    pulseq_memory[57] = 0x0;

    pulseq_memory[58] = 0x0; 
    pulseq_memory[59] = 0x20000000;

    pulseq_memory[60] = 0x0; 
    pulseq_memory[61] = 0x24000000;

    pulseq_memory[62] = 0x42f6; 
    pulseq_memory[63] = 0x74000500;

    pulseq_memory[64] = 0x29da4; 
    pulseq_memory[65] = 0x74000700;

    pulseq_memory[66] = 0x1b3f724; 
    pulseq_memory[67] = 0x74000900;

    pulseq_memory[68] = 0x0; 
    pulseq_memory[69] = 0x74000400;

    pulseq_memory[70] = 0x0; 
    pulseq_memory[71] = 0x4000002;

    pulseq_memory[72] = 0x1d; 
    pulseq_memory[73] = 0x40000002;

    pulseq_memory[74] = 0x0; 
    pulseq_memory[75] = 0x64000000;

    break;

    // End pulse sequence 3 
  
	// sequence 100: service sequence to set gradient state
	case 100:

		// J to address 10 x 8 bytes A[B]
		// A[0]
		pulseq_memory[0] = 0x00000003;
		pulseq_memory[1] = 0x5C000000;
		// A[1] CMD1 GRAD GATE
		pulseq_memory[2] = 0x00000006;
		pulseq_memory[3] = 0x00000000;
		// A[2] CMD2 OFF
		pulseq_memory[4] = 0x00000002;
		pulseq_memory[5] = 0x00000000;
		// GRADOFFSET 0
		// A[3]
		pulseq_memory[6] = 0x00000000;
		pulseq_memory[7] = 0x24000000;
		// LD64 [1] -> R[2]
		// A[4]
		pulseq_memory[8] = 0x00000001;
		pulseq_memory[9] = 0x10000002;
		// LD64 [2] -> R[3]
		// A[5]
		pulseq_memory[10] = 0x00000002;
		pulseq_memory[11] = 0x10000003;		
		// PR [2] CMD1 with 40 us delay
		// A[6]
		pulseq_memory[12] = 0x00001652;
		pulseq_memory[13] = 0x74000200;
		// PR [3] CMD2 with no delay
		// A[7]
		pulseq_memory[14] = 0x00000000;
		pulseq_memory[15] = 0x74000300;		
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


// Function 7
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
	volatile uint32_t *gradient_memory_x;
	volatile uint32_t *gradient_memory_y;
	volatile uint32_t *gradient_memory_z;
  gradient_offset_t gradient_offset;  // these offsets are in Ampere
  gradient_offset.gradient_x =  0.120;
  gradient_offset.gradient_y =  0.045;
  gradient_offset.gradient_z = -0.092;

  int i, j; // for loop
  int is_gradient_on = 0;  // used in GUI 3, 0:FID/SE/upload seq; 1:GRE
  uint32_t default_frequency = 15670000; // 15.67MHz
  float pi = 3.14159;
  float pe, pe2, pe_step, pe_step2, ro, amp_x, amp_y; // related to gradient amplitude
  float a0, w0; // for spiral
  char pAxis; // projection axis: x/y/z

  // for real-time update rotation
  float angle_rad;
  int num_avgs;
  angle_t theta;

  // number of phase encoding and echo train length
  uint32_t npe_idx, npe2_idx, etl_idx;
  int32_t npe, npe2; // npe(2) and npe(2)_list have to signed int(will go into int operations when calculating phase encoding grads)
  int32_t npe_list[] = {4, 8, 16, 32, 64, 128, 256};
  int32_t npe2_list[] = {4, 8, 16, 32};
  uint32_t etl;
  uint32_t etl_list[] = {2, 4, 8, 16, 32};

  // sequence type
  uint32_t seqType_idx; // used in GUI 3 and 5
  uint32_t pulseq_memory_upload_temp[200]; // record uploaded sequence
  unsigned char *b; // for sequence upload
  unsigned int cmd; // for sequence upload
  uint32_t mem_counter, nbytes, size_of_seq; // for sequence upload
  
  // signal from the client
  uint32_t trig;    // Highest 4 bits of command            (trig==1)  Change center frequency
                    //                                      (trig==2)  Change gradient offset        
  uint32_t value;   // Lower 28 bits of command             2^28 = 268,435,456 enough for frequency ~15,700,000
  uint32_t value1;  // Second highest 4 bits of command     0~6: different functions
  uint32_t value2;  // Third highest 4 bits of command      sign of gradient offset   0:+, 1:-. 
  int32_t value3;   // Remain 20 bits of command            gradient offsets value  2^20 = 1,048,576
  
  

  if(argc != 3) {
    fprintf(stderr,"parameters: RF duration, RF amplitude\n");
    fprintf(stderr,"e.g.\t./mri_lab 60 32200\n");
    return -1;
  }

	if((fd = open("/dev/mem", O_RDWR)) < 0) {
  	perror("open");
  	return EXIT_FAILURE;
	}


  // set up shared memory (please refer to the memory offset table)
	slcr = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, SLCR_OFFSET);
	cfg = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, CFG_OFFSET);
	sts = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, STS_OFFSET);
	rx_data = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, RX_DATA_OFFSET);
	tx_data = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, TX_DATA_OFFSET);
	pulseq_memory = mmap(NULL, 16*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, PULSEQ_MEMORY_OFFSET);
	seq_config = mmap(NULL, sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, SEQ_CONFIG_OFFSET);  

	/*
	NOTE: The block RAM can only be addressed with 32 bit transactions, so gradient_memory needs to
			be of type uint32_t. The HDL would have to be changed to an 8-bit interface to support per
		byte transactions
	*/
	gradient_memory_x = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, GRADIENT_MEMORY_X_OFFSET);
	gradient_memory_y = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, GRADIENT_MEMORY_Y_OFFSET);
	gradient_memory_z = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, GRADIENT_MEMORY_Z_OFFSET);

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
  
	// set the NCO to 15.67 MHz
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

	// RF Pulse 0: RF:90x+ offset 0, start with 50 us lead-in
  for(i = 64; i <= 64+duration; i=i+2) {
    pulse[i] = RF_amp;
	}

	// RF Pulse 1: RF:180x+ offset 1000 in 32 bit space, start with 50 us lead-in
  for(i = 1*memory_gap+64; i <= 1*memory_gap+64+duration*2; i=i+2) {
    pulse[i] = RF_amp;
	}

  // RF Pulse 2: RF:180y+ offset 2000 in 32 bit space, start with 50 us lead-in
  for(i = 2*memory_gap+64; i <= 2*memory_gap+64+duration*2; i=i+2) {
    pulse[i+1] = RF_amp;
  }

  // RF Pulse 3: RF:180y- offset 3000 in 32 bit space, start with 50 us lead-in
  for(i = 3*memory_gap+64; i <= 3*memory_gap+64+duration*2; i=i+2) {
    pulse[i+1] = -RF_amp;
  }

  // RF Pulse 4: RF:180x+ offset 4000 in 32 bit space, start with 50 us lead-in
  for(i = 4*memory_gap+64; i <= 4*memory_gap+64+duration; i=i+2) {
    pulse[i] = 2*RF_amp;
  }

  // RF Pulse 5: SINC PULSE
  for(i = 5*memory_gap+64; i <= 5*memory_gap+576; i=i+2) {
    j = (int)((i - (5*memory_gap+64)) / 2) - 128;
    pulse[i] = (int16_t) floor(48*RF_amp*(0.54 + 0.46*(cos((pi*j)/(2*48)))) * sin((pi*j)/(48))/(pi*j)); 
  }
  pulse[5*memory_gap+64+256] = RF_amp;

  // RF Pulse 6: SIN PULSE
  for(i = 6*memory_gap+64; i <= 6*memory_gap+576; i=i+2) {
    pulse[i] = (int16_t) floor(RF_amp * sin((pi*i)/(128)));
  }

	*tx_divider = 200;

	size = 32768-1;
	*tx_size = size;
	memset(tx_data, 0, 65536);
	memcpy(tx_data, pulse, 2 * size);
  /************* End of RF pulse *************/
  
	
  
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

    // Change center frequency when client status is idle (not start yet)
    if ((command>>28) == 1) {
      value = command & 0xfffffff;
      *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
      printf("Setting frequency to %.4f MHz\n",value/1e6f);
      if(value < 0 || value > 60000000) {
        printf("Frequency value out of range\n");
        continue;
      }
      continue;       
    }

    switch( command & 0x0000ffff ) {
    case 1: 
      /* GUI 1 */
      /********************* FID with frequency modification and shimming *********************/
      printf("*** MRI Lab *** -- FID\n");
      // update_pulse_sequence(1, pulseq_memory); the old built-in seq, no longer in use
      // receive pulse sequence from the frontend
      printf("%s \n", "Receiving pulse sequence");
      if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
         break;
      }
      size_of_seq = command; // number of bytes (4*num of int_32)
      if(recv(sock_client, &buffer, size_of_seq, MSG_WAITALL) <= 0) {
         break;
      }
      b = (unsigned char*) buffer; 
      mem_counter = size_of_seq/4 - 1;
      for (i=size_of_seq-1; i>=0; i-=4) {
        cmd = (b[i]<<24) | (b[i-1]<<16)| (b[i-2] <<8) | b[i-3];
        pulseq_memory_upload_temp[mem_counter] = cmd;
        mem_counter -= 1;
      }
      mem_counter = 0;
      for (i=0; i<size_of_seq; i+=4) {
        printf("\tpulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);
        mem_counter += 1;
      }
      printf("%s \n", "Pulse sequence loaded");
      update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
      
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

        else if ( trig == 2 ) { // refresh/acquire, change gradient offset, load/zero shims
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
            printf("Load gradient offsets\n");
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
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            if (value2 == 0){
              continue;
            }
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0 %d\n");
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
        usleep(500000);
        //usleep(2000000);
      }
      break;
      /********************* End Case 1: FID with frequency modification and shimming *********************/
    
    case 2: 
      /* GUI 2 */
      /********************* Spin Echo with frequency modification and shimming *********************/
      printf("*** MRI Lab *** -- Spin Echo\n");
      //update_pulse_sequence(2, pulseq_memory); // Spin echo, the old built-in seq, no longer in use
      // receive pulse sequence from the frontend
      printf("%s \n", "Receiving pulse sequence");
      if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
         break;
      }
      size_of_seq = command; // number of bytes (4*num of int_32)
      if(recv(sock_client, &buffer, size_of_seq, MSG_WAITALL) <= 0) {
         break;
      }
      b = (unsigned char*) buffer; 
      mem_counter = size_of_seq/4 - 1;
      for (i=size_of_seq-1; i>=0; i-=4)
      {
        cmd = (b[i]<<24) | (b[i-1]<<16)| (b[i-2] <<8) | b[i-3];
        pulseq_memory_upload_temp[mem_counter] = cmd;
        mem_counter -= 1;
      }
      mem_counter = 0;
      for (i=0; i<size_of_seq; i+=4) {
        printf("\tpulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);
        mem_counter += 1;
      }
      printf("%s \n", "Pulse sequence loaded");
      update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

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

        else if ( trig == 2 ) { // Acquisition: Acquire when triggered, change gradient offset, load/zero shims
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
            printf("Load gradient offsets\n");
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
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            if (value2 == 0){
              continue;
            }
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0 %d\n");
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
        usleep(500000);
      }
      break;
      /********************* End Case 2: Spin Echo with frequency modification and shimming *********************/

    case 3: 
      /* GUI 3 */
      /********************* MRI Signals GUI with frequency modification and shimming *********************/
      printf("*** MRI Lab *** -- MRI Signals\n");

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

        else if ( trig == 2 ) { // Acquisition: Acquire when triggered, change gradient offset, load/zero shims
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
            //update_gradient_waveform_state(gradient_memory_x,gradient_memory_y,gradient_memory_z,GRAD_OFFSET_ENABLED_OUTPUT,gradient_offset);
            break;
          case 2:
            printf("Set gradient offsets Y %d\n", value3);
            gradient_offset.gradient_y = (float)value3/1000.0; // these offsets are in Ampere
            //update_gradient_waveform_state(gradient_memory_x,gradient_memory_y,gradient_memory_z,GRAD_OFFSET_ENABLED_OUTPUT,gradient_offset);
            break;
          case 3: 
            printf("Set gradient offsets Z %d\n", value3);
            gradient_offset.gradient_z = (float)value3/1000.0; // these offsets are in Ampere
            //update_gradient_waveform_state(gradient_memory_x,gradient_memory_y,gradient_memory_z,GRAD_OFFSET_ENABLED_OUTPUT,gradient_offset);
            break;
          case 4:
            printf("Load gradient offsets\n");
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
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            if (value2 == 0){
              continue;
            }
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0 %d\n");
            gradient_offset.gradient_x = 0.0;
            gradient_offset.gradient_y = 0.0;
            gradient_offset.gradient_z = 0.0;
            break;          
          default:
            printf("hahahahaha Acquiring\n");
            break;
          }
          printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
        } 

        else if( trig == 3 ) { // receive pulse sequence from frontend
          seqType_idx = (int)(command & 0x0fffffff);

          printf("%s \n", "Receiving pulse sequence");
          nbytes = read(sock_client, &buffer, sizeof(buffer));
          printf("%s %d \n", "Num bytes received = ", nbytes);
          b = (unsigned char*) buffer; 
          mem_counter = nbytes/4 - 1;
          for (i=nbytes-1; i>=0; i-=4)
          {
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

          printf("%s %d\n", "seqType_idx", seqType_idx);
          if (seqType_idx == 0 | seqType_idx == 1 | seqType_idx == 3) {
            is_gradient_on = 0;
          }
          else {
            is_gradient_on = 1;
          }
          printf("is_gradient_on: %d\n", is_gradient_on);

          update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

          continue;  // wait for acquire command
        }


        if (is_gradient_on == 0){
          // turn on gradients with offset currents (sequence with no gradient waveforms)
          printf("sequence with NO gradient waveforms\n");
          update_gradient_waveform_state(gradient_memory_x,gradient_memory_y,gradient_memory_z,GRAD_OFFSET_ENABLED_OUTPUT,gradient_offset);
        }
        else {
          // sequence with gradient waveforms
          printf("sequence with gradient waveforms\n");
          ro = 1.865/2;
          update_gradient_waveforms_echo(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , 0, gradient_offset);
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
        usleep(500000);
      }
      break;
      /********************* End Case 3: MRI Signals GUI with frequency modification and shimming *********************/


    case 4: 
      /* GUI 4 */
      /********************* 1 D Projection with frequency modification *********************/
      printf("*** MRI Lab *** -- Projection\n");

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

        else if ( trig == 2 ) { // Acquisition: Acquire when triggered, change projection axis, load/zero shims
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
            printf("Load gradient offsets\n");
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
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            if (value2 == 0){
              continue;
            }
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0 %d\n");
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

        else if ( trig == 3 ) { // Acquire all three projections

          generate_gradient_waveforms_se_proj(gradient_memory_x,gradient_memory_y,gradient_memory_z,1.0,GRAD_AXIS_X,gradient_offset);
          printf("Aquiring x data\n");
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
          //usleep(2000000);

          generate_gradient_waveforms_se_proj(gradient_memory_x,gradient_memory_y,gradient_memory_z,1.0,GRAD_AXIS_Y,gradient_offset);
          printf("Aquiring y data\n");
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
          //usleep(2000000);

          generate_gradient_waveforms_se_proj(gradient_memory_x,gradient_memory_y,gradient_memory_z,1.0,GRAD_AXIS_Z,gradient_offset);
          printf("Aquiring z data\n");
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
          continue;
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
        usleep(500000);
      }
      break;
      /********************* End Case 4: 1 D Projection with frequency modification *********************/


    case 5: 
      /* GUI 5 */
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
        printf("Command: %d \n", command);
        printf("Trig: %d \n", trig);

        if ( trig == 1 ) { // Change center frequency
          value = command & 0xfffffff;
          *rx_freq = (uint32_t)floor(value / 125.0e6 * (1<<30) + 0.5);
          printf("Setting frequency to %.4f MHz\n",value/1e6f);
          if(value < 0 || value > 60000000) {
            printf("Frequency value out of range\n");
            continue;
          }          
        }

        else if( trig == 3 ) { // Receive the uploaded sequence
          printf("%s \n", "Receiving the Uploaded the pulse sequence");

          // Note that read() returns the number of bytes read
          nbytes = read(sock_client, &buffer, sizeof(buffer));
          printf("%s %d \n", "Num bytes received = ", nbytes);
          
          // Loop over the number of bytes received
          // This makes b point to the first elt of buffer and recasts buffer to unsigned char
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

          printf("%s \n", "Pulse sequence loaded\n");
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
            etl_idx = (command & 0x00000fff) >> 8;
            etl = etl_list[etl_idx];

            npe_idx = (command & 0x000000ff) >> 4;
            npe = npe_list[npe_idx];

            seqType_idx = (command & 0x0000000f);

            switch(seqType_idx) {
            case 0: // Spin Echo
              // update_pulse_sequence(2, pulseq_memory); // Spin echo
              update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
              printf("*** MRI Lab *** -- 2D Imaging Spin Echo -- npe = %d\n", npe);
              usleep(2000000); // sleep 2 second  give enough time to monitor the printout
              printf("Acquiring\n");
              printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
              // Phase encoding gradient loop
              pe_step = 2.936/44.53/2; //[A]
              pe = -(npe/2-1)*pe_step;
              ro = 1.865/2;
              clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z);
              update_gradient_waveforms_echo(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, gradient_offset);
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
                update_gradient_waveforms_echo(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro, pe, gradient_offset);
                usleep(500000);
              }
              printf("*********************************************\n");
              break;

            case 1: // Gradient Echo
              // update_pulse_sequence(3, pulseq_memory); // Gradient echo
              update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
              printf("*** MRI Lab *** -- 2D Imaging Gradient Echo -- npe = %d\n", npe);
              usleep(2000000); // sleep 2 second  give enough time to monitor the printout
              printf("Acquiring\n");
              printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
              // Phase encoding gradient loop
              pe_step = 2.936/44.53/2; //[A]
              pe = -(npe/2-1)*pe_step;
              ro = 1.865/2;
              clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z);
              update_gradient_waveforms_echo(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, gradient_offset);
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
                update_gradient_waveforms_echo(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro, pe, gradient_offset);
                usleep(500000);
              }
              printf("*********************************************\n");
              break;

            case 2:
              update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
              printf("*** MRI Lab *** -- 2D Imaging SE (Slice-selective) -- npe = %d\n", npe);
              usleep(2000000); // sleep 2 second  give enough time to monitor the printout
              printf("Acquiring\n");
              printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
              // Phase encoding gradient loop
              pe_step = 2.936/44.53/2; //[A]
              pe = -(npe/2-1)*pe_step;
              pe2 = 2.02;
              ro = 1.865/2;
              clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z);
              update_gradient_waveforms_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, pe2, gradient_offset);
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
                update_gradient_waveforms_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, pe2, gradient_offset);
                usleep(500000);
              }
              printf("*********************************************\n");
              break;

            case 3: // Slice-selective GRE
              update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
              printf("*** MRI Lab *** -- 2D Imaging GRE (Slice-selective) -- npe = %d\n", npe);
              usleep(2000000); // sleep 2 second  give enough time to monitor the printout
              printf("Acquiring\n");
              printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
              // Phase encoding gradient loop
              pe_step = 2.936/44.53/2; //[A]
              pe = -(npe/2-1)*pe_step;
              pe2 = 2.02;
              ro = 1.865/2;
              clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z);
              update_gradient_waveforms_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, pe2, gradient_offset);
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
                update_gradient_waveforms_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, pe2, gradient_offset);
                usleep(500000);
              }
              printf("*********************************************\n");
              break;

            case 4: // TSE
              update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
              printf("*** MRI Lab *** -- 2D Imaging Uploaded Turbo Spin Echo -- npe = %d\n", npe);
              usleep(2000000); // sleep 2 second  give enough time to monitor the printout
              printf("Acquiring\n");
              printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000));
              etl = 2;
              int k = 0;
              pe_step = 2.936/44.53/2; //[A]
              pe = -(npe/2-1)*pe_step;
              ro = 1.865/2;
              float pes[] = {pe, pe+pe_step};
              clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z);
              update_gradient_waveforms_tse_2(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pes, gradient_offset);
              for(int reps=0; reps<npe/etl; reps++) { 
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
                for(k=0;k<etl;k++) {
                  pes[k] += pe_step*etl;
                }
                update_gradient_waveforms_tse_2(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pes, gradient_offset);
                usleep(500000);
              }
              printf("*********************************************\n");
              break;

            case 5: //epi
              update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
              printf("*** MRI Lab *** -- 2D Imaging Uploaded EPI Sequence\n");
              usleep(2000000); // sleep 2 second  give enough time to monitor the printout
              printf("Acquiring\n");
              printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
              pe_step = 2.936/44.53/2;  //* delta_ky = 800.0 * pe_step *//
              amp_x = 800.0 * pe_step * 64.0 / 300.0;
              amp_y = 800.0 * pe_step / 50.0;
              clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z);
              update_gradient_waveforms_epi(gradient_memory_x,gradient_memory_y,gradient_memory_z, amp_x, amp_y, gradient_offset, 0);
              printf("EPI TR[0]: go!!\n");
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
              printf("*********************************************\n");
              break;

            case 6: // epi without y gradients
              update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
              printf("*** MRI Lab *** -- 2D Imaging Uploaded EPI Sequence Disabling Grad_y\n");
              usleep(2000000); // sleep 2 second  give enough time to monitor the printout
              printf("Acquiring\n");
              printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
              pe_step = 2.936/44.53/2;  //* delta_ky = 800.0 * pe_step *//
              amp_x = 800.0 * pe_step * 64.0 / 300.0;
              amp_y = 800.0 * pe_step / 50.0;
              clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z);
              update_gradient_waveforms_epi(gradient_memory_x,gradient_memory_y,gradient_memory_z, amp_x, amp_y, gradient_offset, 1);
              printf("EPI TR[0]: go!!\n");
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
              printf("*********************************************\n");
              break;
            
            case 7: // spiral
              update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
              printf("*** MRI Lab *** -- 2D Imaging Uploaded Spiral Sequence\n");
              usleep(2000000); // sleep 2 second  give enough time to monitor the printout
              printf("Acquiring\n");
              printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
              a0 = 2.936/44.53/2 * 800 /2/3.14159;
              w0 = 0.01;
              clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z);
              update_gradient_waveforms_spiral(gradient_memory_x,gradient_memory_y,gradient_memory_z, a0, w0, gradient_offset);
              printf("SPIRAL TR[0]: go!!\n");
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
              printf("*********************************************\n");
              break;

            default:
              break;
            }
            

            printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
            break;
            
          case 4:
            printf("Load gradient offsets\n");
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
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            if (value2 == 0){
              continue;
            }
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0 %d\n");
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
      /********************* End Case 5: 2 D Imaging *********************/ 

    case 6: 
      /* GUI 6 */
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
            npe2 = npe2_list[npe2_idx];

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
            pe_step = 2.936/44.53/2; //[A]
            pe_step2 = 2.349/44.53;  //[A]
            pe = -(npe/2-1)*pe_step;
            pe2 = -(npe2/2-1)*pe_step2;
            ro = 1.865/2;
            for(int parts = 0; parts<npe2; parts++) { // Phase encoding 2 gradient loop
              update_gradient_waveforms_echo3d(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro , pe, pe2, gradient_offset);
              for(int reps=0; reps<npe; reps++) { // Phase encoding 1 gradient loop
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
                update_gradient_waveforms_echo3d(gradient_memory_x,gradient_memory_y,gradient_memory_z, ro, pe, pe2, gradient_offset);
                usleep(500000);
              }
              pe = -(npe/2-1)*pe_step;
              pe2 = pe2+pe_step2;
            }
            printf("*********************************************\n");
            printf("Gradient offsets(mA): X %d, Y %d, Z %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000)); 
            break;

          case 4:
            printf("Load gradient offsets\n");
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
            if(recv(sock_client, (char *)&command, 4, MSG_WAITALL) <= 0) {
               break;
            }
            value2 = (command & 0x00ffffff) >> 20;
            if (value2 == 0){
              continue;
            }
            break;
          case 5:
            printf("Set gradient offsets to 0 0 0 %d\n");
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
      /********************* End Case 6: 3 D Imaging *********************/

    case 7: 
      /* GUI 7 */
      /********************* 1 D Projection with real-time rotations *********************/
      printf("*** MRI Lab *** -- Real-Time Rotated Projections\n");

      update_pulse_sequence(2, pulseq_memory); // Spin echo
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
            printf("Set gradient offsets to 0 0 0 %d\n");
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
            generate_gradient_waveforms_se_proj_rot(gradient_memory_x, gradient_memory_y, gradient_memory_z, 1.0, GRAD_AXIS_X, gradient_offset, theta.val);
            // generate_gradient_waveforms_se_rot(gradient_memory_x, gradient_memory_y, gradient_memory_z, 1.0, GRAD_AXIS_X, gradient_offset, theta.val);
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
          update_gradient_waveforms_echo_rot(gradient_memory_x,gradient_memory_y, gradient_memory_z, ro, pe, gradient_offset, theta.val);
          // generate_gradient_waveforms_se_rot_2d(gradient_memory_x,gradient_memory_y, gradient_memory_z, ro, pe, gradient_offset, theta.val);
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
          update_gradient_waveforms_echo_rot(gradient_memory_x,gradient_memory_y, gradient_memory_z, ro, pe, gradient_offset, theta.val);
          // generate_gradient_waveforms_se_rot_2d(gradient_memory_x,gradient_memory_y, gradient_memory_z, ro, pe, gradient_offset, theta.val);
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

      /********************* End Case 7: 1 D Projection with real-time rotations *********************/
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
    
	} // End while loop

	// Close the socket connection
	close(sock_server);
	return EXIT_SUCCESS;
} // End main
