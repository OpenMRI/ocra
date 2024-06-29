use anyhow::Result;
use log::info;
use clap::Parser;
use clap_num::maybe_hex;
use memmap2::{MmapMut, MmapOptions};

#[derive(Parser, Debug, Clone)]
struct Args {
    /// address
    #[arg(short, long, value_parser=maybe_hex::<usize>)]
    address: usize,

    /// write value
    #[arg(short, long, value_parser=maybe_hex::<u32>)]
    value: Option<u32>,
}

fn read_u32(mmap: &mut MmapMut, offset: usize) -> Result<u32> {
    let res = mmap[offset..offset + 4]
        .try_into()
        .map(u32::from_le_bytes)
        .map_err(|_| anyhow::anyhow!("Failed to read u32 at offset 0x{:x}", offset));
    //info!("Read u32 at offset 0x{:x}: {:?}", offset, res);
    res
}
fn write_u32(mmap: &mut MmapMut, offset: usize, value: u32) -> Result<()> {
    //info!("Write u32 at offset 0x{:x}: {:x}", offset, value);
    mmap[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
    Ok(())
}


fn main() -> Result<()> {
    simple_logger::SimpleLogger::new()
        .with_level(log::LevelFilter::Info)
        .init()
        .unwrap();
    let args: Args = Args::parse();

    let address: usize = args.address;
    let (write, write_value): (bool, u32) = if let Some(value) = args.value {
        (true, value)
    } else {
        (false, 0)
    };

    //file open
    let file = std::fs::OpenOptions::new()
        .read(true)
        .write(true)
        .open("/dev/mem")?;
    let mmap_page_addr = address & 0xfffff000;
    let addr_offset = address & 0xfff;
    //mmap
    let mut pl_mmap: MmapMut = unsafe {
        MmapOptions::new()
            .offset(mmap_page_addr as u64)
            .len(4096)
            .map_mut(&file)?
    };
    let read_val: u32 = read_u32(&mut pl_mmap, addr_offset)?;
    info!("Read  Register {:08x}: {:08x}", address, read_val);

    if write {
        info!("Write Register {:08x}: {:08x}", address, write_value);
        write_u32(&mut pl_mmap, addr_offset, write_value)?;
    }

    Ok(())
}
