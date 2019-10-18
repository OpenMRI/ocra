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
typedef struct
{
  float gradient_x;
  float gradient_y;
  float gradient_z;
} gradient_offset_t;


void generate_gradient_waveforms(volatile uint32_t *gx,volatile uint32_t *gy, volatile uint32_t *gz, gradient_offset_t offset)
{
  uint32_t i;
  int32_t ival;
  float fLSB = 10.0/((1<<15)-1);
  
  ival = (int32_t)floor(offset.gradient_x/fLSB)*16;
  gx[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_y/fLSB)*16;
  gy[0] = 0x001fffff & (ival | 0x00100000);
  ival = (int32_t)floor(offset.gradient_z/fLSB)*16;
  gz[0] = 0x001fffff & (ival | 0x00100000);
  gx[1] = 0x00200002;
  gy[1] = 0x00200002;
  gz[1] = 0x00200002;
  float fRO = offset.gradient_x;
  //Design the X gradient
  for(i=0; i<500; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=500; i<620; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=620; i<740; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=740; i<741; i++)
  {
    fRO += 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=741; i<860; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=860; i<1859; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1859; i<1160; i++)
  {
    fRO -= 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1160; i<1460; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1460; i<1580; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1580; i<1700; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1700; i<1820; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1820; i<1821; i++)
  {
    fRO += 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1821; i<3819; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=3819; i<2220; i++)
  {
    fRO -= 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=2220; i<2225; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=2225; i<200000; i++)
  {
    ival=(int32_t)floor(offset.gradient_x/fLSB)*16;
    gx[i] = 0x001fffff & (ival | 0x00100000);
  }


  //Design the Y gradient
  for(i=0; i<500; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=500; i<620; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=620; i<740; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=740; i<741; i++)
  {
    fRO += 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=741; i<860; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=860; i<1859; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1859; i<1160; i++)
  {
    fRO -= 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1160; i<1460; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1460; i<1580; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1580; i<1700; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1700; i<1820; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1820; i<1821; i++)
  {
    fRO += 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1821; i<3819; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=3819; i<2220; i++)
  {
    fRO -= 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=2220; i<2225; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=2225; i<200000; i++)
  {
    ival=(int32_t)floor(offset.gradient_y/fLSB)*16;
    gy[i] = 0x001fffff & (ival | 0x00100000);
  }


  //Design the Z gradient
  for(i=0; i<500; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=500; i<501; i++)
  {
    fRO += 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=501; i<620; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=620; i<739; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=739; i<740; i++)
  {
    fRO -= 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=740; i<741; i++)
  {
    fRO -= 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=741; i<859; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=859; i<860; i++)
  {
    fRO += 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=860; i<1160; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1160; i<1460; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1460; i<1461; i++)
  {
    fRO += 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1461; i<1580; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1580; i<1699; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1699; i<1700; i++)
  {
    fRO -= 0.01;
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1700; i<1820; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=1820; i<2220; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=2220; i<2225; i++)
  {
    ival = (int32_t)floor(fRO/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
  for(i=2225; i<200000; i++)
  {
    ival=(int32_t)floor(offset.gradient_z/fLSB)*16;
    gz[i] = 0x001fffff & (ival | 0x00100000);
  }
}
