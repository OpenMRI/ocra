# How To - OCRA Tabletop MRI System (RP125-14, RPi 3B+)

1. Startup
2. Finding the first signal
    1. Manual frequency search
    2. Automatic frequency search
3. Flip angle adjustment
    1. Manual transmit adjust
    2. Automatic transmit adjust
4. Shimming of the B0 field
    1. Manual shimming
    2. Automatic shimming
5. Adjusting the gradients
    1. Testing the gradients
    2. Gradient scaling
6. Parameters for spectroscopy and imaging
    1. Spectroscopy
        1. Free Induction Decay (FID)
        2. Spin Echo (SE)
    2. Imaging
        1. 2D Gradient Echo (GRE)
        2. 2D Spin Echo (SE)

## 1 Startup

Boot the Raspberry Pi by connecting it to power and log in (user: pi, pw: raspberry).

After the Raspberry Pi is booted completely switch on the console and gradient power amplifier (push the reset button when a red LED is visible).

Open the file manager and go to /home/pi/relax2.

Double click on the Relax2_main.py file to open it with the Thonny editor.

Click on the green play button (Run current script) to start the Relax 2.0 graphical user interface.

Connect to the console (192.168.1.84).

## 2 Finding the first signal

To excite spins with RF pulses the carrier frequency of the RF pulse needs to match the LARMOR frequency of the OCRA Tabletop System.

### 2.i Manual frequency search

Insert a water sample (without a 3D printed sample).

In the main window click on Spectroscopy and select the Spin Echo sequence.

In the main window click on parameters.

Enter the following parameters.

Parameters: 
- 90° Ref. Pulselength = 100us
- TE = 12ms
- TR = 500ms
- Sampling Time TS = 6ms
- RF Attenuation = -15dB
- Averaging off
- all Shims = 0mA
- RF Frequency = marked on the magnet (about 11.30MHz)

In the main window click on Acquire.

Check the log in Thonny for ‘Spectrum acquired!’.

In the main window click on Data Process.

The Signal should be shown in the plot.

If the signal is not visible search for the signal in the range of 11.10 MHz to 11.40MHz (parameter window - RF Frequency) by repeating the measurement.

Reacquire the signal with different RF frequencies till you find the spectrum peak.
 
Verify that it’s the spin signal by removing the sample.
 
When the sample is removed the signal should disappear.
 
If not, it’s just a noise peak.

The time domain signal should have a bell curve.

If you are close to the frequency in your plot you can press ‘Recenter’ in the parameter window.

Iterrate the measurement and recenter process till you have the exact LARMOR frequency.

RF Frequency: _____________________MHz

### 2.ii Automatic frequency search

Try the Autocenter Tool (main window - Tools) and compare your results.

Define your range and search in steps of 5000Hz.

Autocenter RF Frequency: _____________________MHz

## 3 Flip angle adjustment

The RF Attenuation scales the RF pulse amplitudes. 
Small attenuation (-1dB) means high RF pulse amplitudes and high flip angles, high attenuation (-31dB) means low RF pulse amplitudes and small flip angles. 

### 3.i Manual transmit adjust

Acquire Spin Echo Signals with different RF attenuations (-31dB to -1dB in steps of 2dB) and plot the signal amplitude shown in the plotvalues window (Peak Max). 

Wait min. 8s between the acquirements for the signal to relax (full T1 relaxation).

Parameters:
- Sample: Water without 3D printed sample
- Sequence: Spectrum - Spin Echo
- 90° Ref. Pulselength = 100us
- TE = 12ms
- Sampling Time TS = 6ms
- Averaging off
- all Shims = 0mA
- RF Frequency = LARMOR frequency

Plot the signal amplitude over RF attenuation and explain the signal behaviour.

>*Explanation: 
A Spin Echo sequence uses two RF pulses with a certain ampliutude (flip pulse) and a doubled amplitude (inversion). 
Ideal would be a 90°/180° pulse combination to achieve maximum transverse magnetization.
The RF attenuation will scale both pulses up or down. 
At high attenuation the pulses will be like 1°/2°, 5°/10°, 10°/20°, 20°/40° and so on.
Therefore, weak signals are to be expected, which increase with lower attenuation.
The first signal maximum is at 90°/180°. 
With even smaller attenuations RF pulses will grow to 100°/200°, 120°/240°, 140°/280° and so on.
A first signal minimum is expected at 180°/360° and a second maximum at 270°/540°.
The ideal RF attenuation is the first signal maximum (90°/180°).*

