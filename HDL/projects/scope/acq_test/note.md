## memory allocation:
- reserved region: 0x1000_0000 with 0x100_0000 size
- double buffer-> split in half - 0x80_0000 per each TR
- split in four windows - 0x20_0000 per each window.
- with 8B word size, 0x20_0000/8 = 0x40000 words per window (262144)
- 262144 words with 64 decimation rate: longest window is ~0.134217728 second (134 milliseconds)
-> DMA Max Transfer per request: 8388607 B -> 1048575 words. This is longer than the max needed (262144 words).

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





