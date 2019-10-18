# class of basic parameters
class BasicParameters:
    def __init__(self):
		# TW: These parameters should be from an external "tuneup" parameter file, and it should be possible to save them there,
		#     and not be hardwired in the code here. Alas I'm using values that are typical for the tabletop magnet #26 in my lab
		#     that are a reasonable starting point for its configuration as of 12/14/2018
        self.gradient_offsets = [128, 24, -165, 0]
        # X -119, Y 42, Z 74 , Z2 0 mA

        # central frequency (MHz)
        self.freq = 15.673000

        # initial attenuation (dB)
        self.at = 20

        # initial host address
        self.addr = '172.20.125.186'

    def set_grad_offsets(self, offset_list):
        self.gradient_offsets = offset_list

    def set_grad_offset_x(self, offset_x):
        self.gradient_offsets[0] = offset_x

    def set_grad_offset_y(self, offset_y):
        self.gradient_offsets[1] = offset_y

    def set_grad_offset_z(self, offset_z):
        self.gradient_offsets[2] = offset_z

    def set_grad_offset_z2(self, offset_z2):
        self.gradient_offsets[3] = offset_z2

    def get_grad_offsets(self):
        return self.gradient_offsets

    def get_grad_offset_x(self):
        return self.gradient_offsets[0]

    def get_grad_offset_y(self):
        return self.gradient_offsets[1]

    def get_grad_offset_z(self):
        return self.gradient_offsets[2]

    def get_grad_offset_z2(self):
        return self.gradient_offsets[3]

    def set_freq(self, value):
        self.freq = value

    def get_freq(self):
        return self.freq

    def set_at(self, value):
        # Round attenuation to nearest 0.25
        self.at = value

    def get_at(self):
        return self.at

    def set_hostaddr(self, str):
        self.addr = str

    def get_hostaddr(self):
        return self.addr

# record basic parameters
parameters = BasicParameters()
