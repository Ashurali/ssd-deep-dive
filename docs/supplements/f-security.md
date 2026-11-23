---
title: "Supp F — Security & Sanitization"
tags:
  - security
  - sanitize
  - firmware
  - nvme
source_anchor: "original — no book chapter"
textbook: v2
---

# Supplement F — Security & Sanitization

A solid-state drive (SSD) is trusted with data that must not leak, on hardware that leaves the owner's hands: drives are stolen, sold, returned under warranty and retired by the thousand. This supplement covers the machinery that keeps that trust: encryption inside the drive, the standard way to manage it, the commands that truly erase a drive, and the checks that stop a drive from running firmware nobody approved.

Much of it rests on [Chapter 4](../core/ch4-ftl.md): because flash can't be overwritten in place, a drive keeps old copies of data in places the host can't reach, and every erase method has to be judged by whether it reaches them.

!!! abstract "In this supplement"
    - **The threat model** ⭐ — who the attacker is, and what each defense covers (§F.1)
    - **Self-encrypting drives** ⭐⭐ — AES-XTS in the data path, and the key hierarchy that makes crypto erase instant (§F.2)
    - **TCG Opal, Pyrite and Ruby** — the standard way to lock and manage an encrypting drive (§F.3)
    - **Erasing an SSD** ⭐⭐ — why deleted data lingers, Format versus Sanitize, and the sanitization standards (§F.4)
    - **Secure boot and attestation** ⭐ — signed firmware, anti-rollback, SPDM and Caliptra (§F.5–F.6)
    - **Certifications** — FIPS 140-3 and its neighbors (§F.7)

    Short on time? §F.2 and §F.4 carry the most.

---

## F.1 The threat model ⭐

Security starts by naming the attacker. For a drive there are four:

- **The finder.** A laptop is stolen or a drive is lost. The attacker has the hardware but not the password. Defense: encryption with keys the attacker can't recover (§F.2–F.3).
- **The next owner.** A drive is sold, recycled or returned to its vendor under an RMA (return merchandise authorization). The attacker reads whatever the last owner left behind, including copies the host never knew about. Defense: sanitization that reaches every copy (§F.4).
- **The firmware attacker.** Someone replaces the drive's firmware, in the supply chain or through the update command, with a version that leaks data or lies about what it stores. Defense: signed firmware, secure boot and anti-rollback (§F.5).
- **The impostor.** A counterfeit or tampered drive claims to be genuine. Defense: device identity and attestation (§F.6).

One attacker is out of scope: someone who controls the running, unlocked computer. Once the drive is unlocked it returns plaintext to anyone the host lets ask, so that threat belongs to the operating system, not the drive.

## F.2 Self-encrypting drives ⭐⭐

A **self-encrypting drive (SED)** encrypts everything it writes and decrypts everything it reads, in a hardware engine on the controller's data path between the host interface and the flash. The cipher is the Advanced Encryption Standard (AES) in **XTS mode** (the XEX-based tweaked-codebook mode with ciphertext stealing), standardized for storage by the Institute of Electrical and Electronics Engineers as IEEE 1619. XTS mixes each block's address into the encryption as a "tweak", so the same data stored at two addresses produces different ciphertext, and an attacker can't spot repeated content by comparing blocks. XTS hides data but does not authenticate it; it is built for storage, where the ciphertext must be exactly as large as the data.

Because the engine runs at full interface speed, encryption costs no measurable performance, and many drives encrypt all the time whether or not anyone has set a password.

**The key hierarchy** is what makes an SED manageable:

![A key hierarchy from top to bottom: a password goes through a key derivation function to give the key encryption key; that key unwraps the media encryption key, whose wrapped copy is stored in flash; the media encryption key drives the AES-XTS engine, so the NAND holds only ciphertext. Crypto erase destroys the media encryption key, and every block becomes noise](../assets/figures/supp-f/sed-keys.svg){ .sdd-fig }
/// figure-caption
The SED key hierarchy. Only a wrapped copy of the media key is ever stored, and the key that unwraps it exists only while the right password is supplied. Destroying the media key makes every block unreadable at once.
///

- The **media encryption key (MEK)** encrypts the data. It is random, generated inside the drive, and never leaves it.
- The MEK is stored only in **wrapped** (encrypted) form, under a **key encryption key (KEK)**.
- The KEK is derived from the user's password by a **key derivation function (KDF)** each time the drive is unlocked, and is never stored.

