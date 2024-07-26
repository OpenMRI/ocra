use std::fs::{File, OpenOptions};
use std::ptr;
use memmap2::{MmapMut, MmapOptions};
use anyhow::Result;
use std::{time, thread};
use std::io::{Read, Write, Seek, SeekFrom};

struct MemoryMap {
    map: MmapMut,
    size: usize,
}
impl MemoryMap {
    pub fn new(file: &File, base_addr: usize, size: usize) -> Result<Self> {
        let map: MmapMut = unsafe {
            MmapOptions::new()
                .offset(base_addr as u64)
                .len(size)
                .map_mut(file)
                .unwrap()
        };
        Ok(MemoryMap {
            map: map,
            size: size,
        })
    }
    fn validate_offset(&self, offset: usize) -> Result<()> {
        if offset >= self.size {
            Err(anyhow::anyhow!("Offset out of bounds"))
        } else {
            Ok(())
        }
    }
    pub fn write(&mut self, offset: usize, data: u32) -> Result<()> {
        self.validate_offset(offset)?;
        unsafe {ptr::write_volatile(self.map[offset..offset+4].as_mut_ptr() as *mut u32, data) };
        Ok(())
    }
    pub fn read(&mut self, offset: usize) -> Result<u32> {
        let readback_data: u32 = unsafe {ptr::read_volatile(self.map[offset..offset+4].as_mut_ptr() as *mut u32) };
        Ok(readback_data)
    }
}
struct DmaController {
    mmap: MemoryMap,
    irq_file: Option<File>,
}
impl DmaController {
    const SOFT_RESET_OFFSET: usize = 0x0;
    const BUFFER_WRITTEN_FLAGS_OFFSET: usize = 0x4;
    const CONFIGURE_BUFFER_COUNT_OFFSET: usize = 0x18;
    const CONFIGURE_BUFFER_ADDRESS_OFFSET: usize = 0x20;

    pub fn new(file: &File, base_addr: usize, size: usize) -> Result<Self> {
        let mmap: MemoryMap = MemoryMap::new(file, base_addr, size)?;
        Ok(DmaController {
            mmap: mmap,
            irq_file: None,
        })
    }
    pub fn configure_interrupt_file(&mut self, file: File) {
        self.irq_file = Some(file);
    }
    pub fn wait_for_completion(&mut self) -> Result<()> {
        let mut buf = [0u8; 4];
        self.irq_file.as_mut().unwrap().read_exact(&mut buf)?;
        self.irq_file.as_mut().unwrap().seek(SeekFrom::Start(0))?;
        self.irq_file.as_mut().unwrap().write(&1u32.to_le_bytes()).unwrap();
        Ok(())
    }
    pub fn soft_reset(&mut self) -> Result<()> {
        let _ = self.mmap.write(Self::SOFT_RESET_OFFSET, 0x1);
        self.mmap.write(Self::SOFT_RESET_OFFSET, 0x0)
    }
    pub fn configure_buffer_count(&mut self, value: u32) -> Result<()> {
        self.mmap.write(Self::CONFIGURE_BUFFER_COUNT_OFFSET, value)
    }
    pub fn configure_buffer_address(&mut self, idx: usize, value: u32) -> Result<()> {
        self.mmap.write(Self::CONFIGURE_BUFFER_ADDRESS_OFFSET + (4*idx), value)
    }
    pub fn read_status(&mut self) -> Result<()> {
        let bitmask = self.mmap.read(Self::BUFFER_WRITTEN_FLAGS_OFFSET)?;
        println!("Buffer written flags: 0x{:08x}", bitmask);
        //Clear flags
        let _ = self.mmap.write(Self::BUFFER_WRITTEN_FLAGS_OFFSET, 0x0);
        for i in (0x8..0x21).step_by(4) {
            let result = self.mmap.read(i)?;
            println!("0x{:08x}: 0x{:08x}", i, result);
        }
        Ok(())
    }
}

struct ConfigController {
    mmap: MemoryMap,
    irq_file: File,
}
impl ConfigController {
    fn new(file: &File, base_addr: usize, size: usize, irq_file: File) -> Result<Self> {
        let mmap: MemoryMap = MemoryMap::new(file, base_addr, size)?;
        Ok(ConfigController {
            mmap: mmap,
            irq_file: irq_file,
        })
    }
    pub fn wait_for_completion(&mut self) -> Result<()> {
        let mut buf = [0u8; 4];
        self.irq_file.read_exact(&mut buf)?;
        //re enable
        self.irq_file.seek(SeekFrom::Start(0))?;
        self.irq_file.write(&1u32.to_le_bytes())?;
        Ok(())
    }
    pub fn unmask_gate(&mut self) -> Result<()> {
        self.mmap.write(0x14, 0x1)
    }
    pub fn mask_gate(&mut self) -> Result<()> {
        self.mmap.write(0x14, 0x0)
    }
    pub fn cic_rate(&mut self, rate: u16) -> Result<()> {
        self.mmap.write(0x8, rate as u32)
    }
    pub fn nco_rate(&mut self, rate: u32) -> Result<()> {
        self.mmap.write(0x4, rate)
    }
}

