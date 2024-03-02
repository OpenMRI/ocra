use std::fs::{File, OpenOptions};
use std::ptr;
use memmap2::{MmapMut, MmapOptions};
use anyhow::Result;
use std::{time, thread};

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
    irq_count: u32,
}
impl DmaController {
    const SOFT_RESET_OFFSET: usize = 0x0;
    const BUFFER_WRITTEN_FLAGS_OFFSET: usize = 0x4;
    const CONFIGURE_SAMPLING_OFFSET: usize = 0x14;
    const CONFIGURE_BUFFER_COUNT_OFFSET: usize = 0x18;
    const IRQ_COUNT_OFFSET: usize = 0x1C;
    const CONFIGURE_BUFFER_ADDRESS_OFFSET: usize = 0x20;

    pub fn new(file: &File, base_addr: usize, size: usize) -> Result<Self> {
        let mmap: MemoryMap = MemoryMap::new(file, base_addr, size)?;
        Ok(DmaController {
            mmap: mmap,
            irq_count: 0,
        })
    }
    pub fn update_irq_count(&mut self) -> Result<()> {
        self.irq_count = self.mmap.read(Self::IRQ_COUNT_OFFSET)?;
        println!("IRQ Count: 0x{:08x}", self.irq_count);
        Ok(())
    }
    pub fn wait_for_completion(&mut self) -> Result<()> {
        loop {
            let current_irq_count = self.mmap.read(Self::IRQ_COUNT_OFFSET)?;
            if self.irq_count != current_irq_count {
                break;
            }
            thread::sleep(time::Duration::from_micros(1));
        }
        Ok(())
    }
    pub fn soft_reset(&mut self) -> Result<()> {
        let _ = self.mmap.write(Self::SOFT_RESET_OFFSET, 0x1);
        self.mmap.write(Self::SOFT_RESET_OFFSET, 0x0)
    }
    pub fn configure_sampling(&mut self, value: u32) -> Result<()> {
        self.mmap.write(Self::CONFIGURE_SAMPLING_OFFSET, value)
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
}
impl ConfigController {
    fn new(file: &File, base_addr: usize, size: usize) -> Result<Self> {
        let mmap: MemoryMap = MemoryMap::new(file, base_addr, size)?;
        Ok(ConfigController {
            mmap: mmap,
        })
    }
    fn trigger_gate(&mut self) -> Result<()> {
        let curr_value = self.mmap.read(0x0)?;
        self.mmap.write(0x0, curr_value ^ 0x1)
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
    const DMA_RX_BASE_ADDR: usize = 0x40010000;
    const CFG_BASE_ADDR: usize = 0x40000000;
    const SCLR_SIZE: usize = 4096;
    const DMA_RX_SIZE: usize = 4096;
    const CFG_SIZE: usize = 4096;

    //BRAM Target
    //const RAM_BASE_ADDR: usize = 0x42000000; //BRAM
    //const TOTAL_TARGET_SIZE: usize = 8*128; //of 8B words
    //const RAM_SIZE: usize = TOTAL_TARGET_SIZE*8;
    //const BUFFER_COUNT: usize = 1;
    //const TRANSFER_SIZE: usize = TOTAL_TARGET_SIZE/BUFFER_COUNT;
    
    //Zynq-RAM Target
    const RAM_BASE_ADDR: usize = 0x10000000; //Zynq Memory
    const TOTAL_TARGET_SIZE: usize = 4096*4/8; //of 8B words - four 4kB pages for testing
    const RAM_SIZE: usize = TOTAL_TARGET_SIZE*8;
    const BUFFER_COUNT: usize = 1;
    const TRANSFER_SIZE: usize = TOTAL_TARGET_SIZE/BUFFER_COUNT;

    let file: File = OpenOptions::new()
                           .read(true)
                           .write(true)
                           .open("/dev/mem".to_string())
                           .unwrap();

    //sclr initialization
    let mut slcr_ctrl: SlcrController = SlcrController::new(&file, SCLR_BASE_ADDR, SCLR_SIZE).unwrap();
    let _ = slcr_ctrl.initialize();

    //all the other controllers
    let mut dma_ctrl: DmaController = DmaController::new(&file, DMA_RX_BASE_ADDR, DMA_RX_SIZE).unwrap();
    let mut cfg_ctrl: ConfigController = ConfigController::new(&file, CFG_BASE_ADDR, CFG_SIZE).unwrap();
    let mut ram_ctrl: MemoryController = MemoryController::new(&file, RAM_BASE_ADDR, RAM_SIZE).unwrap();

    //reset the dma controller
    println!("Resetting the DMA controller");
    let _ = dma_ctrl.soft_reset();

    //set up buffers
    println!("Configuring the DMA controller");
    let _ = dma_ctrl.configure_sampling(TRANSFER_SIZE as u32);
    let _ = dma_ctrl.configure_buffer_count(BUFFER_COUNT as u32);
    for i in 0..BUFFER_COUNT {
        let _ = dma_ctrl.configure_buffer_address(i, (RAM_BASE_ADDR + i*8*TRANSFER_SIZE).try_into().unwrap());
    }

    //Starting the Data Transfer
    for i in 0..BUFFER_COUNT {
        println!("Starting the Data Transfer {:?}", i);
        let _ = dma_ctrl.update_irq_count();
        println!("Triggering the gate");
        let _ = cfg_ctrl.trigger_gate();
        println!("Waiting for completion");
        let _ = dma_ctrl.wait_for_completion();
    }

    //Read the status
    println!("Reading the status");
    let _ = dma_ctrl.read_status();

    //Read the memory
    println!("Reading the memory");
    for i in 0..BUFFER_COUNT {
        println!("===================== Buffer {:?} ==========================", i);
        let _ = ram_ctrl.read_memory(i*8*TRANSFER_SIZE, 8*TRANSFER_SIZE);
    }
}