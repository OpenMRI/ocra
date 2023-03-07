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
#include <complex.h>

// for debugging:
#include <inttypes.h>
//-------------------

#define PI 3.14159265

// added
typedef union {
  int32_t le_value;
  unsigned char b[4];
} swappable_int32_t;

typedef struct {
  float val;
} angle_t;
//

typedef struct {
  float gradient_sens_x; // [mT/m/A]
  float gradient_sens_y; // [mT/m/A]
  float gradient_sens_z; // [mT/m/A]
  float gradient_sens_z2; // [mT/m/A]
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


/*  generate a gradient waveform that just changes a state
    events like this need a 30us gate time in the sequence

    Notes about the DAC control:
    In the present OCRA hardware configuration of the AD5781 DAC, the RBUF bit must always be set so
    that it can function. (HW config is as Figure 52 in the datasheet). */
void update_gradient_waveform_state(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz,volatile uint32_t *gz2,gradient_state_t state, gradient_offset_t offset)
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
			gz2[0] = 0x001fffff & (0 | 0x00100000);
			// disable the outputs with 2's completment coding
			// 24'b0010 0000 0000 0000 0000 1110;
			gx[1] = 0x0020000e;
			gy[1] = 0x0020000e;
			gz[1] = 0x0020000e;
			gz2[1] = 0x0020000e;
			break;
		case GRAD_ZERO_ENABLED_OUTPUT:
			gx[0] = 0x001fffff & (0 | 0x00100000);
			gy[0] = 0x001fffff & (0 | 0x00100000);
			gz[0] = 0x001fffff & (0 | 0x00100000);
			gz2[0] = 0x001fffff & (0 | 0x00100000);
			// enable the outputs with 2's completment coding
			// 24'b0010 0000 0000 0000 0000 0010;
			gx[1] = 0x00200002;
			gy[1] = 0x00200002;
			gz[1] = 0x00200002;
			gz2[1] = 0x00200002;
			break;
		case GRAD_OFFSET_ENABLED_OUTPUT:
			ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
			gx[0] = 0x001fffff & (ival | 0x00100000);
			ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
			gy[0] = 0x001fffff & (ival | 0x00100000);
			ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
			gz[0] = 0x001fffff & (ival | 0x00100000);
			ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
			gz2[0] = 0x001fffff & (ival | 0x00100000);
			// enable the outputs with 2's completment coding
			// 24'b0010 0000 0000 0000 0000 0010;
			gx[1] = 0x00200002;
			gy[1] = 0x00200002;
			gz[1] = 0x00200002;
			gz2[1] = 0x00200002;
			break;
	}
	for (int k=2; k<2000; k++) {
    // do nothing. DAC will hold Value from before
		gx[k] = 0x0;
		gy[k] = 0x0;
		gz[k] = 0x0;
		gz2[k] = 0x0;
	}
}

// Clear the gradient waveforms
void clear_gradient_waveforms( volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2)
{
	for (int k=0; k<2000; k++) {
		gx[k] = 0x0;
		gy[k] = 0x0;
		gz[k] = 0x0;
		gz2[k] = 0x0;
	}
}

// Function 4.1
/* This function makes gradient waveforms for the spin echo and gradient echo sequences,
  with the prephaser immediately before the readout, and the phase-encode during the prephaser.

   This also still includes a state update.
   The waveform will play out with a 30us delay.
 */
 
 /*
void update_gradient_waveforms_old(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float SLamp, float nPE, float PEstep, float SPEamp, int reps, float Diffamp, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay; // delay has to be < to 1550 in total ?!

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);

  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float signum = 1;
   
  if (fPEamplitude < 0){
    signum = -1;
  }
  else {
    signum = 1;
  }
   
  float fPETSEstep = nPE/2 * PEstep/20 * signum;
  float fPETSE = 0;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSL = offset.gradient_z;
   
  float fSPEamplitude = SPEamp;
  float fSPEstep = fSPEamplitude/20.0;
  float fSPE = offset.gradient_z;
   
  float fPEEPIBstep = 4*nPE/2*PEstep/20-PEstep/2/20-reps*4*PEstep/20;
  float fPEEPIB = offset.gradient_y;
  float fPEEPIstep = 4*PEstep/20;
  float fPEEPI = offset.gradient_y;
   
  float fDiffamplitude = Diffamp;
  float fDiffstep = fDiffamplitude/20.0;
  float fDiffx = offset.gradient_x;
  float fDiffy = offset.gradient_y;
  float fDiffz = offset.gradient_z;

  //printf("PE amplitude = %d \n", fPEamplitude);

  // Set waveform base value
  for(i=2; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
    gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
  
  delay = 2;

  // Design the phase and readout gradients, Phase gradient is in readoutprephaser
  // prephaser 200 us rise time
   
  for(i=delay; i<(delay+20); i++) {
    fRO -= fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);

    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+20; i<(delay+80); i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);

    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+80; i<(delay+100); i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);

    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+100; i<(delay+120); i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+120; i<(delay+420); i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+420; i<(delay+440); i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  // Slice Gradient
  for(i=delay+440; i<(delay+460); i++) {
    fSL += fSLstep;
    ival = (int32_t)floor(fSL/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+460; i<(delay+480); i++) {
    ival = (int32_t)floor(fSL/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+480; i<(delay+500); i++) {
    fSL -= fSLstep;
    ival = (int32_t)floor(fSL/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+500; i<(delay+520); i++) {
    fSL -= fSLrepstep;
    ival = (int32_t)floor(fSL/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+520; i<(delay+540); i++) {
    ival = (int32_t)floor(fSL/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+540; i<(delay+560); i++) {
    fSL += fSLrepstep;
    ival = (int32_t)floor(fSL/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
   
  // TSE phase gradients
  // 1st echo + is in readout prephaser
  // 1st echo -
  for(i=delay+560; i<(delay+580); i++) {
    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+580; i<(delay+640); i++) {
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+640; i<(delay+660); i++) {
    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  // 2nd echo +
  for(i=delay+660; i<(delay+680); i++) {
    fPE += fPEstep;
    fPETSE += fPETSEstep;
    ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+680; i<(delay+740); i++) {
    ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+740; i<(delay+760); i++) {
    fPE -= fPEstep;
    fPETSE -= fPETSEstep;
    ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  // 2nd echo -
  for(i=delay+760; i<(delay+780); i++) {
    fPE -= fPEstep;
    fPETSE -= fPETSEstep;
    ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+780; i<(delay+840); i++) {
    ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+840; i<(delay+860); i++) {
    fPE += fPEstep;
    fPETSE += fPETSEstep;
    ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  // 3rd echo +
  for(i=delay+860; i<(delay+880); i++) {
    fPE += fPEstep;
    fPETSE += fPETSEstep;
    ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+880; i<(delay+940); i++) {
    ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+940; i<(delay+960); i++) {
    fPE -= fPEstep;
    fPETSE -= fPETSEstep;
    ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  // 3rd echo -
  for(i=delay+960; i<(delay+980); i++) {
    fPE -= fPEstep;
    fPETSE -= fPETSEstep;
    ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+980; i<(delay+1040); i++) {
    ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1040; i<(delay+1060); i++) {
    fPE += fPEstep;
    fPETSE += fPETSEstep;
    ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  // 4th echo +
  for(i=delay+1060; i<(delay+1080); i++) {
    fPE += fPEstep;
    fPETSE += fPETSEstep;
    ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1080; i<(delay+1140); i++) {
    ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1140; i<(delay+1160); i++) {
    fPE -= fPEstep;
    fPETSE -= fPETSEstep;
    ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  // 4th echo -
  for(i=delay+1160; i<(delay+1180); i++) {
    fPE -= fPEstep;
    fPETSE -= fPETSEstep;
    ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1180; i<(delay+1240); i++) {
    ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1240; i<(delay+1260); i++) {
    fPE += fPEstep;
    fPETSE += fPETSEstep;
    ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  //3DFFT
  for(i=delay+1260; i<(delay+1280); i++) {
    fRO -= fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);

    fPE += fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    fSPE += fSPEstep;
    ival = (int32_t)floor(fSPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1280; i<(delay+1340); i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);

    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    ival = (int32_t)floor(fSPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1340; i<(delay+1360); i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);

    fPE -= fPEstep;
    ival = (int32_t)floor(fPE/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    fSPE -= fSPEstep;
    ival = (int32_t)floor(fSPE/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
   
  // EPI Block Phase
  for(i=delay+1360; i<(delay+1380); i++) {
    fPEEPIB += fPEEPIBstep;
    ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1380; i<(delay+1440); i++) {
    ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1440; i<(delay+1460); i++) {
    fPEEPIB -= fPEEPIBstep;
    ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  //EPI Readout and Bilps
  for(i=delay+1460; i<(delay+1480); i++) {
    fRO -= fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1480; i<(delay+1495); i++) {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1495; i<(delay+1515); i++) {
    fRO += fROprestep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1515; i<(delay+1535); i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  //Blip1
  for(i=delay+1535; i<(delay+1555); i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fPEEPI += fPEEPIstep;
    ival = (int32_t)floor(fPEEPI/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1555; i<(delay+1575); i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fPEEPI -= fPEEPIstep;
    ival = (int32_t)floor(fPEEPI/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  //Blip2
  for(i=delay+1575; i<(delay+1595); i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fPEEPI += fPEEPIstep;
    ival = (int32_t)floor(fPEEPI/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1595; i<(delay+1615); i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fPEEPI -= fPEEPIstep;
    ival = (int32_t)floor(fPEEPI/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  //Blip3
  for(i=delay+1615; i<(delay+1635); i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fPEEPI += fPEEPIstep;
    ival = (int32_t)floor(fPEEPI/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1635; i<(delay+1655); i++) {
    fRO -= fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fPEEPI -= fPEEPIstep;
    ival = (int32_t)floor(fPEEPI/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  //EPI readout end
  for(i=delay+1655; i<(delay+1675); i++) {
    fRO += fROstep;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  //Diffusion gradient
  for(i=delay+1680; i<(delay+1700); i++) {
    fDiffx += fDiffstep;
    ival = (int32_t)floor(fDiffx/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fDiffy += fDiffstep;
    ival = (int32_t)floor(fDiffy/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    fDiffz += fDiffstep;
    ival = (int32_t)floor(fDiffz/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1700; i<(delay+1800); i++) {
    ival = (int32_t)floor(fDiffx/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    ival = (int32_t)floor(fDiffy/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    ival = (int32_t)floor(fDiffz/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1800; i<(delay+1820); i++) {
    fDiffx -= fDiffstep;
    ival = (int32_t)floor(fDiffx/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fDiffy -= fDiffstep;
    ival = (int32_t)floor(fDiffy/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    fDiffz -= fDiffstep;
    ival = (int32_t)floor(fDiffz/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
   
  for(i=delay+1820; i<(delay+1840); i++) {
    fDiffx -= fDiffstep;
    ival = (int32_t)floor(fDiffx/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fDiffy -= fDiffstep;
    ival = (int32_t)floor(fDiffy/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    fDiffz -= fDiffstep;
    ival = (int32_t)floor(fDiffz/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1840; i<(delay+1940); i++) {
    ival = (int32_t)floor(fDiffx/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    ival = (int32_t)floor(fDiffy/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    ival = (int32_t)floor(fDiffz/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+1940; i<(delay+1960); i++) {
    fDiffx += fDiffstep;
    ival = (int32_t)floor(fDiffx/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
     
    fDiffy += fDiffstep;
    ival = (int32_t)floor(fDiffy/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
     
    fDiffz += fDiffstep;
    ival = (int32_t)floor(fDiffz/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
}
*/