struct AcqController {
    mmap: MemoryMap,
}
impl AcqController {
    fn new(file: &File, base_addr: usize, size: usize) -> Result<Self> {
        let mmap: MemoryMap = MemoryMap::new(file, base_addr, size)?;
        Ok(AcqController {
            mmap: mmap,
        })
    }
    pub fn soft_reset(&mut self) -> Result<()> {
        self.mmap.write(0x20, 0x1)?;
        self.mmap.write(0x20, 0x0)
    }
    pub fn configure_ds(&mut self, values: [u32;4]) -> Result<()> {
        self.mmap.write(0x4, values[0])?;
        self.mmap.write(0xC, values[1])?;
        self.mmap.write(0x14, values[2])?;
        self.mmap.write(0x1C, values[3])
    }
    pub fn configure_ws(&mut self, values: [u32;4]) -> Result<()> {
        self.mmap.write(0x0, values[0])?;
        self.mmap.write(0x8, values[1])?;
        self.mmap.write(0x10, values[2])?;
        self.mmap.write(0x18, values[3])
    }
    pub fn read_status(&mut self) -> Result<()> {
        let result = self.mmap.read(0x24)?;
        println!("Status: 0x{:08x}", result);
        Ok(())
    }
}

struct MemoryController {
    mmap: MemoryMap,
}
impl MemoryController {
    fn new(file: &File, base_addr: usize, size: usize) -> Result<Self> {
        let mmap: MemoryMap = MemoryMap::new(file, base_addr, size)?;
        Ok(MemoryController {
            mmap: mmap,
        })
    }
    pub fn read_memory(&mut self, offset: usize, length: usize) -> Result<()> {
        println!("Printing memory. Starting offset {:08x} with length {:08x}", offset, length);
        for i in (offset..offset+length).step_by(8) {
            let result_l = self.mmap.read(i)?;
            let result_h = self.mmap.read(i+4)?;
            println!("ADDR 0x{:08x} - 0x{:08x}: 0x{:08x}{:08x}", i+4, i, result_h, result_l);
            let _ = self.mmap.write(i, 0x0);
            let _ = self.mmap.write(i+4, 0x0);
        }
        Ok(())
    }
}
struct SlcrController {
    mmap: MemoryMap,
}
impl SlcrController {
    fn new(file: &File, base_addr: usize, size: usize) -> Result<Self> {
        let mmap: MemoryMap = MemoryMap::new(file, base_addr, size)?;
        Ok(SlcrController {
            mmap: mmap,
        })
    }
    pub fn initialize(&mut self) -> Result<()> {
        let _ = self.mmap.write(0x8, 0xDF0D)?;
        let x = (self.mmap.read(92*4)? & !0x03F03F30u32) | 0x00100700u32;
        self.mmap.write(92*4, x)
    }
}

