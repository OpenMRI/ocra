
% j = -256:255;
j = -128:127;
RF_amp = 7*2300*2;
n0 = 48;
pulse = 96*RF_amp.*(0.54 + 0.46.*(cos((pi.*j)./(2*n0)) )) .* sin((pi.*j)./(n0))./(pi.*j); 
% pulse = amp * (0.54 + 0.46*(cos((pi*j)/(2*128)) * sin((pi*j)/(128))/(pi*j))); 
figure, plot(pulse);



