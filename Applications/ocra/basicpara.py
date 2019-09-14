# class of basic parameters
class BasicParameters:
    def __init__(self):
		# TW: These parameters should be from an external "tuneup" parameter file, and it should be possible to save them there,
		#     and not be hardwired in the code here. Alas I'm using values that are typical for the tabletop magnet #26 in my lab
		#     that are a reasonable starting point for its configuration as of 12/14/2018
        self.gradient_offsets = [117, 35, 33]
        # X -119, Y 42, Z 74 mA

        # central frequency (MHz)
        self.freq = 15.673000

    def set_grad_offsets(self, offset_list):
        self.gradient_offsets = offset_list

    def set_grad_offset_x(self, offset_x):
        self.gradient_offsets[0] = offset_x

    def set_grad_offset_y(self, offset_y):
        self.gradient_offsets[1] = offset_y

    def set_grad_offset_z(self, offset_z):
        self.gradient_offsets[2] = offset_z

    def get_grad_offsets(self):
        return self.gradient_offsets

    def get_grad_offset_x(self):
        return self.gradient_offsets[0]

    def get_grad_offset_y(self):
        return self.gradient_offsets[1]

    def get_grad_offset_z(self):
        return self.gradient_offsets[2]

    def set_freq(self, value):
        self.freq = value

    def get_freq(self):
        return self.freq

# record basic parameters
parameters = BasicParameters()