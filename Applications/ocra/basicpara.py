# class of basic parameters
class BasicParameters:
    def __init__(self):
        # gradient offsets
        # self.gradient_offsets =  [120, 45, -92]
        # self.gradient_offsets =  [-120, 45, 92]
        self.gradient_offsets = [-119, 42, 74]
        # X -119, Y 42, Z 74 mA

        # central frequency
        self.freq = 15.670000

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