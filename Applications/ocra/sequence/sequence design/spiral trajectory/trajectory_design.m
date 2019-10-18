%%%
%%% 这里我声明一下，我的kx和ky值的计算，直接就是梯度的积分，
%%% 不乘任何常数，所以Cartesian和Spiral是对等的！！！

pe_step = 2.936/44.53/2;
k_range = 800.0 * pe_step * 64.0;   % phase encoding 等效时长为 800 us
k_step = 800.0 * pe_step;           % 800 us

kx_unit = -31 * k_step : k_step : k_step*32;
ky_unit = kx_unit;

kx = [];
ky = [];
for i = 1:64
    if mod(i,2)
        kx = [kx, kx_unit];
    else
        kx = [kx, flip(kx_unit)];
    end
    ky = [ky, repmat(ky_unit(i),1,64)];
end

a0 = k_step/2/3.14159;
%2.936/44.53/2/2/3.14159*500;
w0 = 0.01;%10000;
t = 0:10:10*2000; % 2000*10 us
% t = 0:0.000010:0.02; % 2000*10 us

kx_spiral = a0 .* w0 .* t .* cos(w0 .* t);
ky_spiral = a0 .* w0 .* t .* sin(w0 .* t);

figure,
plot(kx,ky);
% hold on;
figure,
plot(kx_spiral,ky_spiral);

figure,
plot(kx,ky,'x');
hold on;
plot(kx_spiral,ky_spiral,'r+');

% Gradient
Gx = a0 .* w0 .* (cos(w0 .* t) - w0 .* t .* sin(w0 .* t));
Gy = a0 .* w0 .* (sin(w0 .* t) + w0 .* t .* cos(w0 .* t));
% Gx = a0 .* w0 .* cos(w0 .* t) - a0 .* w0 .* w0 .* t .* sin(w0 .* t);
% Gy = a0 .* w0 .* sin(w0 .* t) + a0 .* w0 .* w0 .* t .* cos(w0 .* t);
figure();
plot(Gx,Gy);

figure,
plot(t,Gx,'r');
hold on,
plot(t,Gy,'b');