fn main() {
    println!("Hello, world!");
    const SCLR_BASE_ADDR: usize = 0xF8000000;
    const DMA_RX_BASE_ADDR: usize = 0x60000000;
    const ACQ_BASE_ADDR: usize = 0x40060000;
    const CFG_BASE_ADDR: usize = 0x40000000;
    const SCLR_SIZE: usize = 4096;
    const DMA_RX_SIZE: usize = 4096;
    const CFG_SIZE: usize = 4096;
    const ACQ_SIZE: usize = 4096;

    //Zynq-RAM Target
    const RAM_BASE_ADDR: usize = 0x10000000; //Zynq Memory
    const RAM_SIZE: usize = 0x100_0000; //16MB
    const TOTAL_TARGET_SIZE: usize = RAM_SIZE/8;
    const BUFFER_COUNT: usize = 8;
    const TRANSFER_SIZE: usize = TOTAL_TARGET_SIZE/BUFFER_COUNT;
    const WSIZE: u32 = 100; //in words
    const READ_SIZE: usize = 8*(WSIZE as usize); //in bytes

    let file: File = OpenOptions::new()
                           .read(true)
                           .write(true)
                           .open("/dev/mem".to_string())
                           .unwrap();
    let trstart_file: File = OpenOptions::new()
                           .read(true)
                           .write(true)
                           .open("/dev/uio0".to_string())
                           .unwrap();
    //sclr initialization
    let mut slcr_ctrl: SlcrController = SlcrController::new(&file, SCLR_BASE_ADDR, SCLR_SIZE).unwrap();
    let _ = slcr_ctrl.initialize();

    //all the other controllers
    let mut dma_ctrl: DmaController = DmaController::new(&file, DMA_RX_BASE_ADDR, DMA_RX_SIZE).unwrap();
    let mut cfg_ctrl: ConfigController = ConfigController::new(&file, CFG_BASE_ADDR, CFG_SIZE, trstart_file).unwrap();
    let mut ram_ctrl: MemoryController = MemoryController::new(&file, RAM_BASE_ADDR, RAM_SIZE).unwrap();
    let mut acq_ctrl: AcqController = AcqController::new(&file, ACQ_BASE_ADDR, ACQ_SIZE).unwrap();
    let irq_file: File = OpenOptions::new()
                           .read(true)
                           .write(true)
                           .open("/dev/uio3".to_string())
                           .unwrap();
    let _ = dma_ctrl.configure_interrupt_file(irq_file);

    //reset the dma controller
    println!("Resetting the DMA controller");
    let _ = dma_ctrl.soft_reset();

    /*
    ## Steps in testing
    - configure CIC decimation to 64
        - config_2[15:0] = 0x4000_0008
    - soft reset acq trigger core = 0x4006_0020 bit 0.
    - configure acq trigger with 4 windows
        - 0x4006_0004: d0 = 1000 (~0.5 ms)
        - 0x4006_0000: w0 = 3000 (~1.5 ms)
        - w1, w2, w3 = 0.
    - soft reset rx dma core
    - configure rx dma:
        - 0x18- buffer to be used: 8
        - 0x20- buffer 0 address: 0x1000_0000
        - 0x24- buffer 1 address: 0x1020_0000
        - 0x28- buffer 2 address: 0x1040_0000
        - 0x2C- buffer 3 address: 0x1060_0000
        - 0x30- buffer 4 address: 0x1080_0000
        - 0x34- buffer 5 address: 0x10a0_0000
        - 0x38- buffer 6 address: 0x10c0_0000
        - 0x3C- buffer 7 address: 0x10e0_0000
    - unmask gate
        - config_5[0] = 0x4000_0014
    - wait for starttr irq
        - mask gate
    - wait for dma_rx irq
    - print out the status register on dma rx
    - print out the status register on acq trigger
    */


    //configure CIC decimation to 64
    println!("Configuring CIC decimation to 64");
    let _ = cfg_ctrl.cic_rate(64);
    let _ = cfg_ctrl.nco_rate(0x14f8bu32);

    //soft reset acq trigger core
    println!("Soft reset acq trigger core");
    let _ = acq_ctrl.soft_reset();

    //configure acq trigger with 4 windows
    println!("Configuring acq trigger with 4 windows");
    let _ = acq_ctrl.configure_ds([500, 500, 500, 500]);
    let _ = acq_ctrl.configure_ws([WSIZE, WSIZE, WSIZE, WSIZE]);

    //reset the dma controller
    println!("Resetting the DMA controller");
    let _ = dma_ctrl.soft_reset();

    //set up buffers
    println!("Configuring the DMA controller");
    let _ = dma_ctrl.configure_buffer_count(BUFFER_COUNT as u32);
    for i in 0..BUFFER_COUNT {
        let _ = dma_ctrl.configure_buffer_address(i, (RAM_BASE_ADDR + i*8*TRANSFER_SIZE).try_into().unwrap());
    }

    //unmask gate
    println!("Unmasking the gate");
    let _ = cfg_ctrl.unmask_gate();

    //wait for starttr irq
    println!("Waiting for starttr irq");
    let _ = cfg_ctrl.wait_for_completion();

    //wait for dma_rx irq
    println!("Waiting for dma_rx irq");
    for _i in 0..4 {
        let _ = dma_ctrl.wait_for_completion();
    }
    //wait for starttr irq
    println!("Waiting for starttr irq");
    let _ = cfg_ctrl.wait_for_completion();
    //mask gate
    println!("Masking the gate");
    let _ = cfg_ctrl.mask_gate();
  
    //wait for dma_rx irq
    println!("Waiting for dma_rx irq");
    for _i in 0..4 {
        let _ = dma_ctrl.wait_for_completion();
    }

    //Read the status
    println!("Reading the status");
    let _ = dma_ctrl.read_status();
    let _ = acq_ctrl.read_status();

    //Read the memory
    println!("Reading the memory");
    for i in 0..BUFFER_COUNT {
        println!("===================== Buffer {:?} ==========================", i);
        let _ = ram_ctrl.read_memory(i*8*TRANSFER_SIZE, READ_SIZE+8);
    }
}