RF Attenuation: _____________________dB

### 3.ii Automatic transmit adjust

Try the transmit adjust (TrAdj) tool (main window - Tools) and compare your results.

- Start Attenuation = -31dB
- Stop Attenuation = -1dB
- Steps = 30

Parameters: 
- Sequence: Spectrum - Spin Echo
- Sample: Water without 3D printed sample
- 90° Ref. Pulselength = 100us
- TE = 12ms
- TR = 500ms
- Sampling Time TS = 6ms
- Averaging off
- all Shims = 0mA
- RF Frequency = LARMOR frequency

100us TrAdj Attenuation:___________________dB

Try 90° Ref. Pulselength = 40us and 200us with the TrAdj Tool and compare the results.

40us TrAdj Attenuation:___________________dB

200us TrAdj Attenuation:___________________dB

Explain the optimal RF attenuation behaviour.

>*Explanation:
The flip angle is determent by the RF pulse energy.
The energy is the product of RF pulse length and amplitude.
Shorter pulses require higher amplitudes, therefore the attenuation is smaller.
Longer pulses require lower amplitudes, therefore the attenuation is higher.*

Set the 90° Ref. Pulselength back to 100us and set the RF Attenuation to the 100us TrAdj attenuation.

## 4 Shimming of the B0 field

Shimming will increase the signal amplitude by applying DC currents (gradient offsets) to the gradient coils. 
This will eliminate field inhomogeneities in the B0 field.

### 4.i Manual shimming

Open the parameters window and make sure all Shim values are set to 0.

Acquire a Spin echo spectrum.

Parameters:
- Sample: Water without 3D printed sample
- 90° Ref. Pulselength = 100us
- TE = 12ms
- TR = 500ms
- Sampling Time TS = 10ms
- Averaging off
- RF Frequency = LARMOR frequency
- RF Attenuation = From transmit adjust (90°/180°)

Signal - without shim (plotvalues window (Peak Max)):___________________

Try to set a shim in one direction (like Shim X) to 20mA.

Reacquire a spectrum and compare the signal (wait min. 8s between the acquirements for the signal to relax (full T1 relaxation)).

If the signal is better the shim is in the right direction, otherwise try -20mA. 

The maximum shim range is ±500mA. 

Recenter the RF frequency for acquirements if necessary.

Try different shims in 20mA steps till you find an optimum for one axis (highest possible signal).

Axis:___ Shim:___________________mA

### 4.ii Automatic shimming

To automate the process, you can use the Shim Tool (main window - Tools).

Set a range from like -400mA to 400mA in 20 steps and select an axis. Look at the resulting plot and find the optimum.

Set the range from (optimum - 50mA) to (optimum + 50mA) in 20 steps and repeat the measurement. Look at the resulting plot and find the finer optimum.

When the top of the plottet bell curve is cut off increase the frequency resolution (set the Sampling Time TS to 20ms).

The optimum shim value is the center of the bell curve, not a single local maximum. 

Enter the shim value for the axis in the parameter window.

Repeat the shimming for all axes (use the previous found shim values for the ohter axes).

As the axes will influence each other repeat the shimming for each axis at least one time.

Iterate all shims to their optimum with about 2mA of deviation. 

Sometimes the shim will shift the center frequency, recenter the RF Frequency if necessary.

Shim X:___________________mA

Shim Y:___________________mA

Shim Z:___________________mA

Shim Z²:___________________mA

Compare the shimmed signal to the reference signal (use the same spetrum parameters).

Signal - with shim (plot window (Peak Max)):___________________

## 5 Adjusting the gradients

To test the gradient channels projections will use each individual gradient channel to acquire a 1D modulated spectrum. 
To acheive a desired field of view (FOV) the gradient current needs to be scaled.

### 5.i Testing the gradients

Make sure the carrier frequency is centered (Spectrum - Spin Echo)

Click on Projections and select the Spin Echo (On Axis) sequence.

