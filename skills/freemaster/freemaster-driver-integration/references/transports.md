# Transport Mini-Recipes, Failure Patterns, and Discovery Questions

Reference for `freemaster-driver-integration`. Load on demand when the user needs transport-specific code, failure diagnosis, or the agent needs to ask clarifying questions.

---

## LPUART

**Use when** the target uses an S32 LPUART peripheral.

```c
#include "freemaster.h"
#include "freemaster_s32_lpuart.h"

int main(void)
{
    /* Application hardware initialization */
    FMSTR_SerialSetBaseAddress(LPUART0_BASE);
    FMSTR_Init();

    for (;;) {
        FMSTR_Poll();
        /* Application background work */
    }
}
```

**Interrupt mode** — attach `FMSTR_SerialIsr` in the LPUART interrupt handler.

**Checks**
- Correct LPUART instance selected.
- Clocks and pins initialized before `FMSTR_Init()`.
- Serial base address matches the actual peripheral instance.

---

## LINFlexD

**Use when** the target uses LINFlexD as the FreeMASTER serial transport.

```c
#include "freemaster.h"
#include "freemaster_s32_linflexd.h"

int main(void)
{
    /* Application hardware initialization */
    FMSTR_SerialSetBaseAddress(LINFLEXD0_BASE);
    FMSTR_Init();

    for (;;) {
        FMSTR_Poll();
        /* Application background work */
    }
}
```

**Interrupt mode** — attach `FMSTR_SerialIsr` in the LINFlexD interrupt handler.

**Checks**
- Correct LINFlexD instance selected.
- Peripheral configured for the intended serial mode before `FMSTR_Init()`.
- LINFlexD header used, not LPUART header.

---

## FlexCAN

**Use when** the target uses FlexCAN for FreeMASTER communication.

```c
#include "freemaster.h"
#include "freemaster_s32_flexcan.h"

int main(void)
{
    /* Application hardware initialization */
    FMSTR_CanSetBaseAddress(FLEXCAN0_BASE);
    FMSTR_Init();

    for (;;) {
        FMSTR_Poll();
        /* Application background work */
    }
}
```

**Interrupt mode** — attach `FMSTR_CanIsr` in the FlexCAN interrupt handler.

**Checks**
- Correct FlexCAN instance selected.
- CAN peripheral initialized before `FMSTR_Init()`.
- `FMSTR_CanSetBaseAddress` used (not the serial setter).
- `FMSTR_CanIsr` used (not `FMSTR_SerialIsr`).

---

## BDM

**Use when** FreeMASTER communication is configured for BDM.

```c
#include "freemaster.h"

int main(void)
{
    /* Application hardware initialization */
    FMSTR_Init();

    for (;;) {
        FMSTR_Poll();
        /* Application background work */
    }
}
```

**Checks**
- `freemaster_cfg.h` selects BDM mode.
- No transport-specific serial or CAN header included.
- Debugger and BDM setup match the intended FreeMASTER configuration.

---

## Common Failure Patterns

Check these first when the integration does not work:

- Wrong S32DS version or wrong FreeMASTER platform folder selected.
- Installation folder found but does not contain the expected `src` subfolders.
- Required include directories missing from the project.
- Required source directories not added to the build.
- `freemaster_cfg.h` missing or not on the include path.
- Template not copied from `src/template`.
- Wrong transport-specific header selected.
- Interrupt mode enabled in config but ISR not connected.
- Wrong base address passed to `FMSTR_SerialSetBaseAddress` or `FMSTR_CanSetBaseAddress`.
- `FMSTR_Init()` never called.
- `FMSTR_Poll()` not called regularly in polling mode.
- Transport-specific header included for BDM, or omitted for UART/CAN.

---

## Discovery Questions

Ask these when the request is underspecified:

- Which MCU or S32 device are you using?
- Which S32 Design Studio version are you using?
- Which platform family should the FreeMASTER Driver come from (e.g. `S32K3`)?
- Which transport is used: LPUART, LINFlexD, FlexCAN, or BDM?
- Are you using polling mode or interrupt mode?
- Which peripheral instance should FreeMASTER use?
- Have you already found the FreeMASTER installation folder?
- Do you already have a `freemaster_cfg.h`, or should one be created from the template?
- Which IDE or build system is this project using?