void update_gradient_waveforms_FID(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fRO = offset.gradient_x;
  float fPE = offset.gradient_y;
   
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_SE(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;


  float fRO = offset.gradient_x;
  float fPE = offset.gradient_y;
   
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_FID_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float SLamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;


  float fRO = offset.gradient_x;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_SE_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float SLamp, float SLrefamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;


  float fRO = offset.gradient_x;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSLrefamplitude = SLrefamp;
  float fSLrefstep = fSLrefamplitude/20.0;
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_SIR_SE_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float SLamp, float SLrefamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;


  float fRO = offset.gradient_x;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSLrefamplitude = SLrefamp;
  float fSLrefstep = fSLrefamplitude/20.0;
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_EPI(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;
  
  float fPE = offset.gradient_y;
  
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout
    for(i=delay+40; i<(delay+60); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+80; i<(delay+100); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+100; i<(delay+120); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout
    for(i=delay+40; i<(delay+60); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+80; i<(delay+100); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+100; i<(delay+120); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout
    for(i=delay+40; i<(delay+60); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+80; i<(delay+100); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+100; i<(delay+120); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_EPI_SE(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPE = offset.gradient_y;
  
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_EPI_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float SLamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;
  
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+120; i<(delay+140); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+180; i<(delay+200); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_EPI_SE_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float SLamp, float SLrefamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;


  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSLrefamplitude = SLrefamp;
  float fSLrefstep = fSLrefamplitude/20.0;
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+320; i<(delay+340); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+340; i<(delay+360); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+360; i<(delay+380); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+380; i<(delay+400); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+320; i<(delay+340); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+340; i<(delay+360); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+360; i<(delay+380); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+380; i<(delay+400); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Slice gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+200; i<(delay+220); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+260; i<(delay+280); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+300; i<(delay+320); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+320; i<(delay+340); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+340; i<(delay+360); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+360; i<(delay+380); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+380; i<(delay+400); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_GRAD_TEST(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float SPamp, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;
   
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }

  float fx = offset.gradient_x;
  float fy = offset.gradient_y;
  float fz = offset.gradient_z;
  float fz2 = offset.gradient_z2;
  
  // X Gradient
  for(i=delay; i<(delay+20); i++) {
     fx += fSPstep;
     ival = (int32_t)floor(fx/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+20; i<(delay+60); i++) {
     fx -= fSPstep;
     ival = (int32_t)floor(fx/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+60; i<(delay+80); i++) {
     fx += fSPstep;
     ival = (int32_t)floor(fx/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  
   for(i=delay+80; i<(delay+100); i++) {
     fy += fSPstep;
     ival = (int32_t)floor(fy/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+100; i<(delay+140); i++) {
     fy -= fSPstep;
     ival = (int32_t)floor(fy/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+140; i<(delay+160); i++) {
     fy += fSPstep;
     ival = (int32_t)floor(fy/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  
   for(i=delay+160; i<(delay+180); i++) {
     fz += fSPstep;
     ival = (int32_t)floor(fz/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+180; i<(delay+220); i++) {
     fz -= fSPstep;
     ival = (int32_t)floor(fz/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+220; i<(delay+240); i++) {
     fz += fSPstep;
     ival = (int32_t)floor(fz/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  
   for(i=delay+240; i<(delay+260); i++) {
     fz2 += fSPstep;
     ival = (int32_t)floor(fz2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+260; i<(delay+300); i++) {
     fz2 -= fSPstep;
     ival = (int32_t)floor(fz2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=delay+300; i<(delay+320); i++) {
     fz2 += fSPstep;
     ival = (int32_t)floor(fz2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
  
}


void update_gradient_waveforms_proj_GRE(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPE = offset.gradient_y;
   
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout gradient
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout gradient
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout gradient
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_proj_SE(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPE = offset.gradient_y;
   
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout gradient
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout gradient
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout gradient
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}
void update_gradient_waveforms_proj_GRE_angle(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float projangle, float ROamp1, float ROamp2, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitudeCos = cos(projangle)*ROamp1;
  float fROpreamplitudeCos = cos(projangle)*ROamp1*2;
  float fROstepCos = fROamplitudeCos/20.0;
  float fROprestepCos = fROpreamplitudeCos/20.0;
  float fROCos = offset.gradient_x;

  float fROamplitudeSin = sin(projangle)*ROamp2;
  float fROpreamplitudeSin = sin(projangle)*ROamp2*2;
  float fROstepSin = fROamplitudeSin/20.0;
  float fROprestepSin = fROpreamplitudeSin/20.0;
  float fROSin = offset.gradient_y;

  float fPE = offset.gradient_y;
   
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fROCos = offset.gradient_x;
     fROSin = offset.gradient_y;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout gradients
    for(i=delay; i<(delay+20); i++) {
      fROCos -= fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fROCos += fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fROCos += fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fROCos -= fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fROCos = offset.gradient_y;
    fROSin = offset.gradient_z;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout gradients
    for(i=delay; i<(delay+20); i++) {
      fROCos -= fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fROCos += fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fROCos += fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fROCos -= fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fROCos = offset.gradient_z;
    fROSin = offset.gradient_x;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout gradients
    for(i=delay; i<(delay+20); i++) {
      fROCos -= fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fROCos += fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fROCos += fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fROCos -= fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_proj_SE_angle(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float projangle, float ROamp1, float ROamp2, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitudeCos = cos(projangle)*ROamp1;
  float fROpreamplitudeCos = cos(projangle)*ROamp1*2;
  float fROstepCos = fROamplitudeCos/20.0;
  float fROprestepCos = fROpreamplitudeCos/20.0;
  float fROCos = offset.gradient_x;

  float fROamplitudeSin = sin(projangle)*ROamp2;
  float fROpreamplitudeSin = sin(projangle)*ROamp2*2;
  float fROstepSin = fROamplitudeSin/20.0;
  float fROprestepSin = fROpreamplitudeSin/20.0;
  float fROSin = offset.gradient_y;
  
  float fPE = offset.gradient_y;
   
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fROCos = offset.gradient_x;
     fROSin = offset.gradient_y;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout gradients
    for(i=delay; i<(delay+20); i++) {
      fROCos -= fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fROCos += fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fROCos += fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fROCos -= fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fROCos = offset.gradient_y;
    fROSin = offset.gradient_z;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout gradients
    for(i=delay; i<(delay+20); i++) {
      fROCos -= fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fROCos += fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fROCos += fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fROCos -= fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fROCos = offset.gradient_z;
    fROSin = offset.gradient_x;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout gradients
    for(i=delay; i<(delay+20); i++) {
      fROCos -= fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fROCos += fROprestepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROprestepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fROCos += fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin += fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fROCos -= fROstepCos;
      ival = (int32_t)floor(fROCos/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fROSin -= fROstepSin;
      ival = (int32_t)floor(fROSin/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_2D_GRE(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_2D_SE(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_2D_GRE_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float SLamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_2D_SE_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float SLamp, float SLrefamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSLrefamplitude = SLrefamp;
  float fSLrefstep = fSLrefamplitude/20.0;
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_3D_SE_slab(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float SLamp, float SLrefamp, float PEstep, float SPEamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay; // delay has to be < to 1550 in total ?!

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);

  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSLrefamplitude = SLrefamp;
  float fSLrefstep = fSLrefamplitude/20.0;
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;
   
  float fSPEamplitude = SPEamp;
  float fSPEstep = fSPEamplitude/20.0;
  float fSPE = offset.gradient_z;
   

   


  //printf("PE amplitude = %d \n", fPEamplitude);

  // Set waveform base value
  for(i=2; i<2000; i++) {
    ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
    ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
    gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
  
  delay = 2;

  // Design the phase and readout gradients, Phase gradient is in readoutprephaser
  // prephaser 200 us rise time
  if (imor == 0){
    fRO = offset.gradient_x;
    fPE = offset.gradient_y;
    fSL = offset.gradient_z;
    fSPE = offset.gradient_z;
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fSPE += fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fSPE -= fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
   
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice Gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    fSPE = offset.gradient_x;
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fSPE += fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fSPE -= fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
   
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice Gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    fSPE = offset.gradient_y;
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fSPE += fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fSPE -= fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
   
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice Gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}


void update_gradient_waveforms_3D_TSE_slab(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float SLamp, float SLrefamp, float CRamp, float SPamp, float imor, float nPE, float PEstep, float SPEamp, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSLrefamplitude = SLrefamp;
  float fSLrefstep = fSLrefamplitude/20.0;
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;
  
  float signum = 1;
  if (fPEamplitude < 0){
    signum = -1;
  }
  else {
    signum = 1;
  }
   
  float fPETSEstep = nPE/2 * PEstep/20 * signum;
  float fPETSE = 0;
  
  float fSPEamplitude = SPEamp;
  float fSPEstep = fSPEamplitude/20.0;
  float fSPE = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
     fSPE = offset.gradient_z;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fSPE += fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
      
      fSPE -= fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+480; i<(delay+500); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+500; i<(delay+520); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+520; i<(delay+540); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+540; i<(delay+560); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    fSPE = offset.gradient_x;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fSPE += fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
      
      fSPE -= fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+480; i<(delay+500); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+500; i<(delay+520); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+520; i<(delay+540); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+540; i<(delay+560); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    fSPE = offset.gradient_y;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fSPE += fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
      
      fSPE -= fSPEstep;
      ival = (int32_t)floor(fSPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+480; i<(delay+500); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+500; i<(delay+520); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+520; i<(delay+540); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+540; i<(delay+560); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}



void update_gradient_waveforms_2D_SE_diff(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float Diffamp, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;
  
  float fDiffamplitude = Diffamp;
  float fDiffstep = fDiffamplitude/20.0;
  float fDiffx = offset.gradient_x;
  float fDiffy = offset.gradient_y;
  float fDiffz = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
  if (imor == 0){
    fRO = offset.gradient_x;
    fPE = offset.gradient_y;
    fSL = offset.gradient_z;
    fDiffx = offset.gradient_x;
    fDiffy = offset.gradient_y;
    fDiffz = offset.gradient_z;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Diffusion gradient
    for(i=delay+200; i<(delay+220); i++) {
      fDiffx += fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy += fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz += fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fDiffx -= fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy -= fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz -= fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fDiffx -= fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy -= fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz -= fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fDiffx += fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy += fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz += fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    fDiffx = offset.gradient_y;
    fDiffy = offset.gradient_z;
    fDiffz = offset.gradient_x;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Diffusion gradient
    for(i=delay+200; i<(delay+220); i++) {
      fDiffx += fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy += fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz += fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fDiffx -= fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy -= fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz -= fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fDiffx -= fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy -= fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz -= fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fDiffx += fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy += fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz += fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    fDiffx = offset.gradient_z;
    fDiffy = offset.gradient_x;
    fDiffz = offset.gradient_y;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Diffusion gradient
    for(i=delay+200; i<(delay+220); i++) {
      fDiffx += fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy += fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz += fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fDiffx -= fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy -= fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz -= fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fDiffx -= fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy -= fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz -= fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fDiffx += fDiffstep;
      ival = (int32_t)floor(fDiffx/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffy += fDiffstep;
      ival = (int32_t)floor(fDiffy/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fDiffz += fDiffstep;
      ival = (int32_t)floor(fDiffz/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_2D_TSE(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float CRamp, float SPamp, float imor, float nPE, float PEstep, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;
  
  float signum = 1;
  if (fPEamplitude < 0){
    signum = -1;
  }
  else {
    signum = 1;
  }
   
  float fPETSEstep = nPE/2 * PEstep/20 * signum;
  float fPETSE = 0;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+200; i<(delay+220); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+240; i<(delay+260); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+200; i<(delay+220); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+240; i<(delay+260); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Crusher gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+140; i<(delay+160); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+200; i<(delay+220); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+220; i<(delay+240); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+240; i<(delay+260); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_2D_TSE_slice(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float SLamp, float SLrefamp, float CRamp, float SPamp, float imor, float nPE, float PEstep, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
   
  float fSLamplitude = SLamp;
  float fSLrepamplitude = SLamp/2;
  float fSLstep = fSLamplitude/20.0;
  float fSLrepstep = fSLrepamplitude/20.0;
  float fSLrefamplitude = SLrefamp;
  float fSLrefstep = fSLrefamplitude/20.0;
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;
  
  float signum = 1;
  if (fPEamplitude < 0){
    signum = -1;
  }
  else {
    signum = 1;
  }
   
  float fPETSEstep = nPE/2 * PEstep/20 * signum;
  float fPETSE = 0;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+480; i<(delay+500); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+500; i<(delay+520); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+520; i<(delay+540); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+540; i<(delay+560); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+480; i<(delay+500); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+500; i<(delay+520); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+520; i<(delay+540); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+540; i<(delay+560); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    // Readout and phase gradients - coupled
    for(i=delay; i<(delay+20); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);

      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSLstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fSL -= fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fSL += fSLrepstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // Slice gradient with crusher
    for(i=delay+160; i<(delay+180); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fSL -= fCRstep;
      fSL += fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fSL += fCRstep;
      fSL -= fSLrefstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+220; i<(delay+240); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+240; i<(delay+260); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+260; i<(delay+280); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // TSE phase gradients
    // 1st echo + is in readout prephaser
    // 1st echo -
    for(i=delay+280; i<(delay+300); i++) {
      fPE -= fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+300; i<(delay+320); i++) {
      fPE += fPEstep;
      ival = (int32_t)floor(fPE/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo +
    for(i=delay+320; i<(delay+340); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+340; i<(delay+360); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 2nd echo -
    for(i=delay+360; i<(delay+380); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+380; i<(delay+400); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo +
    for(i=delay+400; i<(delay+420); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+420; i<(delay+440); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 3rd echo -
    for(i=delay+440; i<(delay+460); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+460; i<(delay+480); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+2*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo +
    for(i=delay+480; i<(delay+500); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+500; i<(delay+520); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // 4th echo -
    for(i=delay+520; i<(delay+540); i++) {
      fPE -= fPEstep;
      fPETSE -= fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+540; i<(delay+560); i++) {
      fPE += fPEstep;
      fPETSE += fPETSEstep;
      ival = (int32_t)floor((fPE+3*fPETSE)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_2D_EPI(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float nPE, float PEstep, int reps, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
  
  float fPEEPIBstep = -(4*nPE/2*PEstep/20-PEstep/2/20-reps*4*PEstep/20);
  float fPEEPIB = offset.gradient_y;
  float fPEEPIstep = 4*PEstep/20;
  float fPEEPI = offset.gradient_y;
  
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
     fPEEPIB = offset.gradient_y;
     fPEEPI = offset.gradient_y;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // EPI Block Phase
    for(i=delay+40; i<(delay+60); i++) {
      fPEEPIB += fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fPEEPIB -= fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+80; i<(delay+100); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+140; i<(delay+160); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+180; i<(delay+200); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+220; i<(delay+240); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+260; i<(delay+280); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    fPEEPIB = offset.gradient_z;
    fPEEPI = offset.gradient_z;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // EPI Block Phase
    for(i=delay+40; i<(delay+60); i++) {
      fPEEPIB += fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fPEEPIB -= fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+80; i<(delay+100); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+140; i<(delay+160); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+180; i<(delay+200); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+220; i<(delay+240); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+260; i<(delay+280); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    fPEEPIB = offset.gradient_x;
    fPEEPI = offset.gradient_x;
    //Spoiler gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // EPI Block Phase
    for(i=delay+40; i<(delay+60); i++) {
      fPEEPIB += fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+60; i<(delay+80); i++) {
      fPEEPIB -= fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+80; i<(delay+100); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+120; i<(delay+140); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+140; i<(delay+160); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+160; i<(delay+180); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+180; i<(delay+200); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+220; i<(delay+240); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+260; i<(delay+280); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}

void update_gradient_waveforms_2D_EPI_SE(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, volatile uint32_t *gz2, float ROamp, float PEamp, float nPE, float PEstep, int reps, float CRamp, float SPamp, float imor, gradient_offset_t offset)
{
  printf("Designing a gradient waveform -- 2D SE/GRE !\n"); fflush(stdout);

  uint32_t i;
  int32_t ival;
  uint32_t delay = 2;

  float fLSB = 10.0/((1<<15)-1);
  //printf("fLSB = %g Volts\n",fLSB);
  // enable the gradients with the prescribed offset current
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
  gz2[0] = 0x001fffff & (ival | 0x00100000);

  // enable the outputs with 2's completment coding
  // 24'b0010 0000 0000 0000 0000 0010;
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  gz2[1] = 0x00200002;

  float fROamplitude = ROamp;
  float fROpreamplitude = ROamp*2;
  float fROstep = fROamplitude/20.0;
  float fROprestep = fROpreamplitude/20.0;
  float fRO = offset.gradient_x;

  float fPEamplitude = PEamp;
  float fPEstep = fPEamplitude/20.0;
  float fPE = offset.gradient_y;
  
  float fPEEPIBstep = 4*nPE/2*PEstep/20-PEstep/2/20-reps*4*PEstep/20;
  float fPEEPIB = offset.gradient_y;
  float fPEEPIstep = 4*PEstep/20;
  float fPEEPI = offset.gradient_y;
  
  float fCRamplitude = CRamp;
  float fCRstep = fCRamplitude/20.0;
  float fSPamplitude = SPamp;
  float fSPstep = fSPamplitude/20.0;
  float fSL = offset.gradient_z;

  // Set waveform base value
  for(i=2; i<2000; i++) {
     ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
     gx[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
     gy[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
     gz[i] = 0x001fffff & (ival | 0x00100000);
     ival = (int32_t)floor(offset.gradient_z2/fLSB)*16;
     gz2[i] = 0x001fffff & (ival | 0x00100000);
  }
   if (imor == 0){
     fRO = offset.gradient_x;
     fPE = offset.gradient_y;
     fSL = offset.gradient_z;
     fPEEPIB = offset.gradient_y;
     fPEEPI = offset.gradient_y;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    // EPI Block Phase
    for(i=delay+120; i<(delay+140); i++) {
      fPEEPIB += fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fPEEPIB -= fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+160; i<(delay+180); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+220; i<(delay+240); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+260; i<(delay+280); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+300; i<(delay+320); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+320; i<(delay+340); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+340; i<(delay+360); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 1){
    fRO = offset.gradient_y;
    fPE = offset.gradient_z;
    fSL = offset.gradient_x;
    fPEEPIB = offset.gradient_z;
    fPEEPI = offset.gradient_z;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    // EPI Block Phase
    for(i=delay+120; i<(delay+140); i++) {
      fPEEPIB += fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fPEEPIB -= fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+160; i<(delay+180); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+220; i<(delay+240); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+260; i<(delay+280); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+300; i<(delay+320); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+320; i<(delay+340); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+340; i<(delay+360); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
  else if (imor == 2){
    fRO = offset.gradient_z;
    fPE = offset.gradient_x;
    fSL = offset.gradient_y;
    fPEEPIB = offset.gradient_x;
    fPEEPI = offset.gradient_x;
    // Crusher gradient
    for(i=delay; i<(delay+20); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+20; i<(delay+40); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+40; i<(delay+60); i++) {
      fSL += fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    } 
    for(i=delay+60; i<(delay+80); i++) {
      fSL -= fCRstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Spoiler gradient
    for(i=delay+80; i<(delay+100); i++) {
      fSL += fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+100; i<(delay+120); i++) {
      fSL -= fSPstep;
      ival = (int32_t)floor(fSL/fLSB)*16;
      gy[i] = 0x001fffff & (ival | 0x00100000);
    }
    // EPI Block Phase
    for(i=delay+120; i<(delay+140); i++) {
      fPEEPIB += fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+140; i<(delay+160); i++) {
      fPEEPIB -= fPEEPIBstep;
      ival = (int32_t)floor((fPEEPIB)/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI Readout and Bilps
    for(i=delay+160; i<(delay+180); i++) {
      fRO -= fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+180; i<(delay+200); i++) {
      fRO += fROprestep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+200; i<(delay+220); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip1
    for(i=delay+220; i<(delay+240); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+240; i<(delay+260); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip2
    for(i=delay+260; i<(delay+280); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+280; i<(delay+300); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //Blip3
    for(i=delay+300; i<(delay+320); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI += fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    for(i=delay+320; i<(delay+340); i++) {
      fRO -= fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
     
      fPEEPI -= fPEEPIstep;
      ival = (int32_t)floor(fPEEPI/fLSB)*16;
      gx[i] = 0x001fffff & (ival | 0x00100000);
    }
    //EPI readout end
    for(i=delay+340; i<(delay+360); i++) {
      fRO += fROstep;
      ival = (int32_t)floor(fRO/fLSB)*16;
      gz[i] = 0x001fffff & (ival | 0x00100000);
    }
  }
}


// This function updates the pulse sequence in the memory with the uploaded sequence
void update_pulse_sequence_from_upload(uint32_t *pulseq_memory_upload, volatile uint32_t *pulseq_memory)
{
  int i;
  int length = 400;
  for(i=0; i<length; i++){
    pulseq_memory[i] = pulseq_memory_upload[i];
  }
}



void update_RF_pulses(volatile uint16_t *tx_size, void *tx_data,  int32_t RF_amp, int32_t RF_flip_amp, int32_t RF_pulse_length, int32_t RF_flip_length, float freq_offset, float phase_offset)
{
  int i, j;
  int size;
  float pi = 3.14159;
  int16_t pulse[32768];
  float _Complex cpulse[16384];
  printf("freq_offset: %f\n", freq_offset);
  printf("freq_phase: %f\n", phase_offset);
  float freq_offset2 = round(1.25*freq_offset);
  float freq_offset3 = round(freq_offset2*((float)RF_flip_length/(2*(float)RF_pulse_length)));
  
  for(i = 0; i < 32768; i++) {
    pulse[i] = 0;
  }
  
  // RF Hardpulse Ref Amp
  for(i = 0; i <= 2*(2*RF_pulse_length); i=i+2) {
    j=i/2-RF_pulse_length;
    cpulse[i/2] = cexp(I*(2*pi*freq_offset3*j+phase_offset));
    pulse[i] = RF_amp*creal(cpulse[i/2]);
    pulse[i+1] = RF_amp*cimag(cpulse[i/2]);
  }

  // RF Hardpulse Flip Amplitude
  for(i = 1000; i <= 1000+2*(RF_flip_length); i=i+2) {
    j=(i-1000)/2-RF_flip_length/2;
    cpulse[i/2] = cexp(I*(2*pi*freq_offset2*j+phase_offset));
    pulse[i] = RF_flip_amp*creal(cpulse[i/2]);
    pulse[i+1] = RF_flip_amp*cimag(cpulse[i/2]);
  }

  // RF Sincpulse
  for(i = 2000; i <= 2000+2*(4*2*RF_pulse_length); i=i+2) {
    j=(i-2000)/2-2*2*RF_pulse_length; 
    cpulse[i/2] = sin(2*pi*j/(4*RF_pulse_length))/(2*pi*j/(4*RF_pulse_length))*cexp(I*(2*pi*freq_offset3*j+phase_offset));
    pulse[i] = RF_amp*creal(cpulse[i/2]);
    pulse[i+1] = RF_amp*cimag(cpulse[i/2]);
  }
  i = 2000+2*(2*2*RF_pulse_length); 
  cpulse[i/2] = cexp(I*(2*pi*freq_offset3*0+phase_offset));
  pulse[i] = RF_amp*creal(cpulse[i/2]);
  pulse[i+1] = RF_amp*cimag(cpulse[i/2]);
  
  // RF Sincpulse Flipangle
  for(i = 6000; i <= 6000+2*(4*RF_flip_length); i=i+2) {
    j=(i-6000)/2-2*RF_flip_length; 
    cpulse[i/2] = sin(2*pi*j/(2*RF_flip_length))/(2*pi*j/(2*RF_flip_length))*cexp(I*(2*pi*freq_offset2*j+phase_offset));
    pulse[i] = RF_flip_amp*creal(cpulse[i/2]);
    pulse[i+1] = RF_flip_amp*cimag(cpulse[i/2]);
  }
  i = 6000+2*2*RF_flip_length;
  cpulse[i/2] = cexp(I*(2*pi*freq_offset2*0+phase_offset));
  pulse[i] = RF_flip_amp*creal(cpulse[i/2]);
  pulse[i+1] = RF_flip_amp*cimag(cpulse[i/2]);

  size = 32768-1;
  *tx_size = size;
  memset(tx_data, 0, 65536);
  memcpy(tx_data, pulse, 2 * size);
}


int main(int argc)
{

  // -- Communication and Data -- //
  int fd, sock_server, sock_client, conn_status;
  void *cfg, *sts;
  volatile uint32_t *slcr, *rx_freq, *rx_rate, *seq_config, *pulseq_memory, *tx_divider;
  volatile uint16_t *rx_cntr, *tx_size;
  //volatile uint8_t *rx_rst, *tx_rst;
  volatile uint64_t *rx_data;
  void *tx_data;
  float tx_freq;
  struct sockaddr_in addr;
  unsigned char command[40];
  int16_t pulse[32768];
  uint64_t buffer[8192];
  int size, yes = 1;
  float pi = 3.14159;
  int i, j; // for loop
  swappable_int32_t lv,bv;

  // -- Gradients -- //
  float pe, pe_step, ro, ro1, ro2, sl, slref, spe_step, spe, da, cr, sp, imor; // related to gradient amplitude
  gradient_offset_t gradient_offset;
  volatile uint32_t *gradient_memory_x;
	volatile uint32_t *gradient_memory_y;
	volatile uint32_t *gradient_memory_z;
	volatile uint32_t *gradient_memory_z2;
  gradient_offset.gradient_x = 0;
  gradient_offset.gradient_y = 0;
  gradient_offset.gradient_z = 0;
  gradient_offset.gradient_z2 = 0;

  // -- Sequence Upload -- //
  uint32_t pulseq_memory_upload_temp[400]; // record uploaded sequence
  unsigned char *b; // for sequence upload
  unsigned int cmd; // for sequence upload
  uint32_t mem_counter, nbytes, size_of_seq; // for sequence upload

  // -- Received Data from Client -- //
  uint32_t trig;  // Trigger (highest 4 bits of command)
  uint32_t freq;  // Frequency (Lower 28 bits of command, 2^28 = 268,435,456 enough for frequency ~15,700,000)
  uint32_t grad_sign; // Sign of gradient offset
  uint32_t grad_ax; // Gradient axis: x, y, z, z2
  int32_t grad_offset; // Gradient offset value
  uint32_t npe;   // Number of phase encodings for 2D SE
  uint32_t proj_ax;

  // -- Defaults (freq & at in mem map) -- //
  uint32_t default_frequency = 11300000; // 11.3MHz
  volatile uint32_t *attn_config;

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
  float attenuation = 31.75;
  // Check if its bigger than 31.75 or some thing (later)
  if(attenuation < 0.0 || attenuation > 31.75) {
    fprintf(stderr,"Error: transmit attenuation of %g dB out of range.\n Please specify a value between 0 and 31.75 dB!\n",attenuation);
    return -1;
  }

  // convert to the bits
  unsigned int attn_bits = attenuation/0.25;

  // set the attenuation value
  attn_config[0] = attn_bits;

  printf("Attn register value: %g dB (bits = %d)\n",attenuation,attn_config[0]);

  //NOTE: The block RAM can only be addressed with 32 bit transactions, so gradient_memory needs to
  //be of type uint32_t. The HDL would have to be changed to an 8-bit interface to support per
  //byte transactions
  gradient_memory_x = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40002000);
	gradient_memory_y = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40004000);
	gradient_memory_z = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40006000);
	gradient_memory_z2 = mmap(NULL, 2*sysconf(_SC_PAGESIZE), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0x40008000);

  printf("Setup standard memory maps !\n"); fflush(stdout);

  //rx_rst = ((uint8_t *)(cfg + 0));
  tx_divider = ((uint32_t *)(cfg + 0));

  rx_freq = ((uint32_t *)(cfg + 4));
  rx_rate = ((uint32_t *)(cfg + 8));
  rx_cntr = ((uint16_t *)(sts + 0));

  //tx_rst = ((uint8_t *)(cfg + 1));
  tx_size = ((uint16_t *)(cfg + 12));

  printf("Setting FPGA clock to 143 MHz !\n"); fflush(stdout);

  // set FPGA clock to 143 MHz
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

  // set default rx sample rate
  *rx_rate = 250;

  // fill tx buffer with zeros
  memset(tx_data, 0, 65536);

  // local oscillator for the excitation pulse
  tx_freq = 19.0e6;  // not used
  for(i = 0; i < 32768; i++) {
    pulse[i] = 0;
  }

  // ************* Design RF pulse ************* //
  uint32_t duration = 420;  // 64+2*duration < 2*offset_gap = 2000 -> duration<968
  uint32_t offset_gap = 1000;
  uint32_t memory_gap = 2*offset_gap;
  int32_t RF_amp = 16384; // 2*14bit = 32768 (needs to be checked again)
  int32_t RF_flip_amp = 16384;
  int32_t RF_pulse_length;
  int32_t RF_flip_length;
  // this divider makes the sample duration a convenient 1us
  *tx_divider = 125;

  // RF sample duration is
  float txsample_duration_us = 1.0/125.0*(float)(*tx_divider);

  printf("Transmit sample duration is %g us\n",txsample_duration_us);

  unsigned int ntxsamples_needed = (float)(duration)/txsample_duration_us;
  printf("A %d us pulse would need %d samples !\n",duration,ntxsamples_needed);

// Old RF generation
/*
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
  // RF Pulse 5: SINC PULSE 50% amp
  pulse[7*memory_gap+64+256] = RF_amp;
  for(i = 7*memory_gap; i <= 7*memory_gap+512; i=i+2) {
    j = (int)((i - (7*memory_gap+64)) / 2) - 128;
    pulse[i] = (int16_t) floor(48*RF_amp/2*(0.54 + 0.46*(cos((pi*j)/(2*48)))) * sin((pi*j)/(48))/(pi*j));
  }
  pulse[7*memory_gap+64+256] = RF_amp/2;

  size = 32768-1;
  *tx_size = size;
  memset(tx_data, 0, 65536);
  memcpy(tx_data, pulse, 2 * size);
  // ************* End of RF pulse ************* //
*/
  
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
        conn_status = recv(sock_client, &command, sizeof(command), MSG_WAITALL);
        if( conn_status <= 0 ) {
          // If status is <= 0 close connection and break -- listen again
          close(sock_server);
        }
        break;
      }
      //printf("Status: %d \n", conn_status);
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
        6: Acquire 2D image
      */
      //printf("Command 0-40: \n 0: %d, 1: %d, 2: %d, 3: %d \n 4: %d, 5: %d, 6: %d, 7: %d \n 8: %d, 9: %d, 10: %d, 11: %d \n 12: %d, 13: %d, 14: %d, 15: %d \n 16: %d, 17: %d, 18: %d, 19: %d \n 20: %d, 21: %d, 22: %d, 23: %d \n 24: %d, 25: %d, 26: %d, 27: %d \n 28: %d, 29: %d, 30: %d, 31: %d \n 32: %d, 33: %d, 34: %d, 35: %d \n 36: %d, 37: %d, 38: %d, 39: %d \n", command[0], command[1], command[2], command[3], command[4], command[5], command[6], command[7], command[8], command[9], command[10], command[11], command[12], command[13], command[14], command[15], command[16], command[17], command[18], command[19], command[20], command[21], command[22], command[23], command[24], command[25], command[26], command[27], command[28], command[29], command[30], command[31], command[32], command[33], command[34], command[35], command[36], command[37], command[38], command[39]);
      trig = (float)command[0] + (float)command[1]*0x100;
      //printf("Trigger %d \n", trig);
      
      //if (trig == 0 ) {
        //continue;
      //}
      /*
      //------------------------------------------------------------------------
      //  Acquire when triggered
      //------------------------------------------------------------------------
      if (trig == 1) {
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
      */
      
      //------------------------------------------------------------------------
      //  Change center frequency
      //------------------------------------------------------------------------
      if ( trig == 2 ) {
        printf("Change frequency value.\n");
        freq = command[36] + command[37]*0x100 +command[38]*0x10000 + command[39]*0x1000000;
        *rx_freq = (uint32_t)floor(freq / 125.0e6 * (1<<30) + 0.5);
        printf("Setting frequency to %.4f MHz\n",freq/1e6f);
        if(freq < 0 || freq > 60000000) {
          printf("Frequency value out of range\n");
          continue;
        }
        continue;  // wait for acquire command
      }
      
      //------------------------------------------------------------------------
      //  Change attenuator value
      //------------------------------------------------------------------------
      else if ( trig == 3 ) {
        printf("Change attenuator value.\n");
        unsigned int attn_value = command[36] + command[37]*0x100 +command[38]*0x10000 + command[39]*0x1000000;
        printf("Setting attenuation to %.2f dB\n", (float)(attn_value)*0.25);
        if (attn_value > 127) {
          printf("Attenuator setting out of range, clipping at 31.75 dB\n");
          attn_value = 127;
        }
        // set the attenuation value
        attn_config[0] = attn_value;
        continue;  // wait for acquire command
      }
      
      //------------------------------------------------------------------------
      //  Receive pulse sequence from frontend
      //------------------------------------------------------------------------
      else if ( trig == 4 ) { // receive pulse sequence from frontend
        printf("Receive pulse sequence from frontend.\n");

        // seqType_idx = (int)(command & 0x0fffffff);
        
        //printf("%s \n", "Receiving pulse sequence");
        nbytes = read(sock_client, &buffer, sizeof(buffer));
        printf("%s %d \n", "Num bytes received = ", nbytes);
        b = (unsigned char*) buffer;

        mem_counter = nbytes/4 - 1;
        for (i=nbytes-1; i>=0; i-=4) {
          cmd = (b[i]<<24) | (b[i-1]<<16)| (b[i-2] <<8) | b[i-3];
          pulseq_memory_upload_temp[mem_counter] = cmd;
          mem_counter -= 1;
        }

        //mem_counter = 0;
        //for (i=0; i<nbytes; i+=4) {
          //printf("\tpulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);
          //mem_counter += 1;
        //}

        //printf("%s \n", "Pulse sequence loaded");
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        continue;  // wait for acquire command
      }
      
      //------------------------------------------------------------------------
      //  Set Gradient offsets
      //------------------------------------------------------------------------
      else if ( trig == 5 ) {

        printf("> Load gradient offsets \n");

        grad_ax = command[32];
        grad_sign = command[39];
        grad_offset = command[36] +command[37]*0x100 + command[38]*0x1000;
        printf("Axis = %d \n", grad_ax);
        printf("Sign = %d \n", grad_sign);
        printf("Value = %d \n", grad_offset);

        if (grad_sign == 1) grad_offset = -grad_offset;

        switch(grad_ax){
          case 0:
            printf("Set X gradient offset : %d \n", grad_offset);
            gradient_offset.gradient_x = (float)grad_offset/1000.0;
            break;
          case 1:
            printf("Set Y gradient offset : %d \n", grad_offset);
            gradient_offset.gradient_y = (float)grad_offset/1000.0;
            break;
          case 2:
            printf("Set Z gradient offset : %d \n", grad_offset);
            gradient_offset.gradient_z = (float)grad_offset/1000.0;
            break;
          case 3:
            printf("Set Z2 gradient offset : %d \n", grad_offset);
            gradient_offset.gradient_z2 = (float)grad_offset/1000.0;
            break;
          default:
            printf("Gradient axis not specified.\n");
            break;
        }

        update_gradient_waveform_state(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2,GRAD_OFFSET_ENABLED_OUTPUT,gradient_offset);
        printf("Gradient offsets updated with values: X %d, Y %d, Z %d Z2 %d [mA]\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));

        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D GRE 
      //------------------------------------------------------------------------
      else if ( trig == 8 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_GRE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, sp, imor, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_GRE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, sp, imor, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D SE 
      //------------------------------------------------------------------------
      else if ( trig == 9 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        cr = ((float)command[24] + (float)command[25]*0x100)/1000;
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_SE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, cr, sp, imor, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_SE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, cr, sp, imor, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D GRE slice
      //------------------------------------------------------------------------
      else if ( trig == 10 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sl = ((float)command[30] + (float)command[31]*0x100)/1000; // Slicegradient hight
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_GRE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, sl, sp, imor, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_GRE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, sl, sp, imor, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D SE slice
      //------------------------------------------------------------------------
      else if ( trig == 11 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sl = ((float)command[30] + (float)command[31]*0x100)/1000; // Slicegradient hight
        cr = ((float)command[24] + (float)command[25]*0x100)/1000;
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        slref = sl * RF_flip_length / (2* RF_pulse_length);
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_SE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, sl, slref, cr, sp, imor, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_SE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, sl, slref, cr, sp, imor, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 3D SE slab
      //------------------------------------------------------------------------
      else if ( trig == 12 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sl = ((float)command[30] + (float)command[31]*0x100)/1000; // Slicegradient hight
        float snpe = command[26] + command[27]*0x100;
        spe_step = ((float)command[24] + (float)command[25]*0x100)/1000; // Slice Phasegradient stepsize
        spe = (-(snpe/2)+1)*spe_step - spe_step/2;
        cr = ((float)command[20] + (float)command[21]*0x100)/1000;
        sp = ((float)command[22] + (float)command[23]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        slref = sl * RF_flip_length / (2* RF_pulse_length);
        
        //printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        for(int reps2=0; reps2<snpe; reps2++) {
          update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
          update_gradient_waveforms_3D_SE_slab(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, sl, slref, pe_step, spe, cr, sp, imor,gradient_offset);
          for(int reps=0; reps<npe; reps++) {
            // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
            seq_config[0] = 0x00000000;
            pe = pe+pe_step;
            //printf("PE to set = %d\n", pe);
            update_gradient_waveforms_3D_SE_slab(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, sl, slref, pe_step, spe, cr, sp, imor,gradient_offset);
            usleep(tr*1000); // tr in ms
          }
          spe = spe+spe_step;
          pe = -(npe/2)*pe_step + pe_step/2;
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D SE Diffusion
      //------------------------------------------------------------------------
      else if ( trig == 13 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        da = ((float)command[24] + (float)command[25]*0x100)/1000;
        cr = ((float)command[20] + (float)command[21]*0x100)/1000;
        sp = ((float)command[22] + (float)command[23]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_SE_diff(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, da, cr, sp, imor, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_SE_diff(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, da, cr, sp, imor, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire FID 
      //------------------------------------------------------------------------
      else if ( trig == 14 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        sp = ((float)command[36] + (float)command[37]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_FID(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire SE 
      //------------------------------------------------------------------------
      else if ( trig == 15 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        cr = ((float)command[36] + (float)command[37]*0x100)/1000;
        sp = ((float)command[38] + (float)command[39]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_SE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, cr, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire Projection GRE 
      //------------------------------------------------------------------------
      else if ( trig == 16 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        ro = ((float)command[36] + (float)command[37]*0x100)/1000; // Readoutgradient hight
        sp = ((float)command[34] + (float)command[35]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_proj_GRE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire Projection SE 
      //------------------------------------------------------------------------
      else if ( trig == 17 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        ro = ((float)command[36] + (float)command[37]*0x100)/1000; // Readoutgradient hight
        cr = ((float)command[32] + (float)command[33]*0x100)/1000;
        sp = ((float)command[34] + (float)command[35]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_proj_SE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, cr, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire FID Slice
      //------------------------------------------------------------------------
      else if ( trig == 18 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        sl = ((float)command[32] + (float)command[33]*0x100)/1000; // Slicegradient hight
        sp = ((float)command[36] + (float)command[37]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_FID_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2 ,sl ,sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire SE Slice
      //------------------------------------------------------------------------
      else if ( trig == 19 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        sl = ((float)command[32] + (float)command[33]*0x100)/1000; // Slicegradient hight
        cr = ((float)command[36] + (float)command[37]*0x100)/1000;
        sp = ((float)command[38] + (float)command[39]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        slref = sl * RF_flip_length / (2* RF_pulse_length);
        
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_SE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, sl, slref, cr, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire RF Test 
      //------------------------------------------------------------------------
      else if ( trig == 20 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_FID(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D TSE 
      //------------------------------------------------------------------------
      else if ( trig == 21 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        cr = ((float)command[24] + (float)command[25]*0x100)/1000;
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_TSE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, cr, sp, imor, npe, pe_step, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
          seq_config[0] = 0x00000007;
          usleep(1000000); // sleep 1 second
          // printf("Number of RX samples in FIFO: %d\n",*rx_cntr);
          // Transfer the data to the client
          // transfer 10 * 5k = 50k samples
          for(i = 0; i < 10; ++i) {
            while(*rx_cntr < 5000) usleep(500);
            for(j = 0; j < 5000; ++j) buffer[j] = *rx_data;
            send(sock_client, buffer, 5000*8, MSG_NOSIGNAL | (i<9?MSG_MORE:0));
          }
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_TSE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, cr, sp, imor, npe, pe_step, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D EPI SE
      //------------------------------------------------------------------------
      else if ( trig == 22 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        cr = ((float)command[24] + (float)command[25]*0x100)/1000;
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_EPI_SE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, npe, pe_step, 0, cr, sp, imor, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_EPI_SE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, npe, pe_step, reps+1, cr, sp, imor, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D TSE slice
      //------------------------------------------------------------------------
      else if ( trig == 23 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sl = ((float)command[30] + (float)command[31]*0x100)/1000; // Slicegradient hight
        cr = ((float)command[24] + (float)command[25]*0x100)/1000;
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        slref = sl * RF_flip_length / (2* RF_pulse_length);
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_TSE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, sl, slref, cr, sp, imor, npe, pe_step, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_TSE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, sl, slref, cr, sp, imor, npe, pe_step, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire 2D EPI
      //------------------------------------------------------------------------
      else if ( trig == 24 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_2D_EPI(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, npe, pe_step, 0, sp, imor, gradient_offset);
        for(int reps=0; reps<npe; reps++) {
          // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
          seq_config[0] = 0x00000000;
          pe = pe+pe_step;
          //printf("PE to set = %d\n", pe);
          update_gradient_waveforms_2D_EPI(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,pe, npe, pe_step, reps+1, sp, imor, gradient_offset);
          usleep(tr*1000); // tr in ms
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire EPI
      //------------------------------------------------------------------------
      else if ( trig == 25 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        ro = ((float)command[32] + (float)command[33]*0x100)/1000; // Readoutgradient hight
        sp = ((float)command[36] + (float)command[37]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_EPI(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2 ,ro ,sp, imor, gradient_offset);

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
      
        printf("---------------------------------------\n");
        continue;
      }
     
      //------------------------------------------------------------------------
      //  Acquire SE EPI
      //------------------------------------------------------------------------
      else if ( trig == 26 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        ro = ((float)command[32] + (float)command[33]*0x100)/1000; // Readoutgradient hight
        cr = ((float)command[36] + (float)command[37]*0x100)/1000;
        sp = ((float)command[38] + (float)command[39]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_EPI_SE(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, cr, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire SIR SE Slice
      //------------------------------------------------------------------------
      else if ( trig == 27 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        sl = ((float)command[32] + (float)command[33]*0x100)/1000; // Slicegradient hight
        cr = ((float)command[36] + (float)command[37]*0x100)/1000;
        sp = ((float)command[38] + (float)command[39]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        slref = sl * RF_flip_length / (2* RF_pulse_length);
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_SIR_SE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, sl, slref, cr, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire EPI Slice
      //------------------------------------------------------------------------
      else if ( trig == 28 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sl = ((float)command[32] + (float)command[33]*0x100)/1000; // Slicegradient hight
        sp = ((float)command[36] + (float)command[37]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_EPI_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro ,sl ,sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire EPI SE Slice
      //------------------------------------------------------------------------
      else if ( trig == 29 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sl = ((float)command[32] + (float)command[33]*0x100)/1000; // Slicegradient hight
        cr = ((float)command[36] + (float)command[37]*0x100)/1000;
        sp = ((float)command[38] + (float)command[39]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        slref = sl * RF_flip_length / (2* RF_pulse_length);
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_EPI_SE_slice(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, sl, slref, cr, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire Projection SE angle
      //------------------------------------------------------------------------
      else if ( trig == 30 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        ro1 = ((float)command[36] + (float)command[37]*0x100)/1000; // Readoutgradient hight
        ro2 = ((float)command[38] + (float)command[39]*0x100)/1000; // Readoutgradient hight
        cr = ((float)command[32] + (float)command[33]*0x100)/1000;
        sp = ((float)command[34] + (float)command[35]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        float projection_angle = ((float)command[28] + (float)command[29]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_proj_SE_angle(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, projection_angle, ro1, ro2, cr, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire Projection GRE angle
      //------------------------------------------------------------------------
      else if ( trig == 31 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        ro1 = ((float)command[36] + (float)command[37]*0x100)/1000; // Readoutgradient hight
        ro2 = ((float)command[38] + (float)command[39]*0x100)/1000; // Readoutgradient hight
        sp = ((float)command[34] + (float)command[35]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        float projection_angle = ((float)command[32] + (float)command[33]*0x100)/100;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_proj_GRE_angle(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, projection_angle, ro1, ro2, sp, imor, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
      }
    
      //------------------------------------------------------------------------
      //  Acquire 3D TSE slab
      //------------------------------------------------------------------------
      else if ( trig == 32 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);

        float npe = command[32] + command[33]*0x100;
        uint32_t tr = command[36] + command[37]*0x100 + command[38]*0x10000 + command[39]*0x1000000;
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = command[4] + command[5]*0x100 + command[6]*0x10000 + command[7]*0x1000000;
        RF_pulse_length = command[8] + command[9]*0x100;
        RF_flip_length = command[10] + command[11]*0x100;
        pe_step = ((float)command[28] + (float)command[29]*0x100)/1000; // Phasegradient stepsize
        pe = -(npe/2)*pe_step + pe_step/2;
        ro = ((float)command[34] + (float)command[35]*0x100)/1000; // Readoutgradient hight
        sl = ((float)command[30] + (float)command[31]*0x100)/1000; // Slicegradient hight
        float snpe = command[22] + command[23]*0x100;
        spe_step = ((float)command[20] + (float)command[21]*0x100)/1000; // Slice Phasegradient stepsize
        spe = -(snpe/2)*spe_step + spe_step/2;
        cr = ((float)command[24] + (float)command[25]*0x100)/1000;
        sp = ((float)command[26] + (float)command[27]*0x100)/1000;
        imor = (float)command[2] + (float)command[3]*0x100;
        float freq_offset;
        if (command[18] == 1) {
          freq_offset = -1*((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000);
        }
        else {
          freq_offset = ((float)command[12] + (float)command[13]*0x100 + (float)command[14]*0x10000 + (float)command[15]*0x1000000); 
        }
        float phase_offset = ((float)command[16] + (float)command[17]*0x100)/100;
        
        slref = sl * RF_flip_length / (2* RF_pulse_length);
 
        //printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        for(int reps2=0; reps2<snpe; reps2++) {
          update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
          update_gradient_waveforms_3D_TSE_slab(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, sl, slref, cr, sp, imor, npe, pe_step, spe, gradient_offset);
          for(int reps=0; reps<npe; reps++) {
            // printf("TR[%d]: go!!\n",reps);
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
            //printf("stop !!\n");
            seq_config[0] = 0x00000000;
            pe = pe+pe_step;
            //printf("PE to set = %d\n", pe);
            update_gradient_waveforms_3D_TSE_slab(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, ro, pe, sl, slref, cr, sp, imor, npe, pe_step, spe, gradient_offset);
            usleep(tr*1000); // tr in ms
          }
          spe = spe+spe_step;
          pe = -(npe/2)*pe_step + pe_step/2;
        }
        printf("---------------------------------------\n");
        continue;
      }
      
      //------------------------------------------------------------------------
      //  Acquire Gradient Test 
      //------------------------------------------------------------------------
      else if ( trig == 33 ) {

        // update_pulse_sequence(2, pulseq_memory); // Spin echo
        update_pulse_sequence_from_upload(pulseq_memory_upload_temp, pulseq_memory);
        // printf("npe = %f \t TR = %d ms\n" , npe, tr);

        // printf("_____2D Imaging Spin Echo (npe = %f)_____\n", npe);
        usleep(10); // sleep 10us
        // printf("Acquiring\n");
        RF_flip_amp = 0;
        RF_pulse_length = 0;
        RF_flip_length = 0;
        float freq_offset = 0;
        float phase_offset = 0;
        sp = ((float)command[36] + (float)command[37]*0x100)/1000;
  
        // printf("GRO Amplitude: %f , GPE Step: %f , GS Amplitude: %f \n", ro, pe_step, sl);

        clear_gradient_waveforms(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2);
        

        // printf("PE step: %d \nPE: %d \nro: %d \n", pe_step, pe, ro);
        // printf("pulseq_memory[%d] = 0x%08x\n", mem_counter, pulseq_memory_upload_temp[mem_counter]);

        // Print gradient offsets (after waveforms updated!)
        // printf("Gradient offsets(mA): X %d, Y %d, Z %d, Z2 %d mA\n", (int)(gradient_offset.gradient_x*1000), (int)(gradient_offset.gradient_y*1000), (int)(gradient_offset.gradient_z*1000), (int)(gradient_offset.gradient_z2*1000));
        
        update_RF_pulses(tx_size, tx_data, RF_amp, RF_flip_amp, RF_pulse_length, RF_flip_length, freq_offset, phase_offset);
        update_gradient_waveforms_GRAD_TEST(gradient_memory_x,gradient_memory_y,gradient_memory_z,gradient_memory_z2, sp, gradient_offset);
     
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
      
        printf("---------------------------------------\n");
        continue;
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
