import fcntl, mmap, os, time

SLCR_BASE_ADDR   = 0xF8000000
DMA_RX_ADDR = 0x40010000
CFG_ADDR = 0x40000000
BRAM_ADDR = 0x42000000

def write_reg(mm, base_addr, val):
    val_list = list()
    for i in range(4):
        byte_val = (val >> (i*8)) & 0xFF
        val_list.append(byte_val)
    mm[base_addr:base_addr+4] = bytes(val_list)

def read_reg(mm, base_addr):
    res = 0
    for i in range(4):
        res += (mm[base_addr+i]) << (i*8)
    return res

def configure_samples(mm, num_samples):
    write_reg(mm, 0x14, num_samples)

def configure_buffer_count(mm, count):
    write_reg(mm, 0x18, count)

def configure_buffer_address(mm, idx, addr):
    write_reg(mm, 0x20 + (idx*4), addr)

def soft_reset(mm):
    write_reg(mm, 0x0, 0x1)
    write_reg(mm, 0x0, 0x0)

def trigger_gate(mm, curr_val):
    curr_val ^= 0x1
    write_reg(mm, 0x0, curr_val)
    return curr_val

def read_status(mm):
    result = read_reg(mm, 0x4)
    print("Bitmask: 0x%x"%result)
    write_reg(mm, 0x4, 0x0) #clear flags
    for i in range(0x8, 0x21, 0x4):
        result = read_reg(mm, i)
        print("0x%02x - 0x%x"%(i,result))

def read_bram(mm, address_offset, sample_len):
    for i in range(address_offset, address_offset+8*sample_len, 0x8):
        resultl = read_reg(mm, i)
        resulth = read_reg(mm, (i+4))
        print("Addr (%08x - %08x) - 0x%08x%08x"%(i+4, i, resulth, resultl))
        #zero out to make reading easier after
        write_reg(mm,i,0)
        write_reg(mm,i+4,0)

def main():
    '''
    - perform necessary pl initialization.
    - perform transfers to bram target.
    - read out bram entries.
    '''
    trig_val = 0
    #Initialization
    fd = os.open("/dev/mem", os.O_RDWR)
    if fd<0:
        print("can't open dev mem")
        exit()
    slcr = mmap.mmap(fd, os.sysconf("SC_PAGE_SIZE"), prot=mmap.PROT_READ|mmap.PROT_WRITE, flags=mmap.MAP_SHARED, offset=SLCR_BASE_ADDR)
    write_reg(slcr, 2*4, 0xdf0d)
    write_reg(slcr, 92*4, (read_reg(slcr, 92*4) & ~0x03F03F30) | 0x00100700) #7ns
    slcr.close()
    print("SLCR Init Done")

    #mmap the posedge measurement core
    dma_rx_reg = mmap.mmap(fd, os.sysconf("SC_PAGE_SIZE"), prot=mmap.PROT_READ|mmap.PROT_WRITE, flags=mmap.MAP_SHARED, offset=DMA_RX_ADDR)
    cfg_reg = mmap.mmap(fd, os.sysconf("SC_PAGE_SIZE"), prot=mmap.PROT_READ|mmap.PROT_WRITE, flags=mmap.MAP_SHARED, offset=CFG_ADDR)
    #uio0
    fd_uio = os.open('/dev/uio0', os.O_SYNC | os.O_RDWR)

    #soft reset
    print("soft reset")
    soft_reset(dma_rx_reg)

    #set up buffers
    print("configure")
    configure_samples(dma_rx_reg, 128)
    configure_buffer_count(dma_rx_reg, 8)
    for i in range(8):
        configure_buffer_address(dma_rx_reg, i, BRAM_ADDR + (i*0x400))
  
    #8 buffer transfers!
    for i in range(8):
        #enable interrupt
        print("enable interrupt")
        os.write(fd_uio, bytes([0,0,0,1]))

        #gate
        print("trigger gate")
        trig_val = trigger_gate(cfg_reg, trig_val)

        #wait for interrupt
        os.read(fd_uio, 4)

    #read result
    read_status(dma_rx_reg)
    bram = mmap.mmap(fd, 2*os.sysconf("SC_PAGE_SIZE"), prot=mmap.PROT_READ|mmap.PROT_WRITE, flags=mmap.MAP_SHARED, offset=BRAM_ADDR)
    for i in range(8):
        print("===================== Buffer %i =========================="%i) 
        read_bram(bram, i*0x400, 128)
    bram.close()

    dma_rx_reg.close()
    cfg_reg.close()
    os.close(fd)
    
if __name__=="__main__":
    print(main.__doc__)
    main() 
