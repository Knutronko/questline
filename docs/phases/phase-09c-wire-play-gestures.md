# Phase 09c — Wire play gestures (swipe / drag / long-press) — **schedule on gate**

> Session preamble: see `phase-00-bootstrap.md`. Read ADR-0005, ADR-0008,
> [`wire-setup.md`](../wire-setup.md), [`BALANCE-AUTOMATION.md`](../BALANCE-AUTOMATION.md) §5.
>
> **Status:** brief ready; **do not start** until the Wire playability gate says bots
> cannot complete a normal combat loop with hooks + Tap alone.
> **Does not renumber** 10–15 (lettered Wire follow-up like 05b / 09b).

## Context

Wire v2 (09b) ships find / hierarchy / tap / screenshot. FP-G3 bots should prefer
**hooks + Tap deploy**. If Drag-deploy (or swipe/long-press skills) must be on the
*measured* path and hooks cannot cover them, extend Wire here before or at FP-G3 start.

## Objective

Add thin gesture ops on QuestlineWire so `driver = "questline"` can drag/swipe/long-press
with FakeWire CI coverage — still `#if UNITY_EDITOR || QUESTLINE_DEV`, loopback only.

## In scope

1. Ops: `swipe` and/or `drag` (start/end points or element→point), `long_press` if needed.
2. Python `DriverPort` / QuestlineDriver implementations; remove AuthoringError stubs.
3. FakeWire + wire-smoke extension; error mapping consistent with ADR-0008.
4. Docs: wire-setup, ADR addendum or short ADR-0009, STATUS-DUAL, BALANCE-AUTOMATION §5.
5. Game trigger **QL-2d** (companion sync + optional Dev APK).

## Out of scope

- Poco (14), GameLens G1–G3 product features, text_input unless free,
  non-loopback bind, full AltTester parity.

## Acceptance criteria

- [ ] CI FakeWire gesture tests; live Editor smoke for one drag or swipe path.
- [ ] Old companion without gesture feature → clear AuthoringError.
- [ ] STATUS-DUAL + BALANCE-AUTOMATION updated; QL-2d noted on game side.

## Gate (when to schedule)

Schedule 09c if **any** is true at FP-G3 planning:

1. Bot policy must use Drag deploy (Tap-forced profile rejected by maintainer).
2. A critical combat action has no hook and needs a gesture.
3. Human feel validation of gestures is in-scope for the **automated** suite (unusual).

Otherwise keep this brief parked and ship FP-G3 hooks-first.