Three practical consequences follow. **Changing a password** re-wraps one small key; the terabytes of data are untouched. **Locking** happens at power loss: without the KEK, the MEK can't be unwrapped, so a drive removed from a laptop reads as locked. And **crypto erase** becomes instant: generate a new MEK and destroy the old one, and every block in the drive, including stale copies and spare blocks, becomes ciphertext under a key that no longer exists.

That last point is the SED's quiet superpower for sanitization (§F.4), with one condition: it is only as strong as the guarantee that **all** user data was encrypted with the destroyed key, and that no copy of the key survives anywhere.

## F.3 The TCG storage specifications: Opal, Pyrite and Ruby

An SED needs a standard way for the host to set passwords, lock ranges and erase. That standard comes from the **Trusted Computing Group (TCG)**, whose storage specifications define **Security Subsystem Classes (SSC)**, profiles for different markets:

- **Opal** is the client class, found in most laptop SSDs (revision 2.02 was published in January 2022). It defines administrator and user authorities, and **locking ranges**: up to several LBA (logical block address) ranges, each with its own MEK and its own read and write locks.
- **Pyrite** offers the same access control without encryption, for drives that have no cipher engine. With no keys to destroy, its erase relies on actually removing the data.
- **Ruby** is the newer class for data-center drives, bringing Opal-style management to enterprise SSDs.

Three Opal features show up in practice:

- **Shadow MBR (master boot record).** While the drive is locked, the host sees a small read-only image at the start of the drive instead of the real data. The computer boots that image, a pre-boot authentication program that asks for the password, unlocks the drive and then restarts into the real operating system.
- **PSID revert.** The **physical security ID (PSID)** printed on the drive's label lets anyone holding the drive reset it to factory state. That crypto-erases everything, so a drive with a forgotten password can be reused but not read.
- **Locking on power loss.** Ranges re-lock whenever power is removed, which is what defends against the finder of §F.1.

The TCG commands travel inside the interface's generic security commands: **Security Send** and **Security Receive** on NVMe (Non-Volatile Memory Express) drives, and their equivalents on SATA (Serial AT Attachment) and SCSI (Small Computer System Interface) drives. The drive's firmware implements the TCG state machine behind them.

## F.4 Erasing an SSD: why deleted data lingers ⭐⭐

### F.4.1 Delete, Trim and overwrite

On a hard disk, overwriting a block replaces its contents. On an SSD it never does, and every everyday way of "removing" data leaves copies behind:

