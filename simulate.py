#!/usr/bin/env python3
"""
simulate.py - Simulate Logisim circuits with given memory files using logisim-generic-2.7.1.jar.

Features:
- Simulates circuits without modifying the original .circ file.
- Supports circuits with multiple memories (both RAM and ROM).
- Extracts and outputs the final state of:
    1. Register Bank (x0 - x31)
    2. Every memory in the circuit (RAM and ROM)
    3. Every named register found in the circuit
- Automatically compiles the Java simulation helper if needed.
"""

import os
import sys
import argparse
import subprocess
import json
import tempfile
from pathlib import Path

# RISC-V ABI Register Names
ABI_NAMES = [
    "zero", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
    "s0/fp", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
    "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
    "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"
]

def find_default_jar(script_dir: Path) -> Path:
    candidates = [
        script_dir / "logisim-generic-2.7.1.jar",
        Path.cwd() / "logisim-generic-2.7.1.jar",
        script_dir.parent / "logisim-generic-2.7.1.jar",
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    # Check if any logisim*.jar exists in script_dir or cwd
    for d in [script_dir, Path.cwd()]:
        jars = list(d.glob("logisim*.jar"))
        if jars:
            return jars[0].resolve()
    return (script_dir / "logisim-generic-2.7.1.jar").resolve()

def ensure_compiled(script_dir: Path, jar_path: Path) -> None:
    mem_dir = script_dir / "com" / "cburch" / "logisim" / "std" / "memory"
    java_file = mem_dir / "CircuitSimulator.java"

    if not java_file.is_file():
        sys.exit(f"Error: Java runner source not found at {java_file}")

    expected_classes = [
        "CircuitSimulator.class",
        "CircuitSimulator$MemoryRecord.class",
        "CircuitSimulator$RegisterRecord.class",
        "CircuitSimulator$SimResult.class",
    ]

    needs_compilation = False
    for c_name in expected_classes:
        cf = mem_dir / c_name
        if not cf.is_file():
            needs_compilation = True
            break
        if java_file.stat().st_mtime > cf.stat().st_mtime:
            needs_compilation = True
            break

    if needs_compilation:
        cmd = [
            "javac",
            "-cp", str(jar_path),
            str(java_file)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            sys.exit(f"Error compiling Java simulation helper:\n{res.stderr}")

def format_logisim_raw(entries: list, total_words: int) -> str:
    """Format non-zero entries into a compact Logisim v2.0 raw string with run-length encoding."""
    if not entries:
        return "v2.0 raw\n0\n"

    # Map addresses to values
    addr_map = {e["addr"]: e["value"] for e in entries}
    max_addr = max(addr_map.keys()) if addr_map else 0

    tokens = []
    curr_val = None
    curr_count = 0

    for addr in range(max_addr + 1):
        val = addr_map.get(addr, 0)
        # mask to unsigned 32-bit hex
        u_val = val & 0xFFFFFFFF
        hex_str = f"{u_val:x}"

        if curr_val is None:
            curr_val = hex_str
            curr_count = 1
        elif hex_str == curr_val:
            curr_count += 1
        else:
            if curr_count > 1:
                tokens.append(f"{curr_count}*{curr_val}")
            else:
                tokens.append(curr_val)
            curr_val = hex_str
            curr_count = 1

    if curr_val is not None:
        if curr_count > 1:
            tokens.append(f"{curr_count}*{curr_val}")
        else:
            tokens.append(curr_val)

    # Wrap tokens into lines of ~8 tokens
    lines = ["v2.0 raw"]
    for i in range(0, len(tokens), 8):
        lines.append(" ".join(tokens[i:i+8]))
    return "\n".join(lines) + "\n"

def format_register_bank(reg_data: list) -> str:
    lines = [
        "=" * 80,
        "                    FINAL STATE OF REGISTER BANK (x0 - x31)",
        "=" * 80,
        f"{'Reg':<5} {'ABI':<8} {'Hex Value':<14} {'Signed Dec':>12} {'Unsigned Dec':>14}",
        "-" * 80,
    ]
    for item in reg_data:
        idx = item["index"]
        name = item["name"]
        abi = item.get("abi", ABI_NAMES[idx] if idx < len(ABI_NAMES) else "")
        val = item["value"]
        u_val = val & 0xFFFFFFFF
        hex_val = f"0x{u_val:08x}"
        lines.append(f"{name:<5} {abi:<8} {hex_val:<14} {val:>12} {u_val:>14}")
    lines.append("=" * 80 + "\n")
    return "\n".join(lines)

def format_named_registers(named_regs: list) -> str:
    lines = [
        "=" * 80,
        "                     FINAL STATE OF NAMED REGISTERS",
        "=" * 80,
    ]
    if not named_regs:
        lines.append("  (No named registers found in circuit)")
        lines.append("=" * 80 + "\n")
        return "\n".join(lines)

    lines.append(f"{'Hierarchy Path':<24} {'Register Name':<16} {'Location':<12} {'Width':<8} {'Hex Value':<14} {'Decimal':>12}")
    lines.append("-" * 80)

    for r in named_regs:
        hier = r.get("hierarchy", "")
        label = r.get("label", "")
        loc = r.get("location", "")
        width = f"{r.get('width', 32)}-bit"
        val = r.get("value", 0)
        u_val = val & 0xFFFFFFFF
        hex_val = f"0x{u_val:08x}"
        lines.append(f"{hier:<24} {label:<16} {loc:<12} {width:<8} {hex_val:<14} {val:>12}")

    lines.append("=" * 80 + "\n")
    return "\n".join(lines)

def format_memories(memories: list) -> str:
    lines = [
        "=" * 80,
        "                     FINAL STATE OF EVERY MEMORY",
        "=" * 80,
    ]
    if not memories:
        lines.append("  (No memory components found in circuit)")
        lines.append("=" * 80 + "\n")
        return "\n".join(lines)

    for idx, m in enumerate(memories, 1):
        mtype = m.get("type", "RAM")
        label = m.get("label", "") or "<unlabeled>"
        hier = m.get("hierarchy", "")
        loc = m.get("location", "")
        addr_bits = m.get("addrBits", 0)
        data_bits = m.get("dataBits", 0)
        is_target = "YES" if m.get("isTarget") else "NO"
        entries = m.get("nonZeroEntries", [])
        total_words = 1 << addr_bits

        lines.extend([
            f"Memory #{idx}: {mtype} [{label}]",
            f"  Hierarchy Path: {hier}",
            f"  Location:       {loc}",
            f"  Address Width:  {addr_bits} bits ({total_words} words)",
            f"  Data Width:     {data_bits} bits",
            f"  Target Loaded:  {is_target}",
            f"  Non-zero Words: {len(entries)}",
            "-" * 80,
        ])

        if not entries:
            lines.append("  (Memory is clear / all zeros)")
        else:
            lines.append("  Non-Zero Entries:")
            if data_bits == 32:
                lines.append(f"    {'Word Addr':<14} {'Byte Addr':<14} {'Hex Value':<14} {'Decimal':>12}")
                lines.append("    " + "-" * 58)
                for e in entries:
                    w_addr = e["addr"]
                    b_addr = w_addr * 4
                    w_hex = f"0x{w_addr:08x}"
                    b_hex = f"0x{b_addr:08x}"
                    u_val = e["value"] & 0xFFFFFFFF
                    val_hex = f"0x{u_val:08x}"
                    lines.append(f"    [{w_hex}]   {b_hex:<14} {val_hex:<14} {e['value']:>12}")
            else:
                lines.append(f"    {'Word Addr':<14} {'Hex Value':<14} {'Decimal':>12}")
                lines.append("    " + "-" * 42)
                for e in entries:
                    w_addr = e["addr"]
                    w_hex = f"0x{w_addr:x}"
                    u_val = e["value"] & ((1 << data_bits) - 1)
                    val_hex = f"0x{u_val:x}"
                    lines.append(f"    [{w_hex}]   {val_hex:<14} {e['value']:>12}")

        # Compact Raw Dump
        lines.append("")
        lines.append("  Logisim Raw Image Format (v2.0 raw):")
        raw_str = format_logisim_raw(entries, total_words)
        for r_line in raw_str.strip().splitlines():
            lines.append("    " + r_line)

        lines.append("=" * 80)

    lines.append("")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(
        description="Simulate Logisim circuits with given memory files using logisim-generic-2.7.1.jar.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 simulate.py RISCV_Monociclo.circ mem_instrucoes_monociclo
  python3 simulate.py RISCV_Multiciclo.circ mem_instrucoes_monociclo --cycles 100
  python3 simulate.py RISCV_Pipeline.circ mem_instrucoes_monociclo -o output/
        """
    )

    parser.add_argument("circuit", help="Path to the Logisim .circ file")
    parser.add_argument("mem", help="Path to the memory file to load (Logisim raw/hex format)")
    parser.add_argument("--jar", default=None, help="Path to logisim-generic-2.7.1.jar (default: auto-detect)")
    parser.add_argument("--cycles", "-c", type=int, default=1000, help="Maximum clock cycles to simulate (default: 1000)")
    parser.add_argument("--output-dir", "-o", default="output", help="Directory to save output files (default: output/)")
    parser.add_argument("--reg-out", default=None, help="Custom output path for Register Bank state")
    parser.add_argument("--mem-out", default=None, help="Custom output path for all memories state")
    parser.add_argument("--named-reg-out", default=None, help="Custom output path for named registers state")
    parser.add_argument("--all-out", default=None, help="Custom output path for combined simulation report")
    parser.add_argument("--json-out", default=None, help="Save full simulation results to a JSON file")
    parser.add_argument("--target-mem", default=None, help="Explicit target memory identifier (location e.g. '(310,360)', label, or type)")
    parser.add_argument("--data-mem", default=None, help="Optional memory file to load into data RAM")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print verbose simulation output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress console summary output")

    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    circ_path = Path(args.circuit).resolve()
    mem_path = Path(args.mem).resolve()

    if not circ_path.is_file():
        sys.exit(f"Error: Circuit file not found: {circ_path}")
    if not mem_path.is_file():
        sys.exit(f"Error: Memory file not found: {mem_path}")

    jar_path = Path(args.jar).resolve() if args.jar else find_default_jar(script_dir)
    if not jar_path.is_file():
        sys.exit(f"Error: Logisim jar not found at {jar_path}. Please pass --jar <path>.")

    # Ensure Java simulator is compiled
    ensure_compiled(script_dir, jar_path)

    # Prepare output paths
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    reg_out_path = Path(args.reg_out).resolve() if args.reg_out else (out_dir / "registers_bank.txt")
    mem_out_path = Path(args.mem_out).resolve() if args.mem_out else (out_dir / "memories.txt")
    named_reg_out_path = Path(args.named_reg_out).resolve() if args.named_reg_out else (out_dir / "named_registers.txt")

    # Temporary file for JSON communication
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp_json:
        tmp_json_path = tmp_json.name

    try:
        cmd = [
            "java",
            "-cp", f"{script_dir}:{jar_path}",
            "com.cburch.logisim.std.memory.CircuitSimulator",
            "--circ", str(circ_path),
            "--mem", str(mem_path),
            "--cycles", str(args.cycles),
            "--json-out", tmp_json_path,
        ]
        if args.target_mem:
            cmd.extend(["--target-mem", args.target_mem])
        if args.data_mem:
            cmd.extend(["--data-mem", str(Path(args.data_mem).resolve())])
        if args.verbose:
            cmd.append("--verbose")

        if args.verbose:
            print(f"Executing: {' '.join(cmd)}")

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            sys.exit(f"Simulation failed with exit code {res.returncode}:\n{res.stderr}\n{res.stdout}")

        if args.verbose and res.stdout.strip():
            print(res.stdout.strip())

        with open(tmp_json_path, "r", encoding="utf-8") as f:
            sim_data = json.load(f)

    finally:
        if os.path.exists(tmp_json_path):
            os.remove(tmp_json_path)

    # Generate formatted outputs
    reg_text = format_register_bank(sim_data.get("registerBank", []))
    mem_text = format_memories(sim_data.get("memories", []))
    named_reg_text = format_named_registers(sim_data.get("namedRegisters", []))

    # Write output files
    reg_out_path.write_text(reg_text, encoding="utf-8")
    mem_out_path.write_text(mem_text, encoding="utf-8")
    named_reg_out_path.write_text(named_reg_text, encoding="utf-8")

    if args.all_out:
        all_out_path = Path(args.all_out).resolve()
        combined_text = (
            f"SIMULATION REPORT\n"
            f"Circuit: {circ_path.name}\n"
            f"Memory:  {mem_path.name}\n"
            f"Cycles:  {sim_data.get('totalCycles', 0)}\n"
            f"Halt:    {sim_data.get('haltReason', '')}\n\n"
            f"{reg_text}\n"
            f"{named_reg_text}\n"
            f"{mem_text}\n"
        )
        all_out_path.write_text(combined_text, encoding="utf-8")

    if args.json_out:
        json_out_path = Path(args.json_out).resolve()
        json_out_path.write_text(json.dumps(sim_data, indent=2), encoding="utf-8")

    if not args.quiet:
        print("\n" + "=" * 65)
        print(f"  Logisim Simulation Completed Successfully")
        print("=" * 65)
        print(f"  Circuit:        {circ_path.name}")
        print(f"  Memory Loaded:  {mem_path.name}")
        print(f"  Total Cycles:   {sim_data.get('totalCycles', 0)}")
        print(f"  Halt Reason:    {sim_data.get('haltReason', '')}")
        print("-" * 65)

        # Highlight non-zero registers
        non_zero_regs = [r for r in sim_data.get("registerBank", []) if r["value"] != 0]
        print(f"  Register Bank:  {len(non_zero_regs)} non-zero register(s)")
        for r in non_zero_regs:
            u_val = r["value"] & 0xFFFFFFFF
            print(f"    {r['name']} ({r.get('abi', '')}): 0x{u_val:08x} ({r['value']})")

        # Highlight named registers
        named_regs = sim_data.get("namedRegisters", [])
        if named_regs:
            print(f"  Named Registers: {len(named_regs)} register(s)")
            for r in named_regs:
                u_val = r["value"] & 0xFFFFFFFF
                print(f"    {r['label']} ({r['hierarchy']}): 0x{u_val:08x} ({r['value']})")

        # Highlight memories
        mems = sim_data.get("memories", [])
        print(f"  Memories Found: {len(mems)}")
        for m in mems:
            loaded_tag = " [TARGET LOADED]" if m.get("isTarget") else ""
            print(f"    - {m['type']} [{m.get('label') or '<unlabeled>'}] at {m['location']} in {m['hierarchy']} (non-zero: {len(m.get('nonZeroEntries', []))}){loaded_tag}")

        print("-" * 65)
        print("  Generated Output Files:")
        print(f"    [Registers] -> {reg_out_path}")
        print(f"    [Memories]  -> {mem_out_path}")
        print(f"    [NamedRegs] -> {named_reg_out_path}")
        if args.all_out:
            print(f"    [Combined]  -> {Path(args.all_out).resolve()}")
        if args.json_out:
            print(f"    [JSON Data] -> {Path(args.json_out).resolve()}")
        print("=" * 65 + "\n")

if __name__ == "__main__":
    main()