Click on parameters, under Projections select X, Y and Z.

Enter the following parameters.

Parameters: 
- Sample: Water without 3D printed sample
- TE = 12ms
- TR = 2000ms
- Sampling Time TS = 3ms
- Image resolution = 128
- Field Of View (FOV) = 12mm

Click on Acquire and wait till the Thonny log states ‘Projection(s) acquired!’.

Click on Data Process.

The Signals should be shown in the plot and explain them.

>*Explanation:
All three axes should show a broad spectrum from the gradients modulations. The form appears like the one dimensional shadow of the sample along the projection axis. The watersample in the chemical test tube has a cylindrical shape. So the two axis along the cross section of the chemical test tube (Z and X) should show a round modulation while the axis along the length of the chemical test tub should show a rectengular modulation.*

If a axis looks like a narrow spectrum peak (no modualtion) the gradient channel of this axis is faulty.

### 5.ii Gradient scaling

Make sure the carrier frequency is centered (Spectrum - Spin Echo)

Use the 3D printed stepped cone sample (2mm steps)

Parameters: 
- TE = 10ms
- TR = 4000ms
- Sampling Time TS = 2ms
- Image resolution = 64
- Field Of View (FOV) = 14mm
- Image Orientation = ZX

Use the Gradient Scaling tool (main window - Tools).

You can measure the 3D printed sample diameter with a caliper (8.3mm).

The caliper diameter is the Nominal value. 

Click on Test Image (SE) and wait till the plot appears.

Explain what you see in the MR image and where tho measure the sample.

>*Explanation:
You should see a bright center surrounded by a dark area and a bright outer ring. The inner area of ​​brightness is the cone. Because there is more water in the center of the cone, the inside is lighter than the outside. The surrounding dark area is the 3D printed sample displacing the water. The outer ring is the water between the 3D printed sample and the glass of the chemical test tube. The sample is measured at the outside diameter of the dark area.*

Use the ruler (grid) in the MR image to measure the diameter of the sample (thick lines: 1mm, thin lines: 0.2mm).

The MR image diameter ist is the measured value.

Type in the values for the axis (axes are shown in the plotted MR image)

A new Scaling value is then calculated. 

When sure apply the scaling value (click on Apply * Scaling).

Do this for the Z and X axis.

Repeat the test image with the new scaling factors and check the MR image again.

Repeat the scaling if necessary.

To scale the Y axis set a new image orientation.

Parameters: 
- TE = 10ms
- TR = 4000ms
- Sampling Time TS = 2ms
- Image resolution = 64
- Field Of View (FOV) = 20mm
- Image Orientation = XY

Explain what you see in the MR image and where tho measure the sample.

>*Explanation:
The bright center area has the shape of the stepped cone. Each step is 2mm. The visible coners of the steps determent the total measureable length.*

Scale the Y axis.

Repeat the test image with the new scaling factors and check the MR image again.

Repeat the scaling if necessary.

## 6 Parameters for spectroscopy and imaging

### 6.i Spectroscopy

Make sure:
- Carrier frequency is centered.

#### 6.i.a Free Induction Decay (FID)

Parameters:
- Sample: Water without 3D printed sample
- TE = 1ms
- Sampling Time TS = 10ms

#### 6.i.b Spin Echo (SE)

Parameters:
- Sample: Water without 3D printed sample
- TE = 12ms
- Sampling Time TS = 10ms

### 6.ii Imaging

Make sure:
- Carrier frequency is centered.

Help:
- Images are distorted: Increase gradients by decreasing Sampling Time TS
- GPA goes in error (red LED on an channel): Decrease the gradients by increasing the Sampling Time TS

#### 6.ii.a 2D Gradient Echo (GRE)

Parameters: 
- TE = 1ms
- TR = 1000ms
- Sampling Time TS = 3ms
- Image resolution = 128
- Field Of View (FOV) = 12mm
- Image Orientation = ZX

#### 6.ii.b 2D Spin Echo (SE)

Parameters: 
- TE = 10ms
- TR = 1000ms
- Sampling Time TS = 3ms
- Image resolution = 128
- Field Of View (FOV) = 12mm
- Image Orientation = ZX