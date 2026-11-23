---
title: "Supp G — Firmware: Boot, Update & Debug"
tags:
  - firmware
  - debug
  - nvme
  - testing
source_anchor: "original — no book chapter"
textbook: v2
---

# Supplement G — Firmware: Boot, Update & Debug

The core chapters describe what a solid-state drive's (SSD's) firmware *does*: map addresses, collect garbage, level wear, survive power loss. This supplement follows the firmware's own life: how it starts at power-on, how a new version replaces it in the field without losing data, what it reports about the drive's health, and how engineers find out why it failed. It ends with the loop that connects all of these: a drive fails at a customer, and a firmware update fixes every other drive like it.

Read [Ch 2 §2.1.2](../core/ch2-controllers-afa.md#212-controller-cpu-cpu) for the controller hardware and [Supplement F §F.5](f-security.md#f5-secure-boot-and-signed-firmware) for how signatures keep unapproved firmware out; this supplement builds on both.

!!! abstract "In this supplement"
    - **What the firmware is** — tasks, cores and the images stored on the drive (§G.1)
    - **Boot** ⭐⭐ — from power-on to "ready", and why the map decides how long it takes (§G.2)
    - **Updating in the field** ⭐⭐ — Firmware Image Download, Firmware Commit, slots and power-loss safety (§G.3)
    - **Health and logs** ⭐ — SMART, the error and persistent event logs, telemetry (§G.4)
    - **Debugging** — consoles, debug ports, asserts and crash dumps (§G.5)
    - **Factory to field** — manufacturing steps and the field-return loop (§G.6)

    Short on time? §G.2 and §G.3 carry the most.

---

## G.1 What the firmware is

An SSD controller is a small computer with several processor cores, typically real-time cores of the Arm Cortex-R family, plus hardware accelerators ([Ch 2 §2.1.2](../core/ch2-controllers-afa.md#212-controller-cpu-cpu)). The firmware divides its work among them, commonly along the controller's three parts:

- **the front end**: the host interface, fetching commands from the host's queues and posting completions;
- **the flash translation layer (FTL)**: mapping, garbage collection (GC), wear leveling and power-loss recovery ([Chapter 4](../core/ch4-ftl.md));
- **the back end**: driving the flash channels and the error-correcting code (ECC) engine.

It runs without virtual memory, usually on a small real-time operating system or as hand-scheduled loops, and every core is watched by a **watchdog timer** that resets the controller if the code stops making progress. Its code and fast data live in on-chip SRAM (static random-access memory); the mapping table and buffers live in DRAM (dynamic random-access memory) if the drive has it.

The drive stores several pieces of firmware and data, in different places for different reasons:

| Piece | Stored in | Why there |
|---|---|---|
| boot ROM code | the controller's silicon | can't be changed, so it is the root of trust |
| bootloader | a small SPI NOR flash chip, or a fixed NAND area | simple and reliable to read at power-on |
| main firmware image | NAND flash, two or more copies, usually written in fast, robust SLC (single-level cell) mode | large; redundancy survives a bad block |
| configuration and calibration | reserved NAND blocks | per-drive settings, such as read-retry tables tuned at the factory |
| mapping table snapshot | NAND, in the FTL's own blocks | restored at every boot ([Ch 4 §4.6](../core/ch4-ftl.md#46-power-loss-recovery)) |

SPI (Serial Peripheral Interface) NOR flash is a cheap chip that can be read from address 0 with almost no setup, which is exactly what the earliest code needs. ROM here means read-only memory.

## G.2 Boot: from power-on to ready ⭐⭐

When power arrives and the host releases the reset signal, the drive climbs a short ladder:

![Five boot stages: power on, when the reset is released; the boot ROM, in the chip's silicon, which copies the bootloader in and checks it; the bootloader, in SPI NOR flash, which loads the main firmware image and falls back to a second copy if the first is bad; the main firmware, kept in NAND in two copies, which starts the flash channels and restores the map; and ready, when the host's commands begin](../assets/figures/supp-g/boot-sequence.svg){ .sdd-fig }
/// figure-caption
An SSD's boot. Each stage loads and checks the next, every stage has a fallback copy, and the drive reports ready only once its mapping table is usable.
///

1. **Boot ROM.** Fixed code in the controller's silicon loads the bootloader into on-chip memory and verifies its signature ([Supplement F §F.5](f-security.md#f5-secure-boot-and-signed-firmware)). If it can't find a valid bootloader, it falls into a **download mode** that accepts firmware over a serial or test interface: that is how a factory loads a blank drive, and how a lab revives a bricked one.
2. **Bootloader.** It loads the main firmware image from NAND flash and verifies it. If the active copy fails, it tries the other one, so a single bad block or a corrupted copy never stops the drive from starting.
3. **Main firmware.** It brings up the flash interfaces, which includes training the timing of each channel, loads the configuration, and then restores the **mapping table**. After a clean shutdown it loads the last snapshot; after an unclean one it must also rebuild the changes made since, by scanning recently written blocks ([Ch 4 §4.6](../core/ch4-ftl.md#46-power-loss-recovery)).
4. **Ready.** The drive reports ready, on NVMe (Non-Volatile Memory Express) by setting the CSTS.RDY bit, and the host's commands begin.

The host gives the drive a deadline: an NVMe controller advertises in its capabilities register how long it may take to become ready (in units of 500 ms), and the host waits that long before giving up. Restoring the map dominates the time, which is why recovery after a power loss is slower than a clean boot, and why laptops that power the drive off at idle ([Supplement D §D.2](d-power-management.md#d2-pcie-device-power-states)) push firmware toward map formats that can be loaded quickly or in pieces on demand.

## G.3 Updating firmware in the field ⭐⭐

Firmware is updated for real reasons: to fix bugs found after shipping, close security holes, improve performance or add features. On NVMe drives the update is two commands:

- **Firmware Image Download** carries the new image to the drive in pieces, each with an offset and a length, because an image is far larger than one command's data.
- **Firmware Commit** tells the drive what to do with the image: verify it, write it into a numbered **firmware slot**, and activate it, either at the next reset or immediately.

![A firmware update: the host sends the image in pieces with Firmware Image Download; the drive gathers them in a staging buffer and checks the signature; Firmware Commit writes the image into slot 2, while slot 1 keeps a read-only factory image and slot 3 the previous version; the new slot is activated at the next reset, or at once if supported](../assets/figures/supp-g/fw-slots.svg){ .sdd-fig }
/// figure-caption
A firmware update through slots. The new image is checked before it is written, written before it is activated, and the old images stay where they are until the new one has proved itself.
///

**Slots** let a drive hold up to seven images. Slot 1 may be read-only, keeping the factory image as a last resort, and the Firmware Slot Information log reports which slot is active and which version each one holds. The Identify Controller data says how many slots the drive has, whether slot 1 is read-only and whether activation without a reset is supported.

**Power-loss safety** is the design rule behind all of it. The drive never overwrites the image it is running, or the only good copy, until the new image has been completely written and verified. If power fails mid-update, the old slot still boots. And if the new image is written but fails to start, the bootloader notices, typically by a "try once" flag that the new firmware must clear after a successful start, and falls back to the previous slot.

**Activation without a reset** (commit action 3) swaps firmware while the drive stays online: the drive pauses command processing, starts the new code and resumes, keeping its queues. The pause is bounded, because the drive advertises a maximum firmware activation time. Data centers use it to update fleets without rebooting servers, rolling a new version out to a few drives first and to the rest only after those behave.

Before commit, the drive verifies the image's signature and its security version, so a tampered or downgraded image is rejected without ever running ([Supplement F §F.5](f-security.md#f5-secure-boot-and-signed-firmware)).

## G.4 What the drive tells you: health and logs ⭐

A drive reports on itself through **log pages**, read with the NVMe Get Log Page command:

- **SMART / Health Information** (Self-Monitoring, Analysis and Reporting Technology) is the summary every tool shows:
    - *critical warning* bits: spare capacity below its threshold, temperature out of range, reliability degraded, media switched to read-only, or the backup power for volatile memory failed;
    - *composite temperature*;
    - *available spare*, the percentage of spare blocks left, with its threshold;
    - *percentage used*, the vendor's estimate of endurance consumed, which can pass 100%;
    - *data units read and written*, in units of 1,000 × 512 bytes, from which write amplification and endurance use can be worked out;
    - *power cycles*, *power-on hours* and *unsafe shutdowns*;
    - *media and data integrity errors*, the uncorrectable reads.
- **Error Information** records each recent command that failed: its status, its queue and command identifier, the logical block address (LBA) and the namespace.
- **Persistent Event Log** (NVMe 1.4) keeps a timestamped history that survives power cycles: firmware commits, resets, thermal excursions, changed settings and SMART snapshots. It answers the question "what happened to this drive before it failed?".
- **Telemetry** logs (NVMe 1.3) carry the drive's internal state in a vendor-defined format that the host can't decode, collected for the vendor's engineers. *Host-initiated* telemetry is captured when the host asks; *controller-initiated* telemetry is captured by the drive itself when it detects an internal problem, and the drive then tells the host it has something to collect.

The first three are for the drive's owner; telemetry is for the people who wrote the firmware. Data-center customers often require extra log pages on top, covered with data-center drives in Supplement I.

## G.5 Debugging: from serial console to crash dump

Firmware runs on a chip with no screen and no operating system to catch its mistakes, so it is built with its own debugging aids:

- **A serial console.** A UART (universal asynchronous receiver-transmitter) port prints the firmware's text log during development: boot progress, warnings, state dumps.
- **Debug ports.** JTAG (the Joint Test Action Group's test port) and Arm's two-wire Serial Wire Debug connect a hardware debugger that can halt cores, read memory and set breakpoints. Production drives lock these ports or open them only after a signed challenge ([Supplement F §F.5](f-security.md#f5-secure-boot-and-signed-firmware)).
- **Trace buffers.** Halting a core changes timing, and many firmware bugs are about timing, so firmware records events into ring buffers in SRAM ([Ch 0 §0.10](../core/ch0-foundations.md#010-queues-and-ring-buffers)) that keep the last few thousand events at almost no cost.
- **Asserts.** An assert is a check on something that must always be true, such as "this block is not already free". When one fails, the firmware has found a bug or corrupted state, and continuing could damage data.
- **Crash dumps.** On a failed assert or a fatal error, the firmware saves its registers, stacks and trace buffers to flash before resetting, often into the telemetry log, so the evidence survives. Many drives then enter a reduced **assert mode** that answers only basic commands, enough to pull the dump and sometimes the data, but no longer normal I/O.

On the other side of the interface, protocol analyzers record the PCIe (Peripheral Component Interconnect Express) traffic itself, showing exactly what the host sent and what the drive answered ([Chapter 7](../core/ch7-testing.md)).

## G.6 From the factory to the field

**The factory** turns a controller and a set of NAND packages into a drive:

1. **Load factory firmware** through the boot ROM's download mode, since a new drive has none.
2. **Scan for bad blocks.** The flash arrives with factory-marked bad blocks; the drive reads those marks and tests every other block, building its initial bad-block table ([Ch 4 §4.7](../core/ch4-ftl.md#47-bad-block-management)).
3. **Calibrate.** Each die is characterized, for example to tune its read-retry voltage tables ([Ch 3 §3.4.2](../core/ch3-nand-flash.md#342-read-retry)).
4. **Burn in.** Hours of writing and reading, often at high temperature, make weak parts fail in the factory instead of at a customer.
5. **Personalize.** The production firmware, the customer's settings, the serial number and the drive's identity certificate for attestation are written ([Supplement F §F.6](f-security.md#f6-attestation-spdm-and-caliptra)).
6. **Final test**, then ship.

**The field-return loop** is where firmware quality is really made. When a drive misbehaves at a customer, the investigation follows a cycle:

![Six steps in a clockwise loop: a field failure; evidence collected from logs, telemetry and the crash dump; the failure reproduced in the lab; the root cause found and confirmed; a fix and the regression suite; and a release as a firmware update, which goes back to the field](../assets/figures/supp-g/rma-loop.svg){ .sdd-fig }
/// figure-caption
The field-return loop. Every turn of it fixes a whole population of drives, not just the one returned, as long as the evidence of step 2 exists.
///

1. **Field failure**: a drive hangs, slows down, reports errors or goes read-only.
2. **Evidence**: the persistent event log, telemetry and any crash dump are collected, from the running drive if possible or from the returned drive in the lab.
3. **Reproduce**: engineers recreate the failure with the same firmware, workload and conditions, often by replaying the recorded history.
4. **Root cause**: the bug, or the flash behavior the firmware didn't expect, is found and confirmed.
5. **Fix and test**: the fix is written, and a test that reproduces the failure joins the regression suite, so the bug can't return unnoticed ([Chapter 7](../core/ch7-testing.md)).
6. **Release**: the fix ships as a firmware update through §G.3, to every drive that could hit the same bug.

The loop only turns if step 2 has something to work with, which is why the logs, telemetry and crash dumps of §G.4 and §G.5 are designed in from the start rather than added after the first escalation.

---

## Key takeaways

1. **SSD firmware is a real-time program on a multi-core controller**, split roughly into front end, FTL and back end, guarded by watchdogs, with its images stored redundantly in ROM, NOR and NAND.
2. **Boot climbs a ladder** of ROM, bootloader and main image, each checking the next and each with a fallback, and the drive is ready only when its map is restored.
3. **Updates are two commands**, download then commit, into slots that keep the old image until the new one has proved itself, so a power loss mid-update never bricks the drive.
4. **Activation without a reset** swaps firmware online within an advertised time, which lets fleets update without reboots.
5. **SMART is for the owner, telemetry is for the vendor**, and the persistent event log is the drive's memory of what happened before it failed.
6. **Debugging is built in**: consoles and debug ports for development, trace buffers for timing bugs, asserts and crash dumps for the field.
7. **The field-return loop** turns one failed drive into a fix for all of them, provided the evidence was designed in.

---

## Key vocabulary

| Term | 中文 | Meaning |
|---|---|---|
| firmware task | 固件任務（台：韌體任務） | One of the firmware's concurrent jobs, such as command handling, the FTL or flash channel control. → [§G.1](#g1-what-the-firmware-is) |
| watchdog timer | 看門狗定時器（台：看門狗計時器） | A timer that resets the controller if the firmware stops making progress. → [§G.1](#g1-what-the-firmware-is) |
| boot ROM | 啟動ROM（台：開機ROM） | Fixed code in the controller's silicon, the first to run at power-on. → [§G.2](#g2-boot-from-power-on-to-ready) |
| bootloader | 引導加載程序（台：開機載入程式） | A small program that loads and checks the main firmware image. → [§G.2](#g2-boot-from-power-on-to-ready) |
| SPI NOR flash | SPI NOR閃存（台：SPI NOR快閃記憶體） | A small flash chip read over the Serial Peripheral Interface, often holding the bootloader. → [§G.1](#g1-what-the-firmware-is) |
| download mode | 下載模式 | The boot ROM's fallback that accepts firmware over a test interface, used in factories and labs. → [§G.2](#g2-boot-from-power-on-to-ready) |
| ready (CSTS.RDY) | 就緒（台：就緒狀態） | The NVMe status bit by which the drive tells the host it can take commands. → [§G.2](#g2-boot-from-power-on-to-ready) |
| Firmware Image Download | 固件鏡像下載（台：韌體映像下載） | The NVMe command that carries a new firmware image to the drive in pieces. → [§G.3](#g3-updating-firmware-in-the-field) |
| Firmware Commit | 固件提交（台：韌體提交） | The NVMe command that verifies an image, writes it to a slot and activates it. → [§G.3](#g3-updating-firmware-in-the-field) |
| firmware slot | 固件槽（台：韌體槽位） | One of up to seven stored firmware images; slot 1 may be read-only. → [§G.3](#g3-updating-firmware-in-the-field) |
| activation without reset | 免重置激活（台：免重置啟用） | Switching to new firmware while the drive stays online, within an advertised time. → [§G.3](#g3-updating-firmware-in-the-field) |
| fallback image | 回退鏡像（台：備援映像） | The previous or factory image the bootloader starts if a new one fails. → [§G.3](#g3-updating-firmware-in-the-field) |
| log page | 日誌頁 | A block of status data the host reads with Get Log Page. → [§G.4](#g4-what-the-drive-tells-you-health-and-logs) |
| SMART / Health Information | SMART健康信息（台：SMART健康資訊） | The summary log: warnings, temperature, spare, endurance used, data written, errors. → [§G.4](#g4-what-the-drive-tells-you-health-and-logs) |
| percentage used | 已用壽命百分比 | The vendor's estimate of how much of the drive's endurance has been consumed. → [§G.4](#g4-what-the-drive-tells-you-health-and-logs) |
| Error Information log | 錯誤信息日誌（台：錯誤資訊日誌） | Details of recent failed commands: status, command, LBA and namespace. → [§G.4](#g4-what-the-drive-tells-you-health-and-logs) |
| Persistent Event Log | 持久事件日誌 | A timestamped history of the drive's events that survives power cycles. → [§G.4](#g4-what-the-drive-tells-you-health-and-logs) |
| telemetry | 遙測（台：遙測資料） | Vendor-format internal state, captured on the host's request or by the drive itself. → [§G.4](#g4-what-the-drive-tells-you-health-and-logs) |
| UART console | 串口控制台（台：序列埠主控台） | A serial port that prints the firmware's text log during development. → [§G.5](#g5-debugging-from-serial-console-to-crash-dump) |
| JTAG / SWD | JTAG / SWD調試接口（台：JTAG / SWD除錯介面） | Hardware debug ports that let a debugger halt cores and read memory. → [§G.5](#g5-debugging-from-serial-console-to-crash-dump) |
| assert | 斷言 | A check on something that must always be true; failing it means a bug or corrupted state. → [§G.5](#g5-debugging-from-serial-console-to-crash-dump) |
| crash dump | 崩潰轉儲（台：當機傾印） | Registers, stacks and traces saved to flash at a fatal error, for later analysis. → [§G.5](#g5-debugging-from-serial-console-to-crash-dump) |
| burn-in | 老化測試（台：預燒測試） | Running new drives hard, often hot, so weak parts fail before shipping. → [§G.6](#g6-from-the-factory-to-the-field) |
| field-return (RMA) analysis | 返修分析（台：退貨分析） | Investigating a failed drive from the field, through to a fix for the whole population. → [§G.6](#g6-from-the-factory-to-the-field) |
| regression test | 回歸測試 | A test added to catch a fixed bug if it ever returns. → [§G.6](#g6-from-the-factory-to-the-field) |

---

## Check yourself

1. Why is the bootloader often kept in a separate SPI NOR chip rather than in the NAND with the main firmware?

    ??? success "Answer"
        At power-on only the boot ROM is running, with no flash interface trained and no error correction set up. SPI NOR flash can be read from address 0 with almost no setup, so the ROM can load the bootloader simply and reliably. NAND needs channel training, ECC and bad-block handling, which is the kind of work the bootloader and main firmware do. See [§G.1](#g1-what-the-firmware-is) and [§G.2](#g2-boot-from-power-on-to-ready).

2. Why does an SSD take longer to become ready after a power loss than after a clean shutdown?

    ??? success "Answer"
        After a clean shutdown the firmware saved a complete mapping table and only has to load it. After an unclean shutdown the last snapshot is out of date, so the firmware must also rebuild every change made since, by scanning recently written blocks, before it can report ready. See [§G.2](#g2-boot-from-power-on-to-ready).

3. What two NVMe commands perform a firmware update, and why is the image sent in pieces?

    ??? success "Answer"
        Firmware Image Download sends the image and Firmware Commit verifies it, writes it to a slot and activates it. The image is far larger than the data a single command carries, so it is sent in pieces, each with an offset and a length, and assembled in a staging buffer in the drive. See [§G.3](#g3-updating-firmware-in-the-field).

4. Power fails halfway through writing a new firmware image. Why does the drive still start?

    ??? success "Answer"
        The drive never overwrites the image it is running, or its only good copy, until the new image is completely written and verified. The new image goes into a different slot, so the old slot is untouched and the bootloader starts it as before. See [§G.3](#g3-updating-firmware-in-the-field).

5. A new image is written successfully but crashes at every start. How does a well-designed drive recover?

    ??? success "Answer"
        The new image is first started on a "try once" basis: a flag says it is on trial, and the new firmware clears it only after a successful start. If the flag is still set at the next boot, the bootloader concludes the new image failed and starts the previous slot, or the read-only factory slot, instead. See [§G.3](#g3-updating-firmware-in-the-field).

6. What does activation without a reset allow, and what limits its cost?

    ??? success "Answer"
        It switches the drive to new firmware while the drive stays online, keeping its queues, so servers don't need rebooting and fleets can update gradually. Commands pause during the switch, and the drive advertises a maximum firmware activation time, so the host knows how long the pause can last. See [§G.3](#g3-updating-firmware-in-the-field).

7. A drive's SMART log shows "percentage used" at 85% and "available spare" at 100%. What do the two fields say, and should the owner worry?

    ??? success "Answer"
        Percentage used is the vendor's estimate of how much of the rated endurance has been consumed by writing; available spare is the share of spare blocks still unused. At 85% used the drive is near its rated write life, though it may run beyond 100%; with spare at 100%, no blocks have yet been retired. The owner should plan a replacement before it reaches its rating, but nothing is failing now. See [§G.4](#g4-what-the-drive-tells-you-health-and-logs).

8. How does telemetry differ from the SMART log, and who is each for?

    ??? success "Answer"
        SMART is a standardized summary the owner's tools can read and act on. Telemetry is the drive's internal state in a format only the vendor can decode, captured when the host asks or when the drive detects a problem itself; it is for the vendor's engineers investigating a failure. See [§G.4](#g4-what-the-drive-tells-you-health-and-logs).

9. Why do firmware engineers rely on trace buffers rather than a debugger for many bugs?

    ??? success "Answer"
        Many firmware bugs depend on timing between cores, the flash and the host. Halting a core with a debugger changes that timing, and the bug often disappears. A trace buffer records events into a ring in SRAM at almost no cost, so the sequence leading to the failure can be read afterward without disturbing it. See [§G.5](#g5-debugging-from-serial-console-to-crash-dump).

10. When an assert fails in the field, what should the firmware do, and why not simply carry on?

    ??? success "Answer"
        It should save a crash dump of its registers, stacks and traces to flash, then reset or enter a reduced assert mode that answers only basic commands. A failed assert means a bug or corrupted state; continuing could write wrong data or corrupt the map, while stopping preserves both the data and the evidence. See [§G.5](#g5-debugging-from-serial-console-to-crash-dump).

11. What does burn-in achieve, and how does it relate to the factory bad-block scan?

    ??? success "Answer"
        Burn-in runs new drives hard, often at high temperature, so that weak parts that would fail early in service fail in the factory instead. The bad-block scan finds blocks that are already bad when the drive is built; burn-in finds parts that are about to go bad. Both keep early failures away from customers. See [§G.6](#g6-from-the-factory-to-the-field).

12. Walk through the field-return loop. Which step decides whether the loop can turn at all, and why?

    ??? success "Answer"
        Field failure, evidence, reproduce, root cause, fix and test, then release as a firmware update. The evidence step decides it: without the persistent event log, telemetry or a crash dump, the failure often can't be reproduced, so no root cause is found and nothing is fixed. That is why those logs are designed into the firmware from the start. See [§G.6](#g6-from-the-factory-to-the-field).

---

??? info "📖 Provenance"

    This supplement is original to this site; 《深入淺出SSD》 does not cover
    firmware boot, update or debug. It is written against the NVMe base
    specification, revision 2.x (Firmware Image Download, Firmware Commit, the
    SMART / Health, Error Information, Firmware Slot Information, Telemetry
    and Persistent Event log pages), with common industry practice for the
    rest. Its figures are original drawings.

??? info "🔎 Sources for the 2026 update"

    The command and log details were checked in November 2026 against these sources:

    - Commit actions 2 (activate at the next reset) and 3 (activate without a reset), as exposed by nvme-cli — [nvme-fw-commit manual](https://man.archlinux.org/man/nvme-fw-commit.1.en)
    - The Persistent Event Log (log page 0Dh, NVMe 1.4) — [nvme-persistent-event-log manual](https://man.archlinux.org/man/nvme-persistent-event-log.1.en)
    - The host- and controller-initiated telemetry logs — [Microsoft NVMe documentation](https://learn.microsoft.com/windows/win32/api/nvme/ne-nvme-nvme_log_pages)

*Next: Supplement H — The host side: one read traced through the operating system, and the tools that show what a drive is doing.*