- **Deleting a file** changes only the filesystem's records. The blocks still hold the data until something reuses them.
- **Trim** tells the drive that a range of LBAs is no longer needed ([Ch 4 §4.4](../core/ch4-ftl.md#44-trim)). The drive drops those LBAs from its map, so the host can no longer read the data, but the pages stay in the flash until garbage collection (GC) erases their blocks, which may be much later.
- **Overwriting** an LBA writes the new data to a fresh page; the old page becomes a stale copy, again until GC gets to it ([Ch 4 §4.3](../core/ch4-ftl.md#43-garbage-collection)).

Beyond the stale copies there are places the host can't address at all: the spare flash kept for **over-provisioning (OP)** ([Ch 1 §1.5.1](../core/ch1-overview.md#151-basic-information)), blocks retired as bad that may still hold readable pages ([Ch 4 §4.7](../core/ch4-ftl.md#47-bad-block-management)), and caches in the drive's working memory, its DRAM (dynamic random-access memory) and SRAM (static random-access memory). Anyone who can read the raw flash chips, by desoldering them for example, sees all of it.

![The drive's flash as one bar in four parts: current data, stale copies, spare area for over-provisioning, and retired blocks. Delete and Trim reach only the current data; Sanitize with block erase reaches all four parts; crypto erase makes all four unreadable](../assets/figures/supp-f/erase-scope.svg){ .sdd-fig }
/// figure-caption
Where copies of data live inside an SSD. Host-level deletion touches only what the host can address; only commands that work inside the drive reach the rest.
///

So **sanitizing an SSD must happen inside the drive**, by firmware that knows where every copy is. No host-side tool that writes zeros over the visible LBAs can do it.

### F.4.2 Format NVM and Sanitize

The NVMe command set gives two ways to erase from inside:

**Format NVM with Secure Erase Settings.** Format NVM (NVM being non-volatile memory, the spec's word for the drive's storage) reformats a namespace ([Ch 6 §6.7](../core/ch6-nvme.md#67-namespaces)) and can erase it on the way: a *user data erase*, or a *cryptographic erase* that replaces the encryption key. It was designed as a formatting command, so its guarantees are weaker: its scope is a namespace or all of them, and it does not promise to finish if interrupted.

**Sanitize** (added in NVMe 1.3, 2017) is the command built for the job. It offers three actions:

- **Block erase**: erase every block of flash, including spare and stale ones.
- **Crypto erase**: replace the media encryption keys, so all old ciphertext becomes unreadable.
- **Overwrite**: write a pattern over the media a chosen number of times, which suits other media better than flash, where it is slow and wears the cells.

What makes Sanitize trustworthy is its contract, not just its action:

- **Scope**: the whole NVM subsystem, meaning every namespace and all user data, including caches, deallocated blocks and OP.
- **Persistence**: once started it runs to completion, resuming after a reset or power loss; until it finishes, the drive refuses commands that would read old data.
- **Reporting**: a Sanitize Status log shows progress and the result. A failed sanitize leaves the drive in a failure state that only another successful sanitize clears, so a half-erased drive can't quietly go back into service.
- **Options**: a No-Deallocate setting controls how the erased blocks read afterward, and newer revisions can pause the drive in a media-verification state, so the host can read back and check the result before normal use resumes.

| | Trim | Format NVM, secure erase | Sanitize |
|---|---|---|---|
| Removes data from the host's view | yes | yes | yes |
| Reaches stale copies, OP, retired blocks | no | usually, not promised | yes |
| Reaches caches and every namespace | no | no | yes |
| Finishes after a power loss | — | no | yes |
| Meant for | everyday use | reformatting | retiring a drive |

### F.4.3 The standards: NIST SP 800-88 and IEEE 2883

Organizations don't pick erase commands ad hoc; they follow standards that name levels of sanitization:

- **Clear**: protect against simple, non-invasive recovery through the normal interface.
- **Purge**: protect against laboratory recovery, such as reading raw flash chips. For an SSD, this means Sanitize.
- **Destroy**: make the media unusable, by shredding or melting, for example.

The long-standing reference was the US National Institute of Standards and Technology's (NIST) SP 800-88. Its second revision (September 2025) turned it into guidance for running an enterprise sanitization program and handed the media-specific techniques to **IEEE 2883-2022**, which maps clear, purge and destroy to the exact commands of each interface, NVMe Sanitize among them. Cryptographic erase is the one technique NIST still describes itself, because its strength depends entirely on how the keys were managed.

## F.5 Secure boot and signed firmware ⭐

A drive's firmware sees every byte the drive stores, so firmware the vendor didn't write is the deepest compromise possible. **Secure boot** makes sure only approved firmware ever runs:

![A chain of trust: the boot ROM, fixed in silicon and reading fuses that hold the hash of the vendor's public key and a version counter, checks the bootloader's signature; the bootloader checks the main firmware's signature and version; a bad signature or an older version stops the boot. Each stage's hash is recorded as a measurement for attestation](../assets/figures/supp-f/boot-chain.svg){ .sdd-fig }
/// figure-caption
The chain of trust. Each stage verifies the next before running it, starting from code that can't be changed; the fuses anchor both the vendor's key and the oldest version the drive will accept.
///

- **The root of trust** is the boot ROM (read-only memory), code fixed in the controller's silicon at manufacture. It can't be altered, so it is the one stage that needs no checking. One-time programmable (OTP) fuses hold the hash of the vendor's public key.
- **The chain of trust**: the ROM checks the bootloader's digital signature against that key before running it, and the bootloader checks the main firmware the same way. A firmware image that wasn't signed with the vendor's private key never runs.
- **Signatures** today are mostly ECDSA (the Elliptic Curve Digital Signature Algorithm) or RSA (Rivest–Shamir–Adleman). Because a future quantum computer could forge both, signing is moving to post-quantum cryptography (PQC): NIST standardized ML-DSA (the Module-Lattice Digital Signature Algorithm) in 2024, and the US NSA's CNSA 2.0 suite asks for quantum-resistant firmware signatures, preferred from 2025 and used exclusively by 2030.
- **Anti-rollback**: a valid signature isn't enough, because an old, genuinely signed version may contain a known vulnerability. Each image carries a security version number, and a counter in fuses records the lowest acceptable one; the boot stops for anything older, and the counter rises when a new version is committed.

The same checks guard the update path. A new image arrives through the NVMe Firmware Image Download command and is verified before Firmware Commit activates it, so a bad image is rejected without ever running. The other way in, the debug ports that engineers use (JTAG and the serial console), are locked in production drives or opened only through a signed challenge.

## F.6 Attestation: SPDM and Caliptra

Secure boot protects the drive from bad firmware. **Attestation** lets the *host* check the drive: who made it, and exactly what firmware it is running.

The protocol is the **Security Protocol and Data Model (SPDM)** from the Distributed Management Task Force (DMTF). In outline:

1. The drive proves its **identity** with a certificate chain, rooted in the manufacturer's certificate authority and provisioned at the factory.
2. The host sends a fresh random **nonce** and asks for **measurements**: the hashes of each boot stage that secure boot recorded.
3. The drive returns the measurements **signed** with its identity key, including the nonce, so the reply can't be a replay of an old one.
4. The host compares the measurements with the values the vendor published for that firmware version.

SPDM messages travel over whatever path the platform has: the Management Component Transport Protocol (MCTP) used for out-of-band management, a mailbox on the PCIe (Peripheral Component Interconnect Express) link, or the storage Security Send and Receive commands. A related TCG standard, the **Device Identifier Composition Engine (DICE)**, derives part of the device's identity from the hash of the firmware itself, so a device running different firmware ends up with a different key and can't impersonate the approved one.

**Caliptra** is the industry's shared answer to building all this. It is an open-source silicon root of trust, published as chip design source and firmware, started through the Open Compute Project (OCP) by AMD, Google, Microsoft and NVIDIA and hosted by the CHIPS Alliance. A controller vendor drops it into the chip and gets measured boot, DICE identity and attestation, reviewed in public. Caliptra 2.0 adds post-quantum ML-DSA signatures through its Adams Bridge accelerator, and newer releases add OCP's L.O.C.K. key-management block for storage drives, so a drive's media keys can be generated and held inside the root of trust itself.

Phones guard their most sensitive values differently, in the Replay Protected Memory Block of [Supplement B](b-ufs.md#b5-rpmb-replay-protected-memory-block), whose writes need a valid message authentication code and a fresh counter; NVMe drives can offer the same block.

## F.7 Certifications

Buyers who must prove their storage is secure rely on independent validation:

- **FIPS 140-3** (Federal Information Processing Standard), run by NIST's Cryptographic Module Validation Program (CMVP) with Canada, tests that a cryptographic module, here the drive's encryption engine and key management, is built and implemented correctly, at one of four security levels. The older FIPS 140-2 certificates moved to the historical list on 21 September 2026, so new US government purchases now need FIPS 140-3.
- **Common Criteria** evaluations, against agreed protection profiles for full-drive encryption, are the international counterpart.
- **TCG certification** checks that an Opal or Ruby drive implements the specification correctly.

A certificate covers a specific hardware and firmware version, which is one more reason the firmware update path of §F.5 is tightly controlled.

---

## Key takeaways

1. **Name the attacker first**: the finder, the next owner, the firmware attacker and the impostor each need a different defense; the running, unlocked host is out of the drive's reach.
2. **An SED encrypts everything with AES-XTS** under a media key that is stored only wrapped; passwords re-wrap one small key, and crypto erase destroys it.
3. **Opal is the standard SED interface**: locking ranges, a shadow MBR for pre-boot authentication, and PSID revert for a drive with a lost password.
4. **Flash keeps old copies** in stale pages, OP and retired blocks, so delete, Trim and host overwrites don't sanitize an SSD; only work inside the drive does.
5. **Sanitize is the purge-level command**: whole-subsystem scope, completion after power loss, and a reported result, as IEEE 2883 and NIST SP 800-88 Rev. 2 expect.
6. **Secure boot plus anti-rollback** runs only signed firmware no older than the fuse counter, and signing is moving to post-quantum algorithms.
7. **Attestation lets the host check the drive**: SPDM returns signed measurements, DICE ties identity to firmware, and Caliptra offers it all as open silicon.

---

## Key vocabulary

| Term | 中文 | Meaning |
|---|---|---|
| threat model | 威脅模型 | A statement of which attackers a defense is meant to stop, and which it isn't. → [§F.1](#f1-the-threat-model) |
| self-encrypting drive (SED) | 自加密硬盤（台：自我加密硬碟） | A drive that encrypts all data in hardware on its own data path. → [§F.2](#f2-self-encrypting-drives) |
| AES-XTS | AES-XTS加密模式 | AES in XTS mode (IEEE 1619), which mixes each block's address into its encryption. → [§F.2](#f2-self-encrypting-drives) |
| media encryption key (MEK) | 介質加密密鑰（台：媒體加密金鑰） | The random key that encrypts the stored data; it never leaves the drive. → [§F.2](#f2-self-encrypting-drives) |
| key encryption key (KEK) | 密鑰加密密鑰（台：金鑰加密金鑰） | The key, derived from a password, that wraps the media key. → [§F.2](#f2-self-encrypting-drives) |
| key derivation function (KDF) | 密鑰派生函數（台：金鑰衍生函數） | A function that turns a password into a key, slowly enough to resist guessing. → [§F.2](#f2-self-encrypting-drives) |
| crypto erase | 加密擦除（台：密碼抹除） | Erasing by destroying the media key, which makes all ciphertext unreadable at once. → [§F.2](#f2-self-encrypting-drives) |
| Trusted Computing Group (TCG) | 可信計算組織（台：可信賴運算組織） | The industry body behind the Opal, Pyrite and Ruby storage specifications. → [§F.3](#f3-the-tcg-storage-specifications-opal-pyrite-and-ruby) |
| Opal / Pyrite / Ruby | Opal / Pyrite / Ruby規範 | TCG's client class with encryption, its unencrypted variant, and its data-center class. → [§F.3](#f3-the-tcg-storage-specifications-opal-pyrite-and-ruby) |
| locking range | 鎖定範圍 | An LBA range with its own key and its own read and write locks. → [§F.3](#f3-the-tcg-storage-specifications-opal-pyrite-and-ruby) |
| shadow MBR | 影子主引導記錄（台：影子主開機紀錄） | The pre-boot image a locked drive shows at its start, to ask for the password. → [§F.3](#f3-the-tcg-storage-specifications-opal-pyrite-and-ruby) |
| physical security ID (PSID) | 物理安全標識（台：實體安全識別碼） | The code on the drive's label that resets it to factory state, erasing all data. → [§F.3](#f3-the-tcg-storage-specifications-opal-pyrite-and-ruby) |
| Security Send / Receive | 安全發送 / 接收命令（台：安全傳送 / 接收指令） | The NVMe commands that carry TCG and other security protocols. → [§F.3](#f3-the-tcg-storage-specifications-opal-pyrite-and-ruby) |
| stale copy | 陳舊副本（台：過期副本） | An old version of data left in flash after an overwrite, until garbage collection erases it. → [§F.4.1](#f41-delete-trim-and-overwrite) |
| sanitization | 數據清除（台：資料清除） | Removing data so that it can't be recovered, at a stated level of effort. → [§F.4](#f4-erasing-an-ssd-why-deleted-data-lingers) |
| Format NVM (secure erase) | 格式化NVM（安全擦除） | The NVMe format command, which can erase a namespace's user data or its key. → [§F.4.2](#f42-format-nvm-and-sanitize) |
| Sanitize | 清除命令（台：清除指令） | The NVMe command that erases all user data in the subsystem by block erase, crypto erase or overwrite, and finishes even after a power loss. → [§F.4.2](#f42-format-nvm-and-sanitize) |
| clear / purge / destroy | 清除 / 淨化 / 銷毀 | The sanitization levels, from defeating simple recovery to making the media unusable. → [§F.4.3](#f43-the-standards-nist-sp-800-88-and-ieee-2883) |
| root of trust | 信任根 | The first code to run, fixed in silicon, which every later stage depends on. → [§F.5](#f5-secure-boot-and-signed-firmware) |
| chain of trust | 信任鏈 | Each boot stage verifying the next before running it. → [§F.5](#f5-secure-boot-and-signed-firmware) |
| anti-rollback | 防回滾（台：防降版） | Refusing validly signed firmware older than a version counter kept in fuses. → [§F.5](#f5-secure-boot-and-signed-firmware) |
| post-quantum cryptography (PQC) | 後量子密碼（台：後量子密碼學） | Algorithms, such as ML-DSA, designed to resist attack by quantum computers. → [§F.5](#f5-secure-boot-and-signed-firmware) |
| attestation | 證明（台：認證） | A device proving to the host who it is and what firmware it runs. → [§F.6](#f6-attestation-spdm-and-caliptra) |
| Security Protocol and Data Model (SPDM) | 安全協議與數據模型（台：安全協定與資料模型） | DMTF's protocol for device identity, signed measurements and secure sessions. → [§F.6](#f6-attestation-spdm-and-caliptra) |
| Caliptra | Caliptra信任根 | The open-source silicon root of trust from OCP and the CHIPS Alliance. → [§F.6](#f6-attestation-spdm-and-caliptra) |
| FIPS 140-3 | FIPS 140-3認證 | The US and Canadian validation of cryptographic modules; it replaced FIPS 140-2 in 2026. → [§F.7](#f7-certifications) |

---

## Check yourself

1. Name the four attackers a drive defends against, and the defense for each. Which attacker is out of the drive's reach, and why?

    ??? success "Answer"
        The finder of a lost or stolen drive (encryption and locking), the next owner of a sold or returned drive (sanitization), the firmware attacker (signed firmware, secure boot and anti-rollback) and the impostor, a counterfeit or tampered drive (identity and attestation). The attacker who controls the running, unlocked host is out of reach: once unlocked, the drive returns plaintext to whatever the host asks for. See [§F.1](#f1-the-threat-model).

2. Why does an SED store the media key only in wrapped form, and what does that make cheap?

    ??? success "Answer"
        If the media key were stored in plain form, anyone reading the flash could take it and decrypt everything. Wrapped under a key derived from the password, it is useless without that password, and the drive locks when power is removed. It makes two things cheap: changing a password re-wraps one small key instead of re-encrypting the data, and crypto erase just replaces the media key. See [§F.2](#f2-self-encrypting-drives).

3. What does XTS mode's tweak protect against, and what doesn't XTS provide?

    ??? success "Answer"
        The tweak mixes each block's address into its encryption, so identical data stored at different addresses gives different ciphertext and repeated content can't be spotted by comparing blocks. XTS provides confidentiality only: it has no authentication tag, so it does not by itself detect ciphertext that has been altered. See [§F.2](#f2-self-encrypting-drives).

4. A user forgets their Opal password. What can be done with the drive, and what happens to the data?

    ??? success "Answer"
        A PSID revert, using the physical security ID printed on the drive's label, resets the drive to factory state. That crypto-erases all its data, so the drive can be reused but the old data can't be read. See [§F.3](#f3-the-tcg-storage-specifications-opal-pyrite-and-ruby).

5. A user deletes a file and the filesystem sends Trim. Why can the data still be recovered from the raw flash?

    ??? success "Answer"
        Deleting changes only the filesystem's records, and Trim only removes the LBAs from the drive's map, so the host can no longer read them. The pages themselves stay in the flash until garbage collection erases their blocks, possibly much later. Anyone who reads the raw chips can still see them, along with stale copies from earlier overwrites, OP space and retired blocks. See [§F.4.1](#f41-delete-trim-and-overwrite).

6. Why can't a host-side tool that writes zeros over every LBA sanitize an SSD?

    ??? success "Answer"
        Each write goes to a fresh page, so overwriting an LBA leaves the old page behind as a stale copy, and the host can't address the spare OP area, retired blocks or caches at all. Only the drive's firmware knows where every copy is, so sanitization must be done inside the drive, by Sanitize or by crypto erase. See [§F.4.1](#f41-delete-trim-and-overwrite).

7. Name the three Sanitize actions and the property that makes Sanitize better than Format NVM for retiring a drive.

    ??? success "Answer"
        Block erase, crypto erase and overwrite. Sanitize's contract is stronger: it covers the whole NVM subsystem, including caches and every namespace, it resumes after a reset or power loss until finished, it blocks access to old data in the meantime, and it reports success or failure in a log. Format NVM is a formatting command that makes none of those promises. See [§F.4.2](#f42-format-nvm-and-sanitize).

8. Crypto erase takes milliseconds while a block erase of a large drive takes much longer. What condition must hold for crypto erase to be trusted?

    ??? success "Answer"
        Every piece of user data must have been encrypted with the key that is destroyed, and no copy of that key may survive anywhere, not in a backup, a wrapped copy or a log. If some data was ever stored unencrypted or under another key, it remains readable. That dependence on key management is why NIST still describes cryptographic erase itself rather than deferring it to IEEE 2883. See [§F.2](#f2-self-encrypting-drives) and [§F.4.3](#f43-the-standards-nist-sp-800-88-and-ieee-2883).

9. What do clear, purge and destroy each protect against, and which one means Sanitize on an SSD?

    ??? success "Answer"
        Clear protects against simple recovery through the normal interface; purge protects against laboratory recovery, such as reading the raw flash chips; destroy makes the media unusable. For an SSD, purge means the Sanitize command, as IEEE 2883-2022 sets out per interface. See [§F.4.3](#f43-the-standards-nist-sp-800-88-and-ieee-2883).

10. Why is a valid signature not enough to accept a firmware image, and how does anti-rollback close the gap?

    ??? success "Answer"
        An old firmware version is genuinely signed but may contain a known vulnerability, so an attacker could install it to reopen the hole. Each image carries a security version number, and fuses hold a counter of the lowest acceptable one; the boot refuses older images, and the counter rises when a newer version is committed. See [§F.5](#f5-secure-boot-and-signed-firmware).

11. In an SPDM measurement exchange, what does the host's nonce prevent, and what does the host compare the measurements against?

    ??? success "Answer"
        The nonce is fresh and random and the drive must sign it into its reply, so an attacker can't replay a recording of an earlier, honest answer. The host compares the signed measurements, the hashes of each boot stage, with the values the vendor published for the firmware the drive claims to run. See [§F.6](#f6-attestation-spdm-and-caliptra).

12. Why are firmware signatures moving to post-quantum algorithms, and what deadline drives it?

    ??? success "Answer"
        A large quantum computer could forge today's ECDSA and RSA signatures, which would let an attacker sign malicious firmware, and drives stay in service for years. NIST standardized ML-DSA in 2024, and the NSA's CNSA 2.0 suite asks for quantum-resistant firmware signing to be preferred from 2025 and exclusive by 2030; Caliptra 2.0 already signs with ML-DSA. See [§F.5](#f5-secure-boot-and-signed-firmware).

---

??? info "📖 Provenance"

    This supplement is original to this site; 《深入淺出SSD》 does not cover
    drive security. It is written against NVM Express Base Specification
    2.x (Sanitize, Format NVM, Security Send/Receive), TCG Storage Opal SSC
    2.02, IEEE 1619 (XTS-AES), IEEE 2883-2022, NIST SP 800-88 Rev. 2,
    FIPS 140-3, DMTF SPDM (DSP0274) and the Caliptra 2.x specifications.
    Its figures are original drawings.

??? info "🔎 Sources for the 2026 update"

    The dated facts were checked in November 2026 against these sources:

    - Opal SSC 2.02 (January 2022) and the TCG's list of later revisions — [TCG](https://trustedcomputinggroup.org/storage-work-group-storage-security-subsystem-class-opal/)
    - NIST SP 800-88 Rev. 2 (September 2025) and its hand-off to IEEE 2883 — [NIST CSRC](https://csrc.nist.gov/pubs/sp/800/88/r2/final)
    - FIPS 140-2 certificates move to the historical list on 21 September 2026 — [NIST CMVP](https://csrc.nist.gov/projects/cryptographic-module-validation-program)
    - CNSA 2.0's firmware-signing timeline (prefer by 2025, exclusive by 2030) — [Entrust](https://www.entrust.com/blog/2024/05/nsa-announces-update-to-commercial-national-security-algorithm-suite-2-0-and-quantum-computing-faq)
    - Caliptra 2.0's ML-DSA through Adams Bridge, and the release history — [CHIPS Alliance](https://chipsalliance.github.io/caliptra-web/versioning)
    - Sanitize options (No-Deallocate, media verification) as exposed by nvme-cli — [nvme-sanitize manual](https://man.archlinux.org/man/nvme-sanitize.1)

*Next: [Supplement G — Firmware](g-firmware.md): how the drive boots, updates itself and gets debugged — the life of the code that §F.5 protects.*